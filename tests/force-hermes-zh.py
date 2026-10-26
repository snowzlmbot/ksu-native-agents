from pathlib import Path
import re
root=Path("/opt/hermes-agent/hermes_cli/web_dist/assets")
for p in root.glob("i18n-*.js"):
 s=p.read_text(encoding="utf-8")
 old="return`en`"
 if old in s:
  p.write_text(s.replace(old,"return`zh`",1),encoding="utf-8")
  print("patched",p)
