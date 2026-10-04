"""Preview stock results or a text file, then optionally send to the user's Bot.

Only the explicit --send switch contacts Telegram. No credentials in arguments,
browser storage, public assets, or logs. Uses Python's standard library.
"""
import argparse
import csv
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]

def chunks(text, limit=4000):
    """Respect UTF-16 size even when the message contains emoji."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError('訊息不能空白。')
    result, current, size = [], [], 0
    for char in text:
        n = len(char.encode('utf-16-le')) // 2
        if size + n > limit:
            result.append(''.join(current)); current, size = [], 0
        current.append(char); size += n
    if current: result.append(''.join(current))
    return result

def credentials(env_path=None):
    values = dict(os.environ)
    if env_path:
        for raw in Path(env_path).read_text(encoding='utf-8-sig').splitlines():
            raw = raw.strip()
            if not raw or raw.startswith('#') or '=' not in raw: continue
            key, value = raw.split('=', 1)
            values[key.strip()] = value.strip().strip('\"\'')
    token = values.get('TELEGRAM_BOT_TOKEN', '').strip()
    target = values.get('TELEGRAM_CHAT_ID', '').strip()
    if not re.fullmatch(r'\d+:[A-Za-z0-9_-]+', token):
        raise ValueError('請在本機設定 TELEGRAM_BOT_TOKEN。')
    if not re.fullmatch(r'-?\d+', target):
        raise ValueError('請在本機設定數字 TELEGRAM_CHAT_ID（私人聊天或群組 ID）。')
    return token, target

def sample_message(strategy='trend', minimum=0, snapshot=None):
    data = json.loads(Path(snapshot or ROOT/'stock-picker/demo-data.json').read_text(encoding='utf-8-sig'))
    cards = json.loads((ROOT/'stock-picker/presets.json').read_text(encoding='utf-8-sig'))
    card = next((c for c in cards if c['id'] == strategy), None)
    if card is None: raise ValueError('策略不存在，請核對 presets.json 的 id。')
    rows = [r for r in data['rows'] if strategy in r.get('passes', []) and isinstance(r.get('volume'),(int,float)) and r['volume'] >= minimum]
    lines = ['AI 煉金術｜選股結果', f"資料日：{data['asof']}", f"資料來源：{data['source']}",
             f"範圍：{data['mode']}，{data['universe_count']}檔", f"條件：{card['title']}；最低量 {minimum:g} 張", f'候選：{len(rows)}檔']
    if not rows: lines.append('本次沒有符合的候選。')
    for r in rows: lines.append(f"{r['symbol']} {r.get('name','')}｜收盤 {r.get('price','不足')}｜量 {r['volume']:g} 張")
    lines.extend(['', '候選名單，尚需進出場與風險條件。'])
    if data['mode'] == 'teaching_sample': lines.append('歷史教學小樣本，非即時、非全市場。')
    return '\n'.join(lines)

def csv_message(path, date, rule):
    if not date or not rule: raise ValueError('CSV 必須補上 --date 資料日與 --rule 選股條件。')
    rows = list(csv.DictReader(Path(path).open(encoding='utf-8-sig',newline='')))
    lines = ['AI 煉金術｜選股結果', f'資料日：{date}', f'條件：{rule}', f'來源：使用者匯出的CSV；候選 {len(rows)}檔']
    if not rows: lines.append('本次沒有符合的候選。')
    for r in rows:
        symbol = next((r[k] for k in ('股票代號','股號','symbol') if k in r), None)
        if symbol is None: raise ValueError('CSV 缺少股票代號欄位。')
        lines.append('｜'.join(f'{k}：{v}' for k,v in r.items() if v not in ('',None)))
    lines.append('候選名單，尚需進出場與風險條件；範圍與公式請核對原匯出設定。')
    return '\n'.join(lines)

def send_one(token, target, text, opener=urlopen):
    payload = dict(chat_id=target, text=text, link_preview_options={'is_disabled': True})
    request = Request('https://api.telegram.org/bot'+token+'/sendMessage',
                      data=json.dumps(payload,ensure_ascii=False).encode('utf-8'),
                      headers={'Content-Type':'application/json'}, method='POST')
    try:
        with opener(request,timeout=20) as response:
            body = json.loads(response.read().decode('utf-8'))
    except HTTPError as exc:
        # Raw errors may contain the authenticated URL. Never echo them.
        raise ValueError(f'Telegram 拒絕傳送（HTTP {exc.code}）；核對 Token、聊天ID、/start與Bot權限。') from None
    except (URLError, TimeoutError, OSError, json.JSONDecodeError):
        raise ValueError('傳送狀態不明：請先看 Telegram 是否收到，避免直接重送。') from None
    if not body.get('ok'):
        raise ValueError('Telegram 未確認成功；請核對 Bot 與聊天設定。')
    result = body.get('result', {})
    if not isinstance(result.get('message_id'), int):
        raise ValueError('Telegram 回覆缺少訊息編號，請核對實際收件。')
    return result['message_id']

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    group=p.add_mutually_exclusive_group(required=True)
    group.add_argument('--demo',action='store_true');group.add_argument('--snapshot');group.add_argument('--csv');group.add_argument('--text-file')
    p.add_argument('--strategy',default='trend');p.add_argument('--min-volume',type=float,default=0)
    p.add_argument('--date');p.add_argument('--rule');p.add_argument('--env');p.add_argument('--send',action='store_true')
    p.add_argument('--output',default=str(ROOT/'.local/telegram-preview.txt'))
    a=p.parse_args(argv)
    if a.min_volume < 0: raise ValueError('最低量不能小於零。')
    if a.text_file: message=Path(a.text_file).read_text(encoding='utf-8-sig')
    elif a.csv: message=csv_message(a.csv,a.date,a.rule)
    else: message=sample_message(a.strategy,a.min_volume,a.snapshot)
    messages=chunks(message)
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(message,encoding='utf-8')
    print(message);print(f'\n已產生預覽，共 {len(messages)} 則。'+('' if a.send else ' 尚未傳送；核對後加 --send。'))
    if not a.send: return 0  # No reading secrets and no network in preview mode.
    token,target=credentials(a.env)
    receipt=dict(created_at=datetime.now(timezone.utc).isoformat(),message_sha256=hashlib.sha256(message.encode('utf-8')).hexdigest(),planned=len(messages),message_ids=[],status='in_progress')
    receipt_path=ROOT/'.local/telegram-send-receipt.json';receipt_path.parent.mkdir(parents=True,exist_ok=True)
    try:
        for text in messages:
            receipt['message_ids'].append(send_one(token,target,text))
            receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
        receipt['status']='api_acknowledged'
        print(f'Telegram 已回覆成功，共 {len(messages)} 則；請核對手機收到的內容。')
    except ValueError:
        receipt['status']='stopped_check_delivery_before_retry'
        raise
    finally:
        receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    return 0

if __name__=='__main__':
    try: sys.exit(main())
    except (ValueError, OSError, KeyError, json.JSONDecodeError) as exc:
        if isinstance(exc,ValueError): print(str(exc),file=sys.stderr)
        else: print('本機檔案或格式錯誤，請核對輸入檔案。',file=sys.stderr)
        sys.exit(1)
