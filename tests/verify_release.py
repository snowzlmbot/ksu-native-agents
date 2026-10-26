#!/usr/bin/env python3
"""Verify shipped ZIP bytes, manifests and runtime/source parity before publishing."""
import hashlib, json, stat, subprocess, sys, tempfile, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REQ={'module.prop','skip_mount','customize.sh','service.sh','boot-completed.sh','deploy-runtime.sh',
     'termux','native','agentctl','webroot/index.html','runtime/bootstrap.py','runtime/start.sh',
     'runtime/model-config.py','runtime/model-quick.sh','runtime/storage-clean.py','runtime/force-hermes-zh.py','SHA256SUMS','bin/ksu-agent'}

def digest(z,name):
    h=hashlib.sha256()
    with z.open(name) as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

results=[]
for path in sorted((ROOT/'dist').glob('ksu_*-0.1.0-rc10-*.zip')):
    print('checking',path.name,flush=True)
    with zipfile.ZipFile(path) as z:
        names=set(z.namelist()); assert REQ<=names,REQ-names
        assert not any(n.startswith(('system/','webroot/.env','home/')) for n in names)
        assert z.testzip() is None
        for line in z.read('SHA256SUMS').decode().splitlines():
            value,name=line.split('  ',1); assert digest(z,name)==value,(path.name,name)
        prop=z.read('module.prop').decode(); assert 'version=0.1.0-rc10' in prop and 'versionCode=110' in prop
        custom=z.read('customize.sh').decode(); assert 'VERSION=0.1.0-rc10' in custom and '@APP@' not in custom
        json.loads(z.read('payload/MANIFEST.json'))
        assert ('payload/rootfs.tar.xz' in names)==('-full.zip' in path.name)
        for name in names:
            if name.startswith('runtime/'):
                source=ROOT/('module/common/model-quick.sh' if name.endswith('model-quick.sh') else 'src/'+Path(name).name)
                assert z.read(name)==source.read_bytes(),name
        with tempfile.TemporaryDirectory() as td:
            js=Path(td)/'webui.js'
            js.write_text(z.read('webroot/index.html').decode().split('<script>')[1].split('</script>')[0])
            subprocess.run(['node','--check',str(js)],check=True)
        with path.open('rb') as f: h=hashlib.file_digest(f,'sha256').hexdigest()
        results.append({'file':path.name,'size':path.stat().st_size,'sha256':h,'full':('-full.zip' in path.name),'verified':True})
(ROOT/'dist/package-validation.json').write_text(json.dumps({'ok':True,'scope':'shipped ZIP bytes, hashes, syntax and source parity; not a device install or live model call','assets':results},indent=2)+'\n')
(ROOT/'dist/SHA256SUMS').write_text(''.join(f"{r['sha256']}  {r['file']}\n" for r in results))
print(json.dumps({'ok':True,'verifiedPackages':len(results)}))
assert len(results)==4
