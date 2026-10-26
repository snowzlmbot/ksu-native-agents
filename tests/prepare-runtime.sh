#!/system/bin/sh
set -eu
B=/data/adb/ai-containers-build
curl -fsS http://127.0.0.1:18791/cache/ksu-agent -o "$B/ksu-agent"
chmod 700 "$B/ksu-agent"
for app in openclaw hermes; do
 R=/data/adb/ai-containers/$app/versions/0.1.0
 curl -fsS http://127.0.0.1:18791/src/bootstrap.py -o "$R/opt/ksu-agent/bootstrap.py"
 curl -fsS http://127.0.0.1:18791/src/start.sh -o "$R/opt/ksu-agent/start.sh"
 chmod 755 "$R/opt/ksu-agent/start.sh"
done
"$B/ksu-agent" openclaw exec /usr/bin/python3 /opt/ksu-agent/bootstrap.py
"$B/ksu-agent" hermes exec /usr/bin/python3 /opt/ksu-agent/bootstrap.py
"$B/ksu-agent" hermes exec /usr/local/bin/hermes --version
