#!/system/bin/sh
set -eu
APP=$1
case "$APP" in openclaw|hermes) ;; *) exit 90;; esac
R=/data/adb/ai-containers/$APP/versions/0.1.0
BB=/data/adb/ksu/bin/busybox
$BB mount --make-rprivate /
$BB mount -t proc proc "$R/proc"
$BB mount -o bind /dev "$R/dev"
$BB mount -o bind /dev/pts "$R/dev/pts"
$BB mount -t tmpfs -o size=1024m,mode=1777 tmpfs "$R/tmp"
$BB mount -t tmpfs -o size=32m tmpfs "$R/run"
curl -fsS "http://127.0.0.1:18791/tests/install-$APP.sh" -o "$R/opt/install-agent.sh"
cd /
exec chroot "$R" /usr/bin/env -i HOME=/root PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin LANG=C.UTF-8 DEBIAN_FRONTEND=noninteractive /bin/bash /opt/install-agent.sh
