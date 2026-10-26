#!/system/bin/sh
set -eu
APP=@APP@
STATE=/data/adb/ai-containers/$APP
R=$STATE/versions/0.1.0
[ -d "$R" ] && [ ! -L "$R" ] || exit 1
chmod 755 "$R"; chmod 1777 "$R/tmp"
# Only bounded, module-owned cache cleanup. Never touch config, sessions, secrets, rootfs, or host mounts.
find "$R/tmp" -mindepth 1 -maxdepth 1 -xdev -mtime +2 -exec rm -rf -- {} + 2>/dev/null || true
find "$STATE/run" -maxdepth 1 -type f -name '*.old' -mtime +3 -delete 2>/dev/null || true
if [ "$APP" = hermes ]; then
 G=$R/opt/ksu-hermes-runtime/installs/ffad2f5543956651/pm-runtime
 if [ -f "$G/selected.json" ]; then
  GEN=$(/data/adb/ksu/bin/busybox sed -n 's/.*generation.*generations\/\([a-f0-9]*\).*/\1/p' "$G/selected.json" || true)
  if [ -n "$GEN" ] && [ -d "$G/generations/$GEN" ]; then
   /data/adb/ksu/bin/busybox python3 - "$R" "$G" "$GEN" <<'PY'
import json,sys
r,g,gen=sys.argv[1:]
p=f'{r}/opt/hermes-agent/install-stamp.json'; d=json.load(open(p)); d['pmRuntime']='/root/.hermes/installs/ffad2f5543956651/pm-runtime'; open(p,'w').write(json.dumps(d,indent=2)+'\n')
open(f'{g}/pm-runtime.json','w').write(json.dumps({'python':f'generations/{gen}/bin/python','sitePackages':f'generations/{gen}/lib/python3.14/site-packages'})+'\n')
PY
  fi
 fi
fi
