import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parents[1]
version='0.1.0-rc10'
for app in ('openclaw','hermes'):
    path=P/'dist'/f'ksu_{app}-{version}-update.zip'
    with path.open('rb') as f: digest=hashlib.file_digest(f,'sha256').hexdigest()
    data={'version':version,'versionCode':110,
          'zipUrl':f'https://github.com/snowzlmbot/ksu-native-agents/releases/download/v{version}/{path.name}',
          'zipSha256':digest,
          'changelog':f'https://raw.githubusercontent.com/snowzlmbot/ksu-native-agents/master/docs/RELEASE-v{version}.md'}
    (P/'updates'/f'{app}.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
print('update manifests now refer to the actual verified upgrade ZIP bytes')
