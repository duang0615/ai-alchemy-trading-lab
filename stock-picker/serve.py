"""Loopback-only local viewer. Serves generated data; never exposes login or env.

The watchlist page may write the student's own Telegram settings and price alerts
into ../.local. The token is write-only: no endpoint ever returns it.
"""
import argparse,http.server,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
LOCAL=ROOT.parent/'.local'
sys.path.insert(0,str(ROOT.parent/'scripts'))
import telegram_notify as tg  # noqa: E402
import price_alert as pa  # noqa: E402
ENV=LOCAL/'telegram.env'
ALERTS=LOCAL/'price-alerts.json'
LOCAL_HOSTS=('127.0.0.1','localhost')

def telegram_status():
    try:values=tg.read_env(ENV) if ENV.exists() else {}
    except OSError:values={}
    token,target=values.get('TELEGRAM_BOT_TOKEN',''),values.get('TELEGRAM_CHAT_ID','')
    hint=target if target.startswith('@') else ('…'+target[-4:] if target else '')
    return dict(configured=tg.valid_token(token) and tg.valid_target(target),has_token=tg.valid_token(token),target_hint=hint)

def write_telegram(token,target):
    token,target=(token or '').strip(),(target or '').strip()
    if not token and ENV.exists():token=tg.read_env(ENV).get('TELEGRAM_BOT_TOKEN','')
    if not tg.valid_token(token):raise ValueError('Bot Token 格式不對，應像 123456789:AA… ；請從 BotFather 複製。')
    if not tg.valid_target(target):raise ValueError('頻道格式不對：填 @頻道名稱、-100 開頭的頻道 ID，或自己的數字聊天 ID。')
    LOCAL.mkdir(parents=True,exist_ok=True)
    ENV.write_text(f'TELEGRAM_BOT_TOKEN={token}\nTELEGRAM_CHAT_ID={target}\n',encoding='utf-8')

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT),**kwargs)
    def reply(self,status,payload):
        b=json.dumps(payload,ensure_ascii=False).encode('utf-8')
        self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
    def same_machine(self):
        # Blocks other websites (CSRF) and DNS-rebinding hosts from writing local settings.
        host=(self.headers.get('Host') or '').rsplit(':',1)[0]
        origin=self.headers.get('Origin')
        return host in LOCAL_HOSTS and (origin is None or origin.split('://',1)[-1].rsplit(':',1)[0] in LOCAL_HOSTS)
    def do_GET(self):
        path=self.path.split('?')[0]
        local_files={'/local-data.json':'stock-picker-data.json','/local-pattern-data.json':'pattern-data.json'}
        if path=='/api/alerts':
            if not self.same_machine():return self.reply(403,{'error':'只接受本機連線。'})
            try:alerts=pa.load_alerts(ALERTS)
            except (ValueError,OSError,json.JSONDecodeError):alerts=[]
            return self.reply(200,{'alerts':alerts,'telegram':telegram_status(),'limits':{'max_symbols':pa.MAX_SYMBOLS,'interval_seconds':pa.MIN_INTERVAL}})
        if path in local_files:
            p=LOCAL/local_files[path]
            if not p.exists():self.send_error(404,'Run build_data.py first');return
            b=p.read_bytes();self.send_response(200);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
        else:super().do_GET()
    def do_POST(self):
        path=self.path.split('?')[0]
        if not self.same_machine():return self.reply(403,{'error':'只接受本機連線。'})
        if 'application/json' not in (self.headers.get('Content-Type') or ''):return self.reply(415,{'error':'需要 JSON。'})
        size=int(self.headers.get('Content-Length') or 0)
        if size>65536:return self.reply(413,{'error':'設定太大。'})
        try:body=json.loads(self.rfile.read(size) or b'{}')
        except json.JSONDecodeError:return self.reply(400,{'error':'JSON 格式錯誤。'})
        try:
            if path=='/api/alerts':
                incoming=body.get('alerts');alerts=pa.validate_alerts(incoming)
                try:stored={x['symbol']:x for x in pa.load_alerts(ALERTS)}
                except (ValueError,OSError,json.JSONDecodeError):stored={}
                # The monitor may have fired after this page loaded: keep that result unless the plan changed or the student reset it.
                for alert,raw in zip(alerts,incoming):
                    old=stored.get(alert['symbol'])
                    if old and old['status']!='watching' and not raw.get('reset') and (old['price'],old['condition'])==(alert['price'],alert['condition']):
                        alert.update(status=old['status'],triggered_at=old['triggered_at'],triggered_price=old['triggered_price'])
                    elif raw.get('reset') or (old and (old['price'],old['condition'])!=(alert['price'],alert['condition'])):
                        alert.update(status='watching',triggered_at=None,triggered_price=None)
                pa.save_alerts(alerts,ALERTS)
                return self.reply(200,{'alerts':alerts,'saved':len(alerts)})
            if path=='/api/telegram':
                write_telegram(body.get('token'),body.get('chat_id'));return self.reply(200,{'telegram':telegram_status()})
            if path=='/api/telegram/test':
                if not ENV.exists():raise ValueError('還沒設定 Telegram，請先填 Bot Token 與頻道並存到本機。')
                token,target=tg.credentials(ENV)
                message_id=tg.send_one(token,target,'AI 煉金術｜Telegram 設定測試\n收到這則，代表到價進場通知會送到這裡。')
                return self.reply(200,{'message_id':message_id})
        except ValueError as exc:return self.reply(400,{'error':str(exc)})
        self.reply(404,{'error':'沒有這個功能。'})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8766);a=p.parse_args()
    print(f'Open http://127.0.0.1:{a.port}/ — only accessible on this computer',flush=True)
    http.server.ThreadingHTTPServer(('127.0.0.1',a.port),Handler).serve_forever()
