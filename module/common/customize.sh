#!/system/bin/sh
# Sourced by the modern KernelSU installer; all mutable data stays outside MODPATH.
[ "${KSU:-}" = true ] || abort 'KernelSU required'
[ "$(uname -m)" = aarch64 ] || abort 'ARM64 device required'
APP=@APP@
VERSION=0.1.0-rc1
BASE=/data/adb/ai-containers
STATE=$BASE/$APP
BB=/data/adb/ksu/bin/busybox
[ -x "$BB" ] || abort 'KernelSU BusyBox required'
umask 077
check_dir() {
  p=$1
  [ ! -L "$p" ] && [ -d "$p" ] || abort "Unsafe directory: $p"
}
# No recursive cleanup, chmod, chown, unmount, or symlink-following writes.
for p in /data /data/adb; do check_dir "$p"; done
[ -e "$BASE" ] || mkdir "$BASE" || abort 'Cannot create data base'
check_dir "$BASE"
[ -e "$STATE" ] || mkdir "$STATE" || abort 'Cannot create agent state'
check_dir "$STATE"
for name in versions home workspace run; do
  [ -e "$STATE/$name" ] || mkdir "$STATE/$name" || abort 'Cannot create data directory'
  check_dir "$STATE/$name"
done
ui_print '- Verifying offline package'
(cd "$MODPATH" && "$BB" sha256sum -c SHA256SUMS) || abort 'Package hash verification failed'
chmod 700 "$MODPATH/bin/ksu-agent"
# Prefer the current complete managed rootfs when it exists; upgrade never clones it.
REUSE=
if [ -L "$STATE/current" ]; then
 target=$("$BB" readlink "$STATE/current")
 case "$target" in versions/*) suffix=${target#versions/};; *) abort 'Unsafe current pointer';; esac
 case "$suffix" in ''|*/*|.|..) abort 'Unsafe current version';; esac
 candidate=$STATE/$target
 check_dir "$candidate"
 [ -f "$candidate/opt/ksu-agent/payload-complete" ] || abort 'Current payload is incomplete'
 REUSE=$candidate
fi
ROOT=$STATE/versions/$VERSION
ACTIVE_VERSION=$VERSION
if [ -n "$REUSE" ]; then
 ROOT=$REUSE
 ACTIVE_VERSION=${ROOT##*/}
 ui_print '- Reusing current complete Ubuntu payload; user data untouched'
elif [ -e "$ROOT" ] || [ -L "$ROOT" ]; then
  check_dir "$ROOT"
  [ -f "$ROOT/opt/ksu-agent/payload-complete" ] && [ ! -L "$ROOT/opt/ksu-agent/payload-complete" ] || abort 'Existing version incomplete; preserved, not overwritten'
elif [ -d "$STATE/versions/0.1.0" ] && [ ! -L "$STATE/versions/0.1.0" ] && [ -f "$STATE/versions/0.1.0/opt/ksu-agent/payload-complete" ]; then
  # Device already has the verified Ubuntu payload; never copy it again during install.
  ROOT=$STATE/versions/0.1.0
  ACTIVE_VERSION=0.1.0
  ui_print '- Reusing verified existing Ubuntu payload'
else
  [ -f "$MODPATH/payload/rootfs.tar.xz" ] || abort 'Ubuntu payload missing and no verified existing rootfs'
  STAGE=$STATE/versions/.$VERSION.pending.$$
  [ ! -e "$STAGE" ] && [ ! -L "$STAGE" ] || abort 'Staging path exists'
  mkdir -m 700 "$STAGE" || abort 'Cannot create empty staging'
  ui_print '- Extracting Ubuntu into new private version directory'
  "$BB" tar xJpf "$MODPATH/payload/rootfs.tar.xz" -C "$STAGE" || abort 'Extraction failed; incomplete staging preserved'
  # The minimal Ubuntu export may omit merged-/usr top-level links.
  for pair in bin:usr/bin sbin:usr/sbin lib:usr/lib; do
    link=${pair%%:*}; value=${pair#*:}
    if [ ! -e "$STAGE/$link" ] && [ ! -L "$STAGE/$link" ]; then
      [ -d "$STAGE/$value" ] && [ ! -L "$STAGE/$value" ] || abort 'Missing merged usr directory'
      ln -s "$value" "$STAGE/$link" || abort 'Cannot create Ubuntu standard link'
    fi
  done
  [ -f "$STAGE/opt/ksu-agent/payload-complete" ] || abort 'Payload marker missing'
  [ ! -L "$STAGE/usr" ] && [ -x "$STAGE/usr/bin/bash" ] && [ -e "$STAGE/lib/ld-linux-aarch64.so.1" ] || abort 'Invalid Ubuntu payload/loader'
  mv "$STAGE" "$ROOT" || abort 'Cannot publish version'
fi
# Stop a verified previous supervisor before switching. Never kill arbitrary PIDs.
"$MODPATH/bin/ksu-agent" "$APP" stop || abort 'Stop failed; data preserved'
i=0
while [ "$i" -lt 30 ]; do
  status=$("$MODPATH/bin/ksu-agent" "$APP" status) || abort 'Status failed'
  case "$status" in *' running '*) "$BB" sleep 1;; *) break;; esac
  i=$((i+1))
done
case "$status" in *' running '*) abort 'Previous service did not stop; reboot and retry';; esac
if [ -e "$STATE/current" ] || [ -L "$STATE/current" ]; then
  [ -L "$STATE/current" ] || abort 'Current pointer is not a managed symlink'
  target=$("$BB" readlink "$STATE/current")
  case "$target" in versions/*) suffix=${target#versions/};; *) abort 'Current points outside versions';; esac
  case "$suffix" in ''|*/*|.|..) abort 'Unsafe current version';; esac
fi
NEXT=$STATE/.current.$$
[ ! -e "$NEXT" ] && [ ! -L "$NEXT" ] || abort 'Pointer staging exists'
ln -s "versions/$ACTIVE_VERSION" "$NEXT" || abort 'Cannot create version pointer'
"$BB" mv -Tf "$NEXT" "$STATE/current" || abort 'Cannot switch version'
# Explicit executable bits; do not depend on archive permission preservation.
for script in service.sh boot-completed.sh deploy-runtime.sh uninstall.sh action.sh agentctl termux native; do chmod 700 "$MODPATH/$script"; done
/system/bin/sh "$MODPATH/deploy-runtime.sh" || abort 'Runtime deployment failed; data preserved'
/system/bin/sh "$MODPATH/boot-completed.sh" || abort 'Runtime directory validation failed'
# Modules are never mounted into /system.
touch "$MODPATH/skip_mount"
ui_print "- $APP installed. Default: boot auto-start, UID0, host read/write."
ui_print "- Persistent data: $STATE (also retained on uninstall)"
ui_print '- Model credentials are configured locally after startup.'
