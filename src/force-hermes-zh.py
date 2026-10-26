#!/usr/bin/python3
import re
from pathlib import Path
root=Path('/opt/hermes-agent/hermes_cli/web_dist/assets')
for path in root.glob('i18n-*.js'):
    text=path.read_text(encoding='utf-8')
    original=text
    # Force Simplified Chinese locale on every load, even if old localStorage says en.
    text=re.sub(r'function P\(\)\{.*?return`en`\}', 'function P(){return`zh`}', text, count=1, flags=re.S)
    text=text.replace('return`en`', 'return`zh`')
    if text != original:
        path.write_text(text, encoding='utf-8')
        print('patched', path)
