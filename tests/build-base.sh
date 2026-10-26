#!/bin/bash
set -euo pipefail
apt-get update
apt-get install -y --no-install-recommends ca-certificates curl wget git openssh-client python3.14 python3.14-venv python3-pip build-essential cmake pkg-config libssl-dev libffi-dev ripgrep jq sqlite3 procps iproute2 util-linux tini tzdata xz-utils zstd bzip2 unzip tmux libatomic1 libstdc++6 libgomp1 libcap2-bin
cd /opt
curl -fL --retry 3 https://nodejs.org/dist/v24.22.1/node-v24.22.1-linux-arm64.tar.xz -o /opt/node.tar.xz
curl -fL --retry 3 https://nodejs.org/dist/v24.22.1/SHASUMS256.txt -o /opt/node-SHASUMS256.txt
python3 -c 'import hashlib,pathlib; p=pathlib.Path("/opt/node.tar.xz"); actual=hashlib.sha256(p.read_bytes()).hexdigest(); expect=next(x.split()[0] for x in pathlib.Path("/opt/node-SHASUMS256.txt").read_text().splitlines() if x.endswith(" node-v24.22.1-linux-arm64.tar.xz")); assert actual==expect'
tar xJf /opt/node.tar.xz -C /opt
ln -s /opt/node-v24.22.1-linux-arm64/bin/node /usr/local/bin/node
ln -s /opt/node-v24.22.1-linux-arm64/bin/npm /usr/local/bin/npm
ln -s /opt/node-v24.22.1-linux-arm64/bin/npx /usr/local/bin/npx
node --version
python3.14 --version
mkdir -p /opt/ksu-agent /host /workspace
printf 'base-26.04.1-arm64\n' > /opt/ksu-agent/base-version
