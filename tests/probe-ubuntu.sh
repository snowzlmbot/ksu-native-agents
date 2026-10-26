#!/system/bin/sh
set -eu
BASE=/data/adb/ai-containers-build
BB=/data/adb/ksu/bin/busybox
[ ! -L "$BASE" ] || exit 90
mkdir -p "$BASE/cache" "$BASE/base-rootfs"
chmod 700 "$BASE"
[ ! -e "$BASE/base-rootfs/.unpacked" ] || exit 0
[ -z "$(ls -A "$BASE/base-rootfs")" ] || exit 91
curl -fsS --max-time 120 http://127.0.0.1:18791/cache/ubuntu-base-26.04.1-base-arm64.tar.gz -o "$BASE/cache/base.tgz"
printf '%s  %s\n' 5a1906794ced63a71a8119c3f211ef5f0bbe0a243001b4bbd41fdf80c5b219fd "$BASE/cache/base.tgz" | "$BB" sha256sum -c -
"$BB" tar xzpf "$BASE/cache/base.tgz" -C "$BASE/base-rootfs"
touch "$BASE/base-rootfs/.unpacked"
"$BB" unshare -m /system/bin/sh -c '/data/adb/ksu/bin/busybox mount --make-rprivate /; cd /; /system/bin/chroot /data/adb/ai-containers-build/base-rootfs /bin/bash -c "id; cat /etc/os-release; /usr/bin/python3 --version || true"'
