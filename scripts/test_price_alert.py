import io,json,sys,tempfile,threading,unittest
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import price_alert as pa
import telegram_notify as tg
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'stock-picker'))
import serve

NOW=datetime(2026,10,6,10,15,tzinfo=pa.TAIPEI)
class Response(io.BytesIO):pass
def mis(*rows):return lambda request,timeout:Response(json.dumps({'msgArray':list(rows)}).encode())

class PriceAlertTests(unittest.TestCase):
    def alert(self,**kw):return pa.validate_alert({'symbol':'2330','price':1100,**kw})
    def test_channel_targets_accepted(self):
        self.assertTrue(tg.valid_target('@ai_alchemy_tw'));self.assertTrue(tg.valid_target('-1001234567890'));self.assertTrue(tg.valid_target('12345'))
        self.assertFalse(tg.valid_target('@ab'));self.assertFalse(tg.valid_target('https://t.me/x'))
    def test_validation_rejects_bad_plans(self):
        for bad in ({'symbol':'ABC','price':10},{'symbol':'2330','price':0},{'symbol':'2330','price':10,'condition':'near'},{'symbol':'2330','price':float('nan')}):
            with self.assertRaises(ValueError):pa.validate_alert(bad)
        with self.assertRaises(ValueError):pa.validate_alerts([{'symbol':'2330','price':1},{'symbol':'2330','price':2}])
        with self.assertRaises(ValueError):pa.validate_alerts([{'symbol':str(1000+i),'price':1} for i in range(21)])
    def test_mis_uses_trade_not_yesterday_close(self):
        q=pa.parse_mis({'msgArray':[{'c':'2330','n':'台積電','z':'-','pz':'1095','y':'1000','d':'20261006','t':'10:15:00'},{'c':'6533','z':'-','pz':'-','y':'300'}]})
        self.assertEqual(q['2330']['price'],1095);self.assertEqual(q['2330']['basis'],'前一筆成交');self.assertNotIn('6533',q)
    def test_busy_stock_without_trade_uses_executable_side(self):
        # Shape of a real 2026-10-06 09:22 snapshot for 2330: no z/pz, only bid/ask.
        q=pa.parse_mis({'msgArray':[{'c':'2330','n':'台積電','z':'-','pz':'-','y':'2575.0000','a':'2580.0000_2585.0000_','b':'2575.0000_2570.0000_','d':'20261006','t':'09:22:25'},{'c':'','z':'-'}]})
        self.assertIsNone(q['2330']['price']);self.assertEqual(list(q),['2330'])
        sent=[];alerts=[self.alert(price=2575),self.alert(symbol='2330',price=2578,condition='lte')]
        self.assertEqual(pa.check_once(alerts[:1],q,sent.append,NOW),['2330']);self.assertIn('最佳買價',sent[0])
        self.assertEqual(pa.check_once(alerts[1:],q,sent.append,NOW),[])
    def test_fetch_batches_listed_and_otc_in_one_request(self):
        seen=[]
        def opener(request,timeout):seen.append(request.full_url);return mis({'c':'6533','z':'280'})(request,timeout)
        self.assertEqual(pa.fetch_quotes(['2330','6533'],opener)['6533']['price'],280)
        self.assertEqual(len(seen),1);self.assertIn('tse_2330.tw|otc_2330.tw|tse_6533.tw|otc_6533.tw',seen[0])
    def test_trigger_once_and_message_has_plan(self):
        alerts=[self.alert(stop=1050,note='突破前高'),self.alert(symbol='6533',price=300,condition='lte')]
        sent=[];quotes={'2330':dict(price=1105,name='台積電',time='10:15',basis='最新成交',source='證交所MIS'),'6533':dict(price=310,name='晶心科',time='10:15',basis='最新成交',source='證交所MIS')}
        self.assertEqual(pa.check_once(alerts,quotes,sent.append,NOW),['2330'])
        self.assertEqual(alerts[0]['status'],'triggered');self.assertIn('停損：1,050',sent[0]);self.assertIn('不是下單',sent[0])
        self.assertEqual(pa.check_once(alerts,quotes,sent.append,NOW),[]);self.assertEqual(len(sent),1)
    def test_failed_send_is_not_retried(self):
        alerts=[self.alert()]
        def fail(text):raise ValueError('傳送狀態不明')
        with self.assertRaises(ValueError):pa.check_once(alerts,{'2330':dict(price=1200,name='',time='',basis='',source='')},fail,NOW)
        self.assertEqual(alerts[0]['status'],'check_delivery')
    def test_trading_window(self):
        self.assertTrue(pa.is_trading_time(NOW));self.assertFalse(pa.is_trading_time(NOW.replace(hour=13,minute=31)))
        self.assertFalse(pa.is_trading_time(datetime(2026,10,10,10,0,tzinfo=pa.TAIPEI)))
    def test_interval_floor(self):
        with self.assertRaises(ValueError):pa.main(['--interval','60'])
    def test_dry_run_and_fake_price_never_change_state_or_read_token(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'alerts.json';pa.save_alerts([self.alert()],path)
            with patch.object(tg,'credentials',side_effect=AssertionError('secret read')),redirect_stdout(io.StringIO()) as out:
                pa.main(['--alerts',str(path),'--dry-run'],now=lambda tz:NOW,opener=mis({'c':'2330','z':'1101'}))
            self.assertIn('預覽（未傳送）',out.getvalue());self.assertNotIn('模擬',out.getvalue());self.assertEqual(pa.load_alerts(path)[0]['status'],'watching')
            sent=[]
            with patch.object(tg,'credentials',return_value=('1:x','@chan')),patch.object(tg,'send_one',side_effect=lambda t,c,text,o:sent.append(text)),redirect_stdout(io.StringIO()):
                pa.main(['--alerts',str(path),'--fake-price','2330=1100'],now=lambda tz:NOW)
            self.assertIn('課堂模擬價格',sent[0]);self.assertEqual(pa.load_alerts(path)[0]['status'],'watching')
    def test_loop_waits_outside_market_and_stops_after_all_fire(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'alerts.json';pa.save_alerts([self.alert()],path)
            times=iter([NOW.replace(hour=8),NOW]);slept=[]
            with patch.object(tg,'credentials',return_value=('1:x','1')),patch.object(tg,'send_one',return_value=9),redirect_stdout(io.StringIO()):
                pa.main(['--alerts',str(path)],now=lambda tz:next(times),sleep=slept.append,opener=mis({'c':'2330','z':'1100'}))
            self.assertEqual(slept,[300]);self.assertEqual(pa.load_alerts(path)[0]['status'],'triggered')

class LocalServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();local=Path(self.tmp.name)
        self.patches=[patch.object(serve,'LOCAL',local),patch.object(serve,'ENV',local/'telegram.env'),patch.object(serve,'ALERTS',local/'price-alerts.json')]
        for p in self.patches:p.start()
        self.server=serve.http.server.ThreadingHTTPServer(('127.0.0.1',0),serve.Handler)
        threading.Thread(target=self.server.serve_forever,daemon=True).start()
        self.base=f'http://127.0.0.1:{self.server.server_port}'
    def tearDown(self):
        self.server.shutdown();self.server.server_close()
        for p in self.patches:p.stop()
        self.tmp.cleanup()
    def call(self,path,body=None,origin=None):
        headers={'Content-Type':'application/json'}
        if origin:headers['Origin']=origin
        req=Request(self.base+path,data=None if body is None else json.dumps(body).encode(),headers=headers,method='GET' if body is None else 'POST')
        try:
            with urlopen(req,timeout=5) as r:return r.status,json.loads(r.read())
        except HTTPError as e:return e.code,json.loads(e.read())
    def test_token_is_write_only(self):
        status,_=self.call('/api/telegram',{'token':'123456:SECRET_value','chat_id':'@ai_alchemy_tw'})
        self.assertEqual(status,200)
        status,body=self.call('/api/alerts')
        self.assertTrue(body['telegram']['configured']);self.assertNotIn('SECRET',json.dumps(body))
        self.assertIn('SECRET_value',(serve.ENV).read_text(encoding='utf-8'))
        status,_=self.call('/api/telegram',{'token':'','chat_id':'-1001234567890'})
        self.assertEqual(status,200);self.assertIn('SECRET_value',serve.ENV.read_text(encoding='utf-8'))
    def test_rejects_other_websites(self):
        status,_=self.call('/api/telegram',{'token':'1:a','chat_id':'1'},origin='https://evil.example')
        self.assertEqual(status,403);self.assertFalse(serve.ENV.exists())
    def test_save_keeps_fired_status_unless_reset_or_plan_changed(self):
        self.assertEqual(self.call('/api/alerts',{'alerts':[{'symbol':'2330','price':1100}]})[0],200)
        alerts=pa.load_alerts(serve.ALERTS);alerts[0].update(status='triggered',triggered_at='2026-10-06T10:15:00+08:00',triggered_price=1101);pa.save_alerts(alerts,serve.ALERTS)
        _,body=self.call('/api/alerts',{'alerts':[{'symbol':'2330','price':1100,'note':'改備註'}]})
        self.assertEqual(body['alerts'][0]['status'],'triggered')
        _,body=self.call('/api/alerts',{'alerts':[{'symbol':'2330','price':1100,'reset':True}]})
        self.assertEqual(body['alerts'][0]['status'],'watching')
    def test_invalid_alert_reports_reason(self):
        status,body=self.call('/api/alerts',{'alerts':[{'symbol':'2330','price':-1}]})
        self.assertEqual(status,400);self.assertIn('進場價',body['error'])

if __name__=='__main__':unittest.main()
