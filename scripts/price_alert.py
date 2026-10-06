"""收藏到價進場通知：盤中低頻查價，碰到自己設定的進場價就送到自己的 Telegram。

到價設定來自選股器「我的收藏」，存在 .local/price-alerts.json；Token 與頻道只從
.local/telegram.env 讀取。報價用證交所 MIS 網站內部端點（非官方公開 API）：
一次查一批、最多 20 檔、至少間隔 5 分鐘。這是提醒，不會下單。
"""
import argparse
import json
import math
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent))
import telegram_notify as tg  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ALERTS = ROOT/'.local/price-alerts.json'
ENV = ROOT/'.local/telegram.env'
TAIPEI = timezone(timedelta(hours=8))
MIN_INTERVAL = 300
MAX_SYMBOLS = 20
CONDITIONS = {'gte': '突破 ≥', 'lte': '回到 ≤'}
STATUSES = ('watching', 'triggered', 'check_delivery')
MIS_URL = 'https://mis.twse.com.tw/stock/api/getStockInfo.jsp?json=1&delay=0&ex_ch='

def _positive(value, field, required=True):
    if value in (None, ''):
        if required: raise ValueError(f'{field}必須填寫。')
        return None
    if isinstance(value, bool): raise ValueError(f'{field}必須是數字。')
    number = float(value)
    if not math.isfinite(number) or number <= 0: raise ValueError(f'{field}必須大於零。')
    return number

def validate_alert(raw):
    if not isinstance(raw, dict): raise ValueError('到價設定格式錯誤。')
    symbol = str(raw.get('symbol', '')).strip().upper()
    if not re.fullmatch(r'\d{4,6}[A-Z]?', symbol): raise ValueError(f'股票代號格式錯誤：{symbol or "空白"}')
    condition = raw.get('condition', 'gte')
    if condition not in CONDITIONS: raise ValueError(f'{symbol} 進場條件只能是突破或回到。')
    status = raw.get('status', 'watching')
    if status not in STATUSES: status = 'watching'
    note = str(raw.get('note', '') or '').strip()
    if len(note) > 200: raise ValueError(f'{symbol} 計畫備註請在 200 字內。')
    return dict(symbol=symbol, name=str(raw.get('name', '') or '')[:30], condition=condition,
                price=_positive(raw.get('price'), f'{symbol} 進場價'),
                stop=_positive(raw.get('stop'), f'{symbol} 停損價', required=False),
                note=note, enabled=bool(raw.get('enabled', True)), status=status,
                triggered_at=raw.get('triggered_at') if status != 'watching' else None,
                triggered_price=raw.get('triggered_price') if status != 'watching' else None)

def validate_alerts(items):
    if not isinstance(items, list): raise ValueError('到價設定必須是清單。')
    alerts = [validate_alert(x) for x in items]
    symbols = [a['symbol'] for a in alerts]
    if len(set(symbols)) != len(symbols): raise ValueError('同一檔股票只能設定一個進場價。')
    if sum(a['enabled'] for a in alerts) > MAX_SYMBOLS:
        raise ValueError(f'同時啟用最多 {MAX_SYMBOLS} 檔；低頻查價，不做全市場掃描。')
    return alerts

def load_alerts(path=ALERTS):
    path = Path(path)
    if not path.exists(): return []
    return validate_alerts(json.loads(path.read_text(encoding='utf-8-sig')).get('alerts', []))

def save_alerts(alerts, path=ALERTS):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps({'alerts': alerts}, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(path)

def _number(raw):
    try: value = float(str(raw).split('_')[0])
    except (TypeError, ValueError): return None
    return value if value > 0 else None

def parse_mis(body):
    quotes = {}
    for row in body.get('msgArray', []):
        symbol = row.get('c')
        if not symbol: continue
        # z/pz are often '-' for busy stocks between snapshots; then only best bid/ask is known.
        # Yesterday's close (y) is never used to trigger an entry.
        price, basis = _number(row.get('z')), '最新成交'
        if price is None: price, basis = _number(row.get('pz')), '前一筆成交'
        bid, ask = _number(row.get('b')), _number(row.get('a'))
        if price is None and bid is None and ask is None: continue
        quotes[symbol] = dict(price=price, bid=bid, ask=ask, basis=basis, name=row.get('n', ''),
                              time=f"{row.get('d', '')} {row.get('t', '')}".strip(), source='證交所MIS')
    return quotes

def trigger_price(alert, quote):
    """Trade price when known; otherwise the executable side: best bid for a breakout, best ask for a pullback."""
    if quote.get('price'): return quote['price'], quote['basis']
    if alert['condition'] == 'gte': return quote.get('bid'), '最佳買價'
    return quote.get('ask'), '最佳賣價'

def fetch_quotes(symbols, opener=urlopen):
    symbols = list(dict.fromkeys(symbols))[:MAX_SYMBOLS]
    if not symbols: return {}
    # Listed or OTC is unknown from the watchlist alone; ask for both in one request.
    ex_ch = '|'.join(f'{m}_{s}.tw' for s in symbols for m in ('tse', 'otc'))
    request = Request(MIS_URL+ex_ch, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://mis.twse.com.tw/stock/index.jsp'})
    try:
        with opener(request, timeout=15) as response:
            return parse_mis(json.loads(response.read().decode('utf-8')))
    except (URLError, TimeoutError, OSError, json.JSONDecodeError):
        raise ValueError('查不到報價（證交所 MIS 沒有回應）；這一輪跳過，不用記憶價格補。') from None

def is_trading_time(now):
    """Weekday 09:00-13:30 Taipei. Exchange holidays are not modelled; MIS simply returns no new trades."""
    now = now.astimezone(TAIPEI)
    return now.weekday() < 5 and (9, 0) <= (now.hour, now.minute) <= (13, 30)

def hit(alert, price):
    return price >= alert['price'] if alert['condition'] == 'gte' else price <= alert['price']

def fmt(x): return f'{x:,.2f}'.rstrip('0').rstrip('.')

def alert_message(alert, quote, simulated=False):
    price, basis = trigger_price(alert, quote)
    lines = ['AI 煉金術｜到價進場提醒' + ('（課堂模擬價格）' if simulated else ''),
             f"{alert['symbol']} {quote.get('name') or alert.get('name', '')}".strip(),
             f"現價 {fmt(price)}（{basis}｜{quote['time']}｜{quote['source']}）",
             f"觸發：{CONDITIONS[alert['condition']]} {fmt(alert['price'])}"]
    if alert.get('stop'): lines.append(f"交易計畫停損：{fmt(alert['stop'])}")
    if alert.get('note'): lines.append(f"計畫備註：{alert['note']}")
    lines += ['', '這是到價提醒，不是下單；成交價、部位與出場依自己的交易計畫確認。']
    if simulated: lines.append('模擬價格只測試通知，不代表真實行情。')
    return '\n'.join(lines)

def check_once(alerts, quotes, send, now, simulated=False, persist=None):
    """Send at most one message per alert. Returns triggered symbols; records status only when persist."""
    persist = not simulated if persist is None else persist
    fired = []
    for alert in alerts:
        if not alert['enabled'] or alert['status'] != 'watching': continue
        quote = quotes.get(alert['symbol'])
        price = trigger_price(alert, quote)[0] if quote else None
        if price is None or not hit(alert, price): continue
        stamp = now.astimezone(TAIPEI).isoformat(timespec='seconds')
        try:
            send(alert_message(alert, quote, simulated))
        except ValueError:
            if persist: alert.update(status='check_delivery', triggered_at=stamp, triggered_price=price)
            raise
        if persist: alert.update(status='triggered', triggered_at=stamp, triggered_price=price)
        fired.append(alert['symbol'])
    return fired

def fake_quotes(pairs, now):
    quotes = {}
    for pair in pairs:
        symbol, _, value = pair.partition('=')
        quotes[symbol.strip().upper()] = dict(price=_positive(value, f'{symbol} 模擬價'), name='', basis='模擬價格',
                                              time=now.astimezone(TAIPEI).strftime('%Y-%m-%d %H:%M'), source='課堂測試')
    return quotes

def main(argv=None, now=datetime.now, sleep=time.sleep, opener=urlopen):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--alerts', default=str(ALERTS)); p.add_argument('--env', default=str(ENV))
    p.add_argument('--interval', type=int, default=MIN_INTERVAL, help='查價間隔秒數，最少 300')
    p.add_argument('--once', action='store_true', help='只查一次就結束（收盤後也可核對最新價）')
    p.add_argument('--dry-run', action='store_true', help='查一次價並預覽訊息；不讀 Token、不傳送、不改狀態')
    p.add_argument('--fake-price', nargs='+', metavar='代號=價格', help='課堂沒開盤時用模擬價測試；不改狀態')
    p.add_argument('--test', action='store_true', help='送一則測試訊息，確認 Bot 與頻道設定')
    a = p.parse_args(argv)
    if a.interval < MIN_INTERVAL: raise ValueError(f'查價間隔最少 {MIN_INTERVAL} 秒，避免頻繁打證交所網站。')
    if a.test:
        token, target = tg.credentials(a.env)
        tg.send_one(token, target, 'AI 煉金術｜Telegram 設定測試\n收到這則，代表到價通知會送到這裡。', opener)
        print('測試訊息已送出；請核對手機或頻道是否收到。'); return 0
    alerts = load_alerts(a.alerts)
    watching = [x for x in alerts if x['enabled'] and x['status'] == 'watching']
    if not watching:
        print('沒有監看中的到價設定。請在選股器「我的收藏」設定進場價並儲存。'); return 0
    if a.dry_run: send = lambda text: print('\n--- 預覽（未傳送）---\n'+text)
    else:
        token, target = tg.credentials(a.env)
        send = lambda text: tg.send_one(token, target, text, opener)
    print(f"監看 {len(watching)} 檔：" + '、'.join(f"{x['symbol']} {CONDITIONS[x['condition']]} {fmt(x['price'])}" for x in watching))
    if a.fake_price:
        fired = check_once(alerts, fake_quotes(a.fake_price, now(TAIPEI)), send, now(TAIPEI), simulated=True)
        print(f"模擬觸發：{'、'.join(fired) or '無'}（狀態未改變）"); return 0
    persist = not a.dry_run
    if a.dry_run: a.once = True
    while True:
        current = now(TAIPEI)
        if a.once or is_trading_time(current):
            try:
                symbols = [x['symbol'] for x in alerts if x['enabled'] and x['status'] == 'watching']
                quotes = fetch_quotes(symbols, opener)
                missing = [s for s in symbols if s not in quotes]
                if missing: print('這一輪沒有成交價：' + '、'.join(missing) + '（下一輪再查）')
                fired = check_once(alerts, quotes, send, current, persist=persist)
            except ValueError as exc:
                if persist: save_alerts(alerts, a.alerts)
                if '查不到報價' not in str(exc): raise
                print(str(exc)); fired = []
            if fired and persist: save_alerts(alerts, a.alerts)
            print(f"{current:%H:%M} 查價完成，觸發：{'、'.join(fired) or '無'}")
        else:
            print(f'{current:%m/%d %H:%M} 非盤中（平日 09:00–13:30），等待下次檢查。')
        if a.once or not any(x['enabled'] and x['status'] == 'watching' for x in alerts):
            print('本輪結束。' if a.once else '全部到價設定都已觸發，盯盤結束。'); return 0
        sleep(a.interval)

if __name__ == '__main__':
    try: sys.exit(main())
    except KeyboardInterrupt: print('\n已停止盯盤。'); sys.exit(0)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(str(exc) if isinstance(exc, ValueError) else '本機檔案或格式錯誤，請核對 .local/price-alerts.json。', file=sys.stderr)
        sys.exit(1)
