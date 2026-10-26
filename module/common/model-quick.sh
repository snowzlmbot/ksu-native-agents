#!/bin/bash
set -euo pipefail
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
app=${KSU_AGENT:?}; action=${1:-show}
if [ "$app" = hermes ]; then
 cfg=/root/.hermes/config.yaml
 case "$action" in
  show) sed -E 's/(api_key|password|secret|token):.*/\1: <redacted>/' "$cfg" 2>/dev/null || true;;
  local) /usr/local/bin/hermes config set model.provider custom; /usr/local/bin/hermes config set model.default "${MODEL_ID:?MODEL_ID required}"; /usr/local/bin/hermes config set model.base_url "${MODEL_BASE_URL:?MODEL_BASE_URL required}"; echo 'Hermes model route saved; put API key in .env via Termux.';;
  *) echo 'model show|local'; exit 2;;
 esac
else
 case "$action" in
  show) /usr/local/bin/openclaw models status --json | sed -E 's/(apiKey|token|password|secret)("?[[:space:]]*:[[:space:]]*)"[^"]*"/\1\2"<redacted>"/g';;
  local) /usr/local/bin/openclaw config set models.providers.custom.baseUrl "${MODEL_BASE_URL:?MODEL_BASE_URL required}"; /usr/local/bin/openclaw config set models.providers.custom.api "openai-completions"; /usr/local/bin/openclaw config set models.providers.custom.models "[{\"id\":\"${MODEL_ID:?MODEL_ID required}\",\"name\":\"${MODEL_ID}\",\"input\":[\"text\"],\"contextWindow\":32768,\"maxTokens\":4096}]" --strict-json --merge; /usr/local/bin/openclaw models set "custom/${MODEL_ID}"; echo 'OpenClaw model route saved; put API key in .env via Termux.';;
  *) echo 'model show|local'; exit 2;;
 esac
fi
