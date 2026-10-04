import io,json,tempfile,unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
import telegram_notify as tg

class TelegramNotifyTests(unittest.TestCase):
    def test_preview_never_reads_credentials_or_calls_network(self):
        with tempfile.TemporaryDirectory() as d, patch.object(tg,'credentials',side_effect=AssertionError('secret read')),patch.object(tg,'send_one',side_effect=AssertionError('network')):
            with redirect_stdout(io.StringIO()):tg.main(['--demo','--output',str(Path(d)/'preview.txt')])
            content=(Path(d)/'preview.txt').read_text(encoding='utf-8')
            self.assertIn('2026-10-02',content);self.assertIn('16檔',content);self.assertIn('候選：10檔',content)
    def test_emoji_utf16_and_lossless_split(self):
        source='😀台股\n'*2100
        parts=tg.chunks(source)
        self.assertEqual(''.join(parts),source)
        self.assertTrue(all(len(p.encode('utf-16-le'))//2<=4000 for p in parts))
    def test_empty_rejected(self):
        with self.assertRaises(ValueError):tg.chunks(' ')
    def test_zero_candidates_are_explicit(self):
        self.assertIn('本次沒有符合的候選',tg.sample_message(minimum=1e9))
    def test_csv_requires_metadata(self):
        with self.assertRaises(ValueError):tg.csv_message('missing.csv',None,None)
    def test_csv_handles_pattern_export_bom_and_headers(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'pattern.csv'
            p.write_text('股號,名稱,型態,相似度_非勝率\n3707,漢磊,W底,85.72\n',encoding='utf-8-sig')
            content=tg.csv_message(p,'2026-10-02','W底；18檔教學樣本')
            self.assertIn('候選 1檔',content);self.assertIn('股號：3707',content)
            self.assertIn('相似度_非勝率：85.72',content)
    def test_http_error_hides_authenticated_url(self):
        def rejected(request,timeout):raise HTTPError(request.full_url,403,'denied',{},None)
        with self.assertRaises(ValueError) as ctx:tg.send_one('redaction-test','1','hello',rejected)
        self.assertNotIn('redaction-test',str(ctx.exception));self.assertNotIn('https:',str(ctx.exception))
    def test_sender_payload_and_ack(self):
        class Response(io.BytesIO):pass
        observed={}
        def sender(request,timeout):
            observed.update(json.loads(request.data))
            return Response(json.dumps({'ok':True,'result':{'message_id':7}}).encode())
        self.assertEqual(tg.send_one('unit-test','123','多頭排列 & <5%',sender),7)
        self.assertEqual(observed['chat_id'],'123');self.assertEqual(observed['text'],'多頭排列 & <5%')
        self.assertNotIn('parse_mode',observed);self.assertNotIn('allow_paid_broadcast',observed)

if __name__=='__main__':unittest.main()
