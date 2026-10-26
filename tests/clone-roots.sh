#!/system/bin/sh
set -eu
B=/data/adb/ai-containers-build
A=/data/adb/ai-containers
BB=/data/adb/ksu/bin/busybox
[ ! -L "$A" ] || exit 90
mkdir -p "$A"
chmod 700 "$A"
for app in openclaw hermes; do
  [ ! -L "$A/$app" ] || exit 91
  mkdir -p "$A/$app/versions" "$A/$app/home" "$A/$app/workspace" "$A/$app/run"
  chmod 700 "$A/$app" "$A/$app/home" "$A/$app/run"
  R="$A/$app/versions/0.1.0"
  if [ ! -e "$R" ]; then
    mkdir "$R"
    $BB cp -a "$B/base-rootfs/." "$R/"
    $BB ln -s versions/0.1.0 "$A/$app/current"
  fi
  printf '%s\n' "$app cloned"
done
curl -fsS http://127.0.0.1:18791/cache/ksu-agent -o "$B/ksu-agent"
chmod 700 "$B/ksu-agent"
"$B/ksu-agent" openclaw exec /bin/bash -c 'id; node --version; python3.14 --version; head -n 5 /proc/self/status; ls /host; test -w /host/data/local/tmp && echo HOST_RW_OK; mount -t tmpfs tmpfs /mnt || true'
