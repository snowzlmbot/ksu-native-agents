#!/bin/bash
set -euo pipefail
export HOME=/root PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export HERMES_HOME=/root/.hermes
cd /opt
curl -fsS --retry 3 http://127.0.0.1:18791/cache/hermes-source.tgz -o /opt/hermes-source.tgz
printf '%s  %s\n' 0dc2cca54657d162845a77f634e107c61c3fb0bd6c8505212aa2e200591b7cc9 /opt/hermes-source.tgz | sha256sum -c -
mkdir -p /opt/hermes-agent
tar xzf /opt/hermes-source.tgz -C /opt/hermes-agent --strip-components=1
cd /opt/hermes-agent
python3.14 -m pm.cli install --without agent-browser --without cua-driver
python3.14 -I -B -X utf8 hermes_cli/source_completion.py --source /opt/hermes-agent
printf 'hermes=v0.22.5\ncommit=bf0203a794a07aac3ff764972ab9087baa4e4f4e\n' > /opt/ksu-agent/app-version
