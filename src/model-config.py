#!/usr/bin/python3
"""Local-only model route configuration; no key in argv, logs or status output."""
import base64, getpass, json, os, re, subprocess, sys, tempfile
from pathlib import Path
from urllib.parse import urlsplit

APP = os.environ.get('KSU_AGENT', '')
HOME = Path('/root/.hermes' if APP == 'hermes' else '/root/.openclaw')

def validate(data):
    provider=str(data.get('provider','')).strip()
    model=str(data.get('model','')).strip()
    base=str(data.get('base_url','')).strip().rstrip('/')
    key=str(data.get('key_env') or 'KSU_MODEL_API_KEY').strip()
    if not re.fullmatch(r'[a-z][a-z0-9_-]{0,63}',provider):
        raise ValueError('提供商 ID 只能使用小写字母、数字、_ 和 -，以字母开头')
    if not model or len(model)>256 or any(ord(c)<32 for c in model):
        raise ValueError('模型 ID 不能为空或包含控制字符')
    u=urlsplit(base)
    if u.scheme not in ('https','http') or not u.hostname or u.username or u.password or u.query or u.fragment:
        raise ValueError('接口地址必须是无用户名/密码/查询参数的 HTTP(S) URL')
    if u.scheme=='http' and u.hostname not in ('localhost','127.0.0.1','::1'):
        raise ValueError('远程模型接口必须使用 HTTPS；HTTP 仅允许本机回环')
    if not re.fullmatch(r'[A-Z][A-Z0-9_]{0,127}',key) or not key.endswith('_API_KEY'):
        raise ValueError('密钥变量名必须以 _API_KEY 结尾，例如 KSU_MODEL_API_KEY')
    return {'provider':provider,'model':model,'base_url':base,'key_env':key}

def patch_for(d):
    p,m=d['provider'],d['model']
    return {'models':{'mode':'merge','providers':{p:{'baseUrl':d['base_url'],
        'api':'openai-completions','apiKey':{'source':'env','provider':'default','id':d['key_env']},
        'models':[{'id':m,'name':m,'input':['text'],'contextWindow':32768,'maxTokens':4096}]}}},
        'agents':{'defaults':{'model':{'primary':p+'/'+m}}}}

def invoke(argv):
    r=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    if r.returncode:
        raise RuntimeError('应用配置命令失败；原配置由应用自身保留。请在原生终端运行 config check/validate 诊断。')

def save_key(name,value):
    if not value or '\n' in value or '\r' in value or '\x00' in value:
        raise ValueError('密钥不能为空或包含换行')
    path=HOME/'.env'
    if path.is_symlink(): raise ValueError('拒绝符号链接 .env')
    text=path.read_text() if path.exists() else ''
    lines=[s for s in text.splitlines() if not s.lstrip().startswith((name+'=', 'export '+name+'='))]
    lines.append(name+'='+json.dumps(value,ensure_ascii=False))
    fd,tmp=tempfile.mkstemp(prefix='.ksu-env-',dir=HOME)
    try:
        os.fchmod(fd,0o600)
        with os.fdopen(fd,'w') as f: f.write('\n'.join(lines)+'\n'); f.flush(); os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        Path(tmp).unlink(missing_ok=True)

def apply(data):
    d=validate(data)
    if APP=='hermes':
        entry={'api':d['base_url'],'api_key':'${'+d['key_env']+'}',
            'transport':'openai_chat','models':[d['model']]}
        model={'provider':d['provider'],'default':d['model'],
            'base_url':d['base_url'],'api_mode':'chat_completions','key_env':d['key_env']}
        invoke(['/usr/local/bin/hermes','config','set','providers.'+d['provider'],json.dumps(entry)])
        invoke(['/usr/local/bin/hermes','config','set','model',json.dumps(model)])
    else:
        fd,tmp=tempfile.mkstemp(prefix='ksu-model-',suffix='.json',dir='/tmp')
        try:
            with os.fdopen(fd,'w') as f: json.dump(patch_for(d),f)
            invoke(['/usr/local/bin/openclaw','config','patch','--file',tmp])
        finally: Path(tmp).unlink(missing_ok=True)
    print(json.dumps({'ok':True,**d,'note':'已保存路由。请在终端 model key 安全输入密钥，重启服务后新会话生效；未发起付费推理。'},ensure_ascii=False))

def show():
    if APP=='hermes':
        sys.path.insert(0,'/opt/hermes-agent')
        from pm.environments import selected_venv, site_packages
        sys.path.insert(0,str(site_packages(selected_venv(Path('/opt/hermes-agent')))))
        from hermes_cli.config import read_user_config_raw
        cfg=read_user_config_raw(HOME/'config.yaml')
        model=cfg.get('model') or {}
        if not isinstance(model,dict): model={'default':str(model)}
        d={k:model.get(k,'') for k in ('provider','default','base_url','key_env','api_mode')}
    else:
        cfg=json.loads((HOME/'openclaw.json').read_text())
        d={'primary':cfg.get('agents',{}).get('defaults',{}).get('model',{})}
        d['providers']={p:{'baseUrl':v.get('baseUrl'),'api':v.get('api'),
            'models':[x.get('id') for x in v.get('models',[]) if isinstance(x,dict)]}
            for p,v in cfg.get('models',{}).get('providers',{}).items() if isinstance(v,dict)}
    print(json.dumps(d,ensure_ascii=False,indent=2))

def main():
    if APP not in ('openclaw','hermes'): raise ValueError('KSU_AGENT 无效')
    args=sys.argv[1:]; op=args.pop(0) if args else 'show'
    if op=='show': show()
    elif op=='set':
        if len(args)!=4: raise ValueError('set 需要四个 Base64 参数：provider model base_url key_env')
        apply(dict(zip(('provider','model','base_url','key_env'),[base64.b64decode(x,validate=True).decode() for x in args])))
    elif op=='wizard':
        d=validate({'provider':input('提供商 ID [custom]: ').strip() or 'custom',
            'model':input('模型 ID: '),'base_url':input('接口地址: '),
            'key_env':input('密钥变量 [KSU_MODEL_API_KEY]: ').strip() or 'KSU_MODEL_API_KEY'})
        value=getpass.getpass('API Key（不回显；留空保留原值）: ')
        if value: save_key(d['key_env'],value)
        apply(d)
    elif op=='key':
        name=args[0] if args else 'KSU_MODEL_API_KEY'
        if not re.fullmatch(r'[A-Z][A-Z0-9_]{0,110}_API_KEY',name): raise ValueError('只允许 *_API_KEY 密钥变量')
        if not sys.stdin.isatty(): raise ValueError('请在 MT/Termux 交互终端安全输入密钥')
        save_key(name,getpass.getpass(name+'（不回显）: ')); print('密钥已安全写入 .env，未显示')
    else: raise ValueError('model show | wizard | key [ENV_NAME] | set <四个Base64参数>')

if __name__=='__main__':
    try: main()
    except (Exception,KeyboardInterrupt) as e:
        print('模型配置失败：'+(str(e) if isinstance(e,(ValueError,RuntimeError)) else type(e).__name__),file=sys.stderr)
        sys.exit(1)
