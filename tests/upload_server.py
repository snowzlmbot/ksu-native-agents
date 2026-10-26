from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import os
OUT=Path('/var/minis/workspace/projects/ksu-native-agents/dist')
OUT.mkdir(parents=True,exist_ok=True)
class H(BaseHTTPRequestHandler):
 def do_PUT(self):
  name=Path(self.path).name
  if name not in ('openclaw-rootfs.tar.xz','hermes-rootfs.tar.xz','openclaw-rootfs.tar.gz','hermes-rootfs.tar.gz'):
   self.send_error(403); return
  dst=OUT/name; tmp=dst.with_suffix(dst.suffix+'.part')
  length=self.headers.get('Content-Length')
  remaining=int(length) if length else None
  with open(tmp,'wb') as f:
   while remaining is None or remaining:
    b=self.rfile.read(min(1024*1024,remaining) if remaining else 1024*1024)
    if not b: break
    f.write(b)
    if remaining is not None: remaining-=len(b)
  os.replace(tmp,dst)
  self.send_response(201); self.end_headers(); self.wfile.write(b'ok\n')
 def log_message(self,fmt,*args): print(fmt%args,flush=True)
HTTPServer(('127.0.0.1',18792),H).serve_forever()
