#!/bin/bash
set -euo pipefail
export HOME=/root PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export NPM_CONFIG_PREFIX=/usr/local SHARP_IGNORE_GLOBAL_LIBVIPS=1
npm rebuild -g --allow-scripts=@google/genai,esbuild,koffi,protobufjs,openclaw openclaw
openclaw --version
