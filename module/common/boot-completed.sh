#!/system/bin/sh
set -eu
APP=@APP@
STATE=/data/adb/ai-containers/$APP
R=$STATE/versions/0.1.0
[ -d "$R" ] && [ ! -L "$R" ] || exit 1
chmod 755 "$R"
chmod 1777 "$R/tmp"
if [ "$APP" = hermes ]; then
  G=$R/opt/ksu-hermes-runtime/installs/ffad2f5543956651/pm-runtime
  S=$G/selected.json
  if [ -f "$S" ]; then
    GEN=$(/data/adb/ksu/bin/busybox sed -n 's/.*"generation"[[:space:]]*:[[:space:]]*"generations\/\([^"]*\)".*/\1/p' "$S")
    if [ -n "$GEN" ] && [ -d "$G/$GEN" ]; then
      /data/adb/ksu/bin/busybox python3 - <<PY
import json
p="$R/opt/hermes-agent/install-stamp.json"
d=json.load(open(p)); d['pmRuntime']='/root/.hermes/installs/ffad2f5543956651/pm-runtime'; open(p,'w').write(json.dumps(d,indent=2)+'\n')
q="$G/pm-runtime.json"
d={'python':'$GEN/bin/python','sitePackages':'$GEN/lib/python3.14/site-packages'}; open(q,'w').write(json.dumps(d)+'\n')
PY
    fi
  fi
fi
