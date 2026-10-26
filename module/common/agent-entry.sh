#!/bin/bash
set -euo pipefail
export HOME=/root PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
umask 077
app=${KSU_AGENT:?}
state=/root/.openclaw
if [ "$app" = hermes ]; then state=/root/.hermes; fi
python=/usr/bin/python3
if [ "$app" = hermes ] && [ -x /opt/ksu-hermes-runtime/tools/python-3.14.9+20261021-linux-arm64/bin/python3 ]; then python=/opt/ksu-hermes-runtime/tools/python-3.14.9+20261021-linux-arm64/bin/python3; fi
if [ "$app" = hermes ]; then
  exec /usr/local/bin/hermes "$@"
fi
exec /usr/local/bin/openclaw "$@"
