#!/bin/bash
set -euo pipefail
export HOME=/root PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export NPM_CONFIG_PREFIX=/usr/local
export SHARP_IGNORE_GLOBAL_LIBVIPS=1
npm install -g openclaw@2026.10.7 --omit=dev --no-fund --no-audit
openclaw --version
printf 'openclaw=2026.10.7\n' > /opt/ksu-agent/app-version
