#!/bin/bash
set -euo pipefail
exec /usr/bin/python3 /opt/ksu-agent/model-config.py "$@"
