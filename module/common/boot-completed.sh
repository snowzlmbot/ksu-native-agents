#!/system/bin/sh
# No automatic recursive cleanup of persistent data or host directories.
set -eu
APP=@APP@
MODDIR=${0%/*}
STATE=/data/adb/ai-containers/$APP
BB=/data/adb/ksu/bin/busybox
[ -L "$STATE/current" ] || exit 1
ROOT=$("$BB" readlink -f "$STATE/current")
case "$ROOT" in "$STATE"/versions/*) ;; *) exit 1;; esac
SUFFIX=${ROOT#"$STATE"/versions/}
case "$SUFFIX" in ''|*/*|.|..) exit 1;; esac
# Validate every component before changing rootfs-local permissions.
prefix=
OLDIFS=$IFS; IFS=/
for part in $ROOT; do
 [ -n "$part" ] || continue
 prefix=$prefix/$part
 [ -d "$prefix" ] && [ ! -L "$prefix" ] || exit 1
done
IFS=$OLDIFS
chmod 755 "$ROOT"
[ -d "$ROOT/tmp" ] && [ ! -L "$ROOT/tmp" ] || exit 1
chmod 1777 "$ROOT/tmp"
# Bootstrap repairs PM metadata inside the actual container; no host JSON edits.
# Manual cache cleanup is available via termux clean-cache and never runs at boot.
