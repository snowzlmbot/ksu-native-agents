#!/system/bin/sh
set -eu
B=/data/adb/ai-containers-build
R=$B/base-rootfs
BB=/data/adb/ksu/bin/busybox
$BB mount --make-rprivate /
[ -d "$R/usr/bin" ] && [ ! -L "$R" ] || exit 90
mkdir -p "$R/proc" "$R/dev/pts" "$R/sys" "$R/tmp"
$BB mount -t proc proc "$R/proc"
$BB mount -o bind /dev "$R/dev"
$BB mount -o bind /dev/pts "$R/dev/pts"
$BB mount -t tmpfs -o mode=1777,size=1024m tmpfs "$R/tmp"
$BB mount -t tmpfs -o size=16m tmpfs "$R/run"
printf 'nameserver 223.5.5.5\nnameserver 1.1.1.1\n' > "$R/etc/resolv.conf"
printf 'Types: deb\nURIs: http://ports.ubuntu.com/ubuntu-ports\nSuites: resolute resolute-updates resolute-security\nComponents: main universe\nSigned-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg\n' > "$R/etc/apt/sources.list.d/ubuntu.sources"
printf '#!/bin/sh\nexit 101\n' > "$R/usr/sbin/policy-rc.d"
chmod 755 "$R/usr/sbin/policy-rc.d"
cd /
exec chroot "$R" /usr/bin/env -i HOME=/root PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8 /bin/bash /opt/build-base.sh
