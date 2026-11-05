#!/bin/sh
# Build the public "KSSH for Friends" tree from this repository, without personal data.
# Usage (from a clone of ykinfohome7/ssh-connector):
#   sh scripts/build-friends-repo.sh OUT_DIR
# Needs the branches origin/claude/kssh-snippet-library, origin/claude/install-script
# and origin/claude/friends-export (this file and friends/). Nothing is pushed.
set -eu
OUT="${1:?usage: build-friends-repo.sh OUT_DIR}"
SRC_CODE="${SRC_CODE:-origin/claude/kssh-snippet-library}"
SRC_INSTALL="${SRC_INSTALL:-origin/claude/install-script}"
SRC_FRIENDS="${SRC_FRIENDS:-origin/claude/friends-export}"
[ ! -e "$OUT" ] || { echo "OUT_DIR must not exist: $OUT" >&2; exit 1; }
mkdir -p "$OUT"

git archive "$SRC_CODE" .claude-plugin .agents .github/ISSUE_TEMPLATE .github/PULL_REQUEST_TEMPLATE.md \
  .gitignore LICENSE VERSION requirements.txt server.py servers.example.yaml SECURITY.md CONTRIBUTING.md \
  plugins docs/COMMANDS.md docs/COMMANDS.bg.md docs/SNIPPETS.md docs/SNIPPETS.bg.md docs/SNMP.md docs/RDP.md \
  docs/PLUGIN-AND-ENDPOINT.md docs/SECURITY-STANDARDS.md docs/SECURITY-STANDARDS.bg.md \
  scripts/gen_snippet_docs.py scripts/gen_commands_docs.py tests | tar -x -C "$OUT"
for f in install.sh docs/INSTALL.md docs/INSTALL.bg.md tests/test_install_script.py; do
  git show "$SRC_INSTALL:$f" > "$OUT/$f"
done
cd "$OUT"
rm -f tests/test_ci_summary.py tests/test_cloudns_ddns.py tests/test_connect.py tests/test_monitoring_*.py \
  tests/test_plugin_snmp.py tests/workflow-test.yml.txt tests/servers.test.yaml

# Replace personal names, hosts and repository references.
grep -rIl . --exclude=LICENSE | xargs sed -i -E 's/BGDB/SRV1/g; s/bgdb/srv1/g; s/bgadmin/admin/g; s/100\.65\.111\.82/100.64.0.82/g; s/192\.168\.30\.10/192.0.2.30/g; s/BGSSH/SSH Connector/g; s/bgssh\.example/kssh.example/g; s#ykinfohome7/ssh-connector#ykinfohome7/KSSH-FOR-Friends#g; s/ykinfohome7-tools/kssh-for-friends/g'
sed -i -E 's/ or write to \*\*info@srv1\.eu\*\*//; s/ или пиши на \*\*info@srv1\.eu\*\*//' SECURITY.md
sed -i 's#git clone -b claude/monitor-hardening-snmp #git clone #' docs/PLUGIN-AND-ENDPOINT.md
sed -i 's/"displayName": "ykinfohome7 tools"/"displayName": "KSSH for Friends"/' .agents/plugins/marketplace.json

# Friends-only files (generic server installer, README, extra test).
cd - >/dev/null
for f in README.md README.bg.md install-server.sh tests/test_install_server_script.py; do
  git show "$SRC_FRIENDS:friends/$f" > "$OUT/$f"
done
chmod +x "$OUT/install.sh" "$OUT/install-server.sh"

# Refuse to finish if personal data or secrets are still present.
if grep -rIn -i -E "bgssh|abrdns|bgadmin|bgdb|100\.65\.111|100\.98\.41|192\.168\.|tail675f12|hvdhhh|info@" "$OUT" --exclude=LICENSE --exclude=test_install_server_script.py; then
  echo "personal data found - not done" >&2; exit 2
fi
if grep -rIn -E "BEGIN [A-Z ]*PRIVATE KEY|ghp_[A-Za-z0-9]{20,}|github_pat_|tskey-[a-z]+-[A-Za-z0-9]{10,}" "$OUT" --exclude-dir=tests; then  # tests hold mock keys
  echo "secret-like text found - not done" >&2; exit 3
fi
echo "OK: $(find "$OUT" -type f | wc -l) files in $OUT"
