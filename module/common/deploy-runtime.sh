#!/system/bin/sh
# Deploy only reviewed module runtime files, after the old supervisor has stopped.
set -eu
MODDIR=${0%/*}
APP=@APP@
STATE=/data/adb/ai-containers/$APP
BB=/data/adb/ksu/bin/busybox
[ -L "$STATE/current" ] || exit 1
ROOT=$("$BB" readlink -f "$STATE/current")
case "$ROOT" in "$STATE"/versions/*) ;; *) exit 1;; esac
SUFFIX=${ROOT#"$STATE"/versions/}
case "$SUFFIX" in ''|*/*|.|..) exit 1;; esac
check_chain(){
  local path=$1 prefix= part
  local IFS=/
  for part in $path; do
    [ -n "$part" ] || continue
    prefix=$prefix/$part
    [ -d "$prefix" ] && [ ! -L "$prefix" ] || return 1
  done
}
check_chain "$ROOT"
check_chain "$ROOT/opt/ksu-agent"
chmod 755 "$ROOT"
for name in bootstrap.py start.sh force-hermes-zh.py model-config.py model-quick.sh storage-clean.py; do
  src=$MODDIR/runtime/$name
  [ -f "$src" ] && [ ! -L "$src" ] || exit 1
  dst=$ROOT/opt/ksu-agent/$name
  [ ! -L "$dst" ] || exit 1
  tmp=$dst.new.$$
  [ ! -e "$tmp" ] && [ ! -L "$tmp" ] || exit 1
  (set -C; umask 077; cat "$src" > "$tmp") || exit 1
  chmod 700 "$tmp"
  "$BB" mv -f "$tmp" "$dst"
done
