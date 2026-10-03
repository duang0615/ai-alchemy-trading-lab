"""Loopback-only local viewer. Serves generated data; never exposes login or env."""
import argparse,http.server,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT),**kwargs)
    def do_GET(self):
        if self.path.split('?')[0]=='/local-data.json':
            p=ROOT.parent/'.local'/'stock-picker-data.json'
            if not p.exists():self.send_error(404,'Run build_data.py first');return
            b=p.read_bytes();self.send_response(200);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
        else:super().do_GET()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8766);a=p.parse_args()
    print(f'Open http://127.0.0.1:{a.port}/ — only accessible on this computer',flush=True)
    http.server.ThreadingHTTPServer(('127.0.0.1',a.port),Handler).serve_forever()
