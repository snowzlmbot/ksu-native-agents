#!/usr/bin/env python3
"""Release regression checks; never reads device secrets or installs modules."""
import base64, importlib.util, json, os, re, subprocess, tempfile, zipfile, hashlib
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[1]
checks=[]

def done(name): checks.append({'check':name,'passed':True}); print('PASS',name,flush=True)

def main():
    for p in (PROJECT/'module/common').iterdir():
        if p.is_file(): subprocess.run(['sh','-n',str(p)],check=True)
    subprocess.run(['bash','-n',str(PROJECT/'module/common/model-quick.sh')],check=True)
    done('all shell syntax')
    spec=importlib.util.spec_from_file_location('model_config',PROJECT/'src/model-config.py')
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    d=mod.validate({'provider':'custom','model':'qwen/test-model','base_url':'https://example.test/v1','key_env':'KSU_MODEL_API_KEY'})
    assert mod.patch_for(d)['agents']['defaults']['model']['primary']=='custom/qwen/test-model'
    for d in ({'provider':'../../x'},{'provider':'custom','model':'x','base_url':'https://user:pass@example.test/v1'},
        {'provider':'custom','model':'x','base_url':'http://example.test/v1'},
        {'provider':'custom','model':'x','base_url':'https://example.test/v1','key_env':'LD_PRELOAD'}):
        try: mod.validate(d)
        except ValueError: pass
        else: raise AssertionError('unsafe model input accepted')
    done('model validation and SecretRef patch')
    html=(PROJECT/'module/common/webroot/index.html').read_text()
    js=html.split('<script>')[1].split('</script>')[0].replace('@APP@','hermes')
    with tempfile.TemporaryDirectory() as td:
        t=Path(td); (t/'webui.js').write_text(js)
        subprocess.run(['node','--check',str(t/'webui.js')],check=True)
        # Fake native bridge only; tests real classic-script parsing and callbacks.
        runner="""const fs=require('fs'),vm=require('vm');const nodes={};const ctx={console,setTimeout,clearTimeout,btoa:s=>Buffer.from(s,'binary').toString('base64'),unescape,encodeURIComponent,confirm:()=>false,navigator:{clipboard:{writeText:async()=>{}}},document:{querySelector:s=>nodes[s]||(nodes[s]={textContent:'',value:''})}};ctx.window=ctx;ctx.ksu={moduleInfo:()=>JSON.stringify({id:'ksu_hermes'}),toast:()=>{},exec:(cmd,opt,cb)=>setTimeout(()=>ctx[cb](0,cmd.includes('status')?'hermes running pid=7':'# mappings',''),0)};vm.createContext(ctx);vm.runInContext(fs.readFileSync(process.argv[2],'utf8'),ctx);setTimeout(()=>{if(nodes['#status'].textContent!=='运行中'||typeof ctx.saveModel!=='function'||typeof ctx.showModel!=='function')process.exit(2);console.log('WebUI native bridge fixture OK')},100);"""
        (t/'runner.cjs').write_text(runner)
        subprocess.run(['node',str(t/'runner.cjs'),str(t/'webui.js')],check=True)
        done('WebUI parses and executes native callbacks')
        (t/'bin').mkdir(); (t/'termux').write_text((PROJECT/'module/common/termux').read_text().replace('@APP@','hermes'))
        (t/'bin/ksu-agent').write_text('#!/bin/sh\nfor a in "$@"; do printf "%s\\n" "$a"; done\n')
        (t/'bin/ksu-agent').chmod(0o700)
        args=['set']+[base64.b64encode(x.encode()).decode() for x in ('custom','qwen/test-model','https://example.test/v1','KSU_MODEL_API_KEY')]
        r=subprocess.run(['sh',str(t/'termux'),'model',*args],check=True,capture_output=True,text=True)
        assert r.stdout.splitlines()==['hermes','exec','/bin/bash','/opt/ksu-agent/model-quick.sh',*args]
        done('MT/Termux multi-argument forwarding')
    out=PROJECT/'dist/release-validation.json'
    out.write_text(json.dumps({'ok':True,'scope':'offline regression; not a device install or live inference test','checks':checks},ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__': main()
