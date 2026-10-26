#!/usr/bin/python3
"""Enable bundled Simplified Chinese without rewriting arbitrary JS functions."""
import os, re
from pathlib import Path
root=Path('/opt/hermes-agent/hermes_cli/web_dist')
page=root/'index.html'
if not page.is_file() or page.is_symlink():
    raise SystemExit('Hermes dashboard entry missing or unsafe')
text=page.read_text(encoding='utf-8')
script='<script id="ksu-zh-locale">try{localStorage.setItem("hermes-locale","zh");document.documentElement.lang="zh-CN"}catch(e){}</script>'
if 'id="ksu-zh-locale"' not in text:
    text=text.replace('<head>','<head>\n    '+script,1)
text=text.replace('<html lang="en">','<html lang="zh-CN">').replace('Hermes Agent - Dashboard','Hermes 智能助手 - 控制台')
if text!=page.read_text(encoding='utf-8'):
    tmp=page.with_name('.index.ksu-zh.tmp')
    fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_TRUNC|os.O_NOFOLLOW,0o644)
    with os.fdopen(fd,'w') as f: f.write(text)
    os.replace(tmp,page)
print('Hermes bundled zh locale enabled; model replies, code, and external docs unchanged')
