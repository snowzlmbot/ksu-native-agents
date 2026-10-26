#!/usr/bin/python3
"""Idempotent first boot; generate local secrets without printing them."""
import json, os, secrets, shutil, subprocess
from pathlib import Path

def write_new(path: Path, value: str) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as out:
        out.write(value)

app = os.environ['KSU_AGENT']
if app == 'openclaw':
    home = Path('/root/.openclaw')
    home.mkdir(mode=0o700, exist_ok=True)
    token = secrets.token_urlsafe(36)
    config = {
        'gateway': {'mode': 'local', 'bind': 'loopback', 'port': 18789,
                    'auth': {'mode': 'token', 'token': token}},
        'agents': {'defaults': {'workspace': '/workspace', 'sandbox': {'mode': 'off'}}},
    }
    p = home / 'openclaw.json'
    if not p.exists():
        write_new(p, json.dumps(config, indent=2) + '\n')
        write_new(Path('/root/LOCAL-LOGIN.txt'), 'OpenClaw: http://127.0.0.1:18789/\nToken: ' + token + '\n')
    # Keep the rootfs safe for plugin temp workspaces; /tmp is mounted 1777 too.
    os.chmod('/tmp', 0o1777)
else:
    home = Path('/root/.hermes')
    home.mkdir(mode=0o700, exist_ok=True)
    stamp = Path('/opt/hermes-agent/install-stamp.json')
    if not stamp.exists():
        write_new(stamp, json.dumps({
            'schemaVersion': 2, 'commit': 'bf0203a794a07aac3ff764972ab9087baa4e4f4e',
            'commitDate': None, 'branch': None, 'dirty': False, 'source': 'ci',
            'distribution': 'docker', 'updateMechanism': 'external',
            'baseVersion': '0.22.5', 'displayVersion': '0.22.5', 'distance': 0,
            'payload': 'bootstrap', 'pmRuntime': '/root/.hermes/installs/ffad2f5543956651/pm-runtime', 'tag': None
        }, indent=2) + '\n')
    else:
        try:
            d=json.loads(stamp.read_text())
            d['pmRuntime']='/root/.hermes/installs/ffad2f5543956651/pm-runtime'
            stamp.write_text(json.dumps(d,indent=2)+'\n')
        except Exception:
            pass
    pmroot=Path('/root/.hermes/installs/ffad2f5543956651/pm-runtime')
    selected=pmroot/'selected.json'
    try:
        gen=json.loads(selected.read_text()).get('generation','')
        if gen.startswith('generations/'):
            marker=pmroot/'pm-runtime.json'
            marker.write_text(json.dumps({'python':gen+'/bin/python','sitePackages':gen+'/lib/python3.14/site-packages'})+'\n')
    except Exception:
        pass
    os.chmod('/tmp',0o1777)
    seed = Path('/opt/ksu-agent/home-seed/.hermes')
    if seed.exists():
        for item in seed.iterdir():
            dst = home / item.name
            if not dst.exists() and not dst.is_symlink():
                if item.is_dir():
                    shutil.copytree(item, dst, symlinks=True)
                else:
                    shutil.copy2(item, dst)
    for name in ('tools', 'installs'):
        dst = home / name
        if not dst.exists() and not dst.is_symlink():
            dst.symlink_to('/opt/ksu-hermes-runtime/' + name)
    env = home / '.env'
    if not env.exists():
        import base64, hashlib
        def hash_password(password: str) -> str:
            salt = secrets.token_bytes(16)
            digest = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)
            return 'scrypt$16384$8$1$' + base64.b64encode(salt).decode() + '$' + base64.b64encode(digest).decode()
        password = secrets.token_urlsafe(24)
        lines = ['HERMES_DASHBOARD_BASIC_AUTH_USERNAME=admin',
                 'HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH=' + hash_password(password),
                 'HERMES_DASHBOARD_BASIC_AUTH_SECRET=' + secrets.token_urlsafe(36)]
        write_new(env, '\n'.join(lines) + '\n')
        write_new(Path('/root/LOCAL-LOGIN.txt'), 'Hermes: http://127.0.0.1:9119/\nUsername: admin\nPassword: ' + password + '\n')
    stamp = home / '.ksu-initialized'
    if not stamp.exists():
        for key, value in [('terminal.backend','local'), ('terminal.cwd','/workspace'),
                           ('terminal.home_mode','real'),
                           ('dashboard.public_url','http://hermes.localhost:9119')]:
            subprocess.run(['/usr/local/bin/hermes','config','set',key,value], check=True)
        write_new(stamp, '1\n')
print(app + ' initialization complete (credentials not displayed)')
