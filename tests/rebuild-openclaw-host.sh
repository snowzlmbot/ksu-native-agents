#!/system/bin/sh
set -eu
BB=/data/adb/ksu/bin/busybox
R=/data/adb/ai-containers/openclaw/versions/0.1.0
$BB mount --make-rprivate /
$BB mount -t proc proc "$R/proc"
$BB mount -o bind /dev "$R/dev"
$BB mount -o bind /dev/pts "$R/dev/pts"
$BB mount -t tmpfs -o size=512m,mode=1777 tmpfs "$R/tmp"
curl -fsS http://127.0.0.1:18791/tests/rebuild-openclaw.sh -o "$R/opt/rebuild.sh"
cd /
exec chroot "$R" /usr/bin/env -i HOME=/root PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin /bin/bash /opt/rebuild.sh
