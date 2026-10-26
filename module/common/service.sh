#!/system/bin/sh
MODDIR=${0%/*}
APP=@APP@
STATE=/data/adb/ai-containers/$APP
BB=/data/adb/ksu/bin/busybox
i=0
while [ "$(getprop sys.boot_completed)" != 1 ] && [ "$i" -lt 180 ]; do
  "$BB" sleep 1
  i=$((i+1))
done
[ "$(getprop sys.boot_completed)" = 1 ] || exit 1
[ ! -f "$MODDIR/disable" ] && [ ! -f "$MODDIR/remove" ] || exit 0
[ ! -f "$STATE/NO_AUTOSTART" ] || exit 0
/system/bin/sh "$MODDIR/boot-completed.sh" || exit 1
[ -d "$STATE/run" ] && [ ! -L "$STATE/run" ] || exit 1
# The native supervisor owns the lock, cgroup, mount namespace and crash budget.
exec "$MODDIR/bin/ksu-agent" "$APP" supervise </dev/null >/dev/null 2>&1
