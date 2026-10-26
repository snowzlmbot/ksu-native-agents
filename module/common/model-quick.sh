#!/bin/bash
set -euo pipefail
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
app=${KSU_AGENT:?}; action=${1:-show}
decode(){ printf '%s' "$1" | base64 -d; }
valid(){ [[ "$1" =~ ^[A-Za-z0-9._:/-]+$ ]]; }
if [ "$action" = set ]; then
 [ "$#" -eq 5 ] || { echo 'model set provider model base_url key_env'; exit 2; }
 provider=$(decode "$2"); model=$(decode "$3"); base=$(decode "$4"); key=$(decode "$5")
 valid "$provider" && valid "$model" || { echo 'invalid provider/model'; exit 2; }
 [[ "$base" =~ ^https?://[^[:space:]\"\'\`]+$ ]] || { echo 'invalid base URL'; exit 2; }
 [[ "$key" =~ ^[A-Z][A-Z0-9_]{0,127}$ ]] || { echo 'invalid key environment name'; exit 2; }
 if [ "$app" = hermes ]; then
  /usr/local/bin/hermes config set model.provider "$provider"
  /usr/local/bin/hermes config set model.default "$model"
  /usr/local/bin/hermes config set model.base_url "$base"
  /usr/local/bin/hermes config set model.api_mode chat_completions
  /usr/local/bin/hermes config set model.key_env "$key"
 else
  /usr/local/bin/openclaw config set "models.providers.$provider.baseUrl" "$base"
  /usr/local/bin/openclaw config set "models.providers.$provider.api" openai-completions
  /usr/local/bin/openclaw config set "models.providers.$provider.apiKey" "{\"source\":\"env\",\"provider\":\"default\",\"id\":\"$key\"}" --strict-json --merge
  /usr/local/bin/openclaw config set "models.providers.$provider.models" "[{\"id\":\"$model\",\"name\":\"$model\",\"input\":[\"text\"],\"contextWindow\":32768,\"maxTokens\":4096}]" --strict-json --merge
  /usr/local/bin/openclaw models set "$provider/$model"
 fi
 echo '模型路由已保存；请在 .env 配置对应 API Key，重启后新会话生效。'
 exit 0
fi
if [ "$app" = hermes ]; then
 case "$action" in show) sed -E 's/(api_key|password|secret|token):.*/\1: <redacted>/' /root/.hermes/config.yaml 2>/dev/null || true;; *) echo 'model show|set BASE64_PROVIDER BASE64_MODEL BASE64_URL BASE64_KEY_ENV'; exit 2;; esac
else
 case "$action" in show) /usr/local/bin/openclaw models status --json | sed -E 's/(apiKey|token|password|secret)("?[[:space:]]*:[[:space:]]*)"[^"]*"/\1\2"<redacted>"/g';; *) echo 'model show|set BASE64_PROVIDER BASE64_MODEL BASE64_URL BASE64_KEY_ENV'; exit 2;; esac
fi
