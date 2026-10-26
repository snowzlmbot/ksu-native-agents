#!/bin/bash
set -euo pipefail
umask 077
cd /workspace
/usr/bin/python3 /opt/ksu-agent/bootstrap.py
if [ "$KSU_AGENT" = openclaw ]; then
    exec /usr/local/bin/openclaw gateway run --bind loopback --port 18789 --auth token
fi
# Dashboard and messaging gateway share persistent config, not a systemd unit.
/usr/local/bin/hermes gateway run --external-supervisor > /root/.hermes/logs/ksu-gateway.log 2>&1 &
gateway_pid=$!
/usr/local/bin/hermes dashboard --host 127.0.0.1 --port 9119 --no-open --skip-build &
dashboard_pid=$!
cleanup() {
    kill -TERM "$gateway_pid" "$dashboard_pid" 2>/dev/null || true
    wait "$gateway_pid" "$dashboard_pid" 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 0' TERM INT
wait -n "$gateway_pid" "$dashboard_pid"
