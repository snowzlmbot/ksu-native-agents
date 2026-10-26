#!/system/bin/sh
MODDIR=${0%/*}
APP=@APP@
# Keep all versions, home, workspace, secrets and mapped source directories.
# Reboot releases any residual private mounts; never umount or delete by pathname.
if [ -x "$MODDIR/bin/ksu-agent" ]; then
  "$MODDIR/bin/ksu-agent" "$APP" stop
fi
exit 0
