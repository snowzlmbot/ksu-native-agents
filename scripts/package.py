#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, posixpath, re, stat, subprocess, tarfile, tempfile, zipfile
from pathlib import Path
VERSION='0.1.0-rc7'; CODE=107
APPS={
 'openclaw': {'id':'ksu_openclaw','upstream':'OpenClaw 2026.10.7','port':18789},
 'hermes': {'id':'ksu_hermes','upstream':'Hermes Agent v0.22.5 commit bf0203a794a07aac3ff764972ab9087baa4e4f4e','port':9119},
}

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()

def safe_member(m: tarfile.TarInfo):
 n=m.name
 if n.startswith('/') or '\x00' in n: raise ValueError('absolute/NUL tar member')
 parts=Path(n).parts
 if '..' in parts or not n or len(n)>4096: raise ValueError('unsafe tar member '+n)
 if m.isdev() or m.isfifo(): raise ValueError('device/FIFO forbidden '+n)
 if m.issym() or m.islnk():
  target=m.linkname
  if '\x00' in target: raise ValueError('NUL link '+n)
  if target.startswith('/'):
   allowed=('/bin','/sbin','/lib','/usr','/etc','/opt','/var','/root','/home','/workspace','/tmp','/run','/media','/mnt','/srv')
   if not any(target==a or target.startswith(a+'/') for a in allowed): raise ValueError('host/control absolute link '+n)
  else:
   resolved=posixpath.normpath(posixpath.join(posixpath.dirname(n),target))
   if resolved in ('.','..') or resolved.startswith('../'): raise ValueError('link escapes root '+n)


def validate_rootfs(p):
 with tarfile.open(p,'r:*') as t:
  for m in t: safe_member(m)

def copy_tree(src,dst,app):
 dst.mkdir(parents=True,exist_ok=False)
 for x in ('module/common',):
  pass

def make(app,rootfs,binary,out,include_payload=True):
 if app not in APPS: raise ValueError('app')
 if include_payload: validate_rootfs(rootfs)
 with tempfile.TemporaryDirectory(prefix='ksu-package-') as td:
  t=Path(td); mod=t/'module'; (mod/'bin').mkdir(parents=True); (mod/'payload').mkdir()
  common=Path(__file__).parents[1]/'module/common'
  for name in ('service.sh','uninstall.sh','action.sh','agentctl','termux','boot-completed.sh'):
   text=(common/name).read_text().replace('@APP@',app)
   (mod/name).write_text(text); os.chmod(mod/name,0o700)
  custom=(common/'customize.sh').read_text().replace('@APP@',app).replace('VERSION=0.1.0-rc1',f'VERSION={VERSION}')
  (mod/'customize.sh').write_text(custom); os.chmod(mod/'customize.sh',0o700)
  web=(mod/'webroot'); web.mkdir(); (web/'index.html').write_text((common/'webroot/index.html').read_text().replace('@APP@',app))
  (mod/'agentctl').write_text((common/'agentctl').read_text().replace('@APP@',app)); os.chmod(mod/'agentctl',0o700)
  # Native Termux/MT-facing command launcher with bounded logs and storage diagnostics.
  (mod/'termux').write_text((common/'termux').read_text().replace('@APP@',app)); os.chmod(mod/'termux',0o700)
  prop=f'id={APPS[app]["id"]}\nname=KSU Native {app}\nversion={VERSION}\nversionCode={CODE}\nauthor=snowzlmbot\nupdateJson=https://raw.githubusercontent.com/snowzlmbot/ksu-native-agents/master/updates/{app}.json\ndescription=Ubuntu ARM64 native {app}; private mount namespace; persistent host RW mappings; data retained on uninstall\n'
  (mod/'module.prop').write_text(prop)
  import shutil
  shutil.copy2(binary,mod/'bin/ksu-agent'); os.chmod(mod/'bin/ksu-agent',0o700)
  if include_payload:
   shutil.copy2(rootfs,mod/'payload/rootfs.tar.xz')
   (mod/'payload/README.txt').write_text('Verified Ubuntu 26.04.1 ARM64 rootfs; payload marker opt/ksu-agent/payload-complete required.\\n')
   (mod/'payload/MANIFEST.json').write_text(json.dumps({'app':app,'moduleVersion':VERSION,'upstream':APPS[app]['upstream'],'rootfsSha256':sha(rootfs),'agentSha256':sha(binary)},indent=2)+'\\n')
  else:
   (mod/'payload/README.txt').write_text('Device-local install: reuses an already verified /data/adb/ai-containers payload.\\n')
   (mod/'payload/MANIFEST.json').write_text(json.dumps({'app':app,'moduleVersion':VERSION,'deviceLocalPayload':True,'agentSha256':sha(binary)},indent=2)+'\\n')
  sums=[]
  for p in sorted(x for x in mod.rglob('*') if x.is_file() and x.name!='SHA256SUMS'):
   sums.append(f'{sha(p)}  {p.relative_to(mod)}')
  (mod/'SHA256SUMS').write_text('\n'.join(sums)+'\n')
  out.parent.mkdir(parents=True,exist_ok=True); out.unlink(missing_ok=True)
  with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
   for p in sorted(mod.rglob('*')):
    if p.is_file():
     info=zipfile.ZipInfo(str(p.relative_to(mod)).replace(os.sep,'/'))
     info.external_attr=(p.stat().st_mode & 0xffff)<<16
     z.writestr(info,p.read_bytes(),compress_type=zipfile.ZIP_DEFLATED)
 print(json.dumps({'output':str(out),'sha256':sha(out),'app':app,'version':VERSION}))

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--app',required=True);ap.add_argument('--rootfs',type=Path,required=True);ap.add_argument('--binary',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--device-local',action='store_true');a=ap.parse_args();make(a.app,a.rootfs,a.binary,a.output,not a.device_local)
