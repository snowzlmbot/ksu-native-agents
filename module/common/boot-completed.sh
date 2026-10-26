#!/system/bin/sh
set -eu
APP=@APP@
STATE=/data/adb/ai-containers/$APP
MODDIR=${0%/*}
R=$STATE/versions/0.1.0
[ -d "$R" ] && [ ! -L "$R" ] || exit 1
chmod 755 "$R"; chmod 1777 "$R/tmp"
# Bounded, module-owned cleanup only. Never touch config, sessions, secrets, rootfs or host mounts.
find "$R/tmp" -mindepth 1 -maxdepth 1 -xdev -mtime +2 -exec rm -rf -- {} + 2>/dev/null || true
find "$R/root/.npm/_cacache" -type f -mtime +14 -delete 2>/dev/null || true
rm -f "$R/var/cache/apt/pkgcache.bin" "$R/var/cache/apt/srcpkgcache.bin" "$R/opt/hermes-source.tgz" 2>/dev/null || true
find "$R/var/cache/apt/archives" -type f -mtime +2 -delete 2>/dev/null || true
find "$STATE/run" -maxdepth 1 -type f -name '*.old' -mtime +3 -delete 2>/dev/null || true
if [ "$APP" = hermes ]; then
  G=$R/opt/ksu-hermes-runtime/installs/ffad2f5543956651/pm-runtime
  if [ -f "$G/selected.json" ]; then
    GEN=$(/data/adb/ksu/bin/busybox sed -n 's/.*generation.*generations\/\([a-f0-9]*\).*/\1/p' "$G/selected.json" || true)
    if [ -n "$GEN" ] && [ -d "$G/generations/$GEN" ]; then
      # Host-side JSON maintenance; do not execute the glibc Python binary outside chroot.
      if ! /data/adb/ksu/bin/busybox grep -q '"pmRuntime"' "$R/opt/hermes-agent/install-stamp.json" 2>/dev/null; then
        /data/adb/ksu/bin/busybox sed -i 's/"payload": "bootstrap"/"payload": "bootstrap", "pmRuntime": "\/root\/.hermes\/installs\/ffad2f5543956651\/pm-runtime"/' "$R/opt/hermes-agent/install-stamp.json" || true
      fi
      printf '{"python":"generations/%s/bin/python","sitePackages":"generations/%s/lib/python3.14/site-packages"}\n' "$GEN" "$GEN" > "$G/pm-runtime.json"
    fi
  fi
  # The Python web bundle patch runs inside Ubuntu through the native launcher.
  [ -x "$MODDIR/bin/ksu-agent" ] && [ -f "$R/opt/ksu-agent/force-hermes-zh.py" ] && \
    "$MODDIR/bin/ksu-agent" hermes exec /opt/ksu-hermes-runtime/tools/python-3.14.9+20261021-linux-arm64/bin/python3 /opt/ksu-agent/force-hermes-zh.py >/dev/null 2>&1 || true
fi
