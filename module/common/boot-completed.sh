#!/system/bin/sh
# No automatic recursive deletion of persistent data.
set -eu
APP=@APP@
MODDIR=${0%/*}
STATE=/data/adb/ai-containers/$APP
BB=/data/adb/ksu/bin/busybox
[ -L "$STATE/current" ] || exit 1
R=$("$BB" readlink -f "$STATE/current")
case "$R" in "$STATE"/versions/*) ;; *) exit 1;; esac
SUFFIX=${R#"$STATE"/versions/}
case "$SUFFIX" in ''|*/*|.|..) exit 1;; esac
prefix=; OLDIFS=$IFS; IFS=/
for part in $R; do [ -n "$part" ] || continue; prefix=$prefix/$part; [ -d "$prefix" ] && [ ! -L "$prefix" ] || exit 1; done
IFS=$OLDIFS
chmod 755 "$R"
[ -d "$R/tmp" ] && [ ! -L "$R/tmp" ] || exit 1
chmod 1777 "$R/tmp"
# One-time PM metadata repair is executed through the actual Ubuntu rootfs.
if [ "$APP" = hermes ] && [ -x "$MODDIR/bin/ksu-agent" ] && [ -f "$R/opt/ksu-agent/force-hermes-zh.py" ]; then
  "$MODDIR/bin/ksu-agent" hermes exec /opt/ksu-hermes-runtime/tools/python-3.14.9+20261021-linux-arm64/bin/python3 /opt/ksu-agent/force-hermes-zh.py >/dev/null 2>&1 || true
fi
