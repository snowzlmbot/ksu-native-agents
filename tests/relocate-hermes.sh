#!/bin/bash
set -euo pipefail
H=/root/.hermes
R=/opt/ksu-hermes-runtime
S=/opt/ksu-agent/home-seed
mkdir -p "$R" "$S/.hermes" /usr/local/bin
for d in tools installs; do
 if [ -d "$H/$d" ] && [ ! -L "$H/$d" ]; then mv "$H/$d" "$R/$d"; ln -s "$R/$d" "$H/$d"; fi
done
cp -a "$H/skills" "$S/.hermes/skills"
cp -a "$H/SOUL.md" "$S/.hermes/SOUL.md"
printf '#!/bin/sh\nexec /opt/hermes-agent/.hermes/bin/hermes "$@"\n' > /usr/local/bin/hermes
chmod 755 /usr/local/bin/hermes
