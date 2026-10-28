#!/usr/bin/env bash
# ssh-connector: one-shot installer for an always-on server (Debian/Ubuntu or RHEL/Fedora/Rocky/Alma).
# Runs the connector as a loopback-only systemd service; public HTTPS ingress is configured separately.
# Preferred ingress: bgssh.abrdns.com:443 on a trusted persistent Debian reverse proxy.
# Never expose the local HTTP port or install a temporary Cloudflare tunnel.
#
#   curl -fsSL https://raw.githubusercontent.com/ykinfohome7/ssh-connector/main/install-server.sh | sudo bash
#
# Re-running is safe: it updates the code and keeps your token, key and server list.
# Options (env): PORT=8765 SRC=/path/to/checkout (install from a local copy).
set -euo pipefail

[ "$(id -u)" = 0 ] || { echo "Please run as root: curl ... | sudo bash"; exit 1; }

REPO="https://github.com/ykinfohome7/ssh-connector"
APP=/opt/ssh-connector
ETC=/etc/ssh-connector
DATA=/var/lib/ssh-connector
PORT="${PORT:-8765}"

say() { printf '\n\033[1;32m==> %s\033[0m\n' "$*"; }

say "Installing packages"
if command -v apt-get >/dev/null 2>&1; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y -qq python3 python3-venv git curl openssh-client >/dev/null
elif command -v dnf >/dev/null 2>&1; then
  dnf install -y -q python3 git curl openssh-clients >/dev/null
elif command -v yum >/dev/null 2>&1; then
  yum install -y -q python3 git curl openssh-clients >/dev/null
else
  echo "Unsupported system: need apt-get, dnf or yum"; exit 1
fi

say "Getting the code into $APP"
if [ -n "${SRC:-}" ]; then
  rm -rf "$APP"; cp -r "$SRC" "$APP"
elif [ -d "$APP/.git" ]; then
  git -C "$APP" pull -q --ff-only
else
  git clone -q "$REPO" "$APP"
fi

say "Service user, key and settings"
id sshconn >/dev/null 2>&1 || useradd --system --create-home --home-dir "$DATA" --shell /usr/sbin/nologin sshconn
mkdir -p "$ETC" "$DATA/.ssh"
chown -R sshconn: "$DATA"
chmod 700 "$DATA/.ssh"
if [ ! -f "$DATA/.ssh/id_ed25519" ]; then
  runuser -u sshconn -- ssh-keygen -q -t ed25519 -N "" -f "$DATA/.ssh/id_ed25519" -C "ssh-connector@$(hostname)"
fi
if [ ! -f "$ETC/env" ]; then
  echo "SSH_CONNECTOR_TOKEN=$(python3 -c 'import secrets;print(secrets.token_urlsafe(32))')" > "$ETC/env"
  chmod 600 "$ETC/env"
fi
if [ ! -f "$ETC/servers.yaml" ]; then
  cat > "$ETC/servers.yaml" <<EOF
# Your servers. After editing:  systemctl restart ssh-connector
defaults:
  user: root
  key: $DATA/.ssh/id_ed25519
  known_hosts: null        # host keys are not checked; set a known_hosts file to enable checking
  connect_timeout: 8
  retries: 3
servers:
  this-server:
    os: $( (command -v apt-get >/dev/null && echo debian) || echo redhat )
    hosts: [127.0.0.1]
    tags: [all]
  # web1:
  #   os: debian
  #   hosts: [203.0.113.10, 198.51.100.10]   # primary, then fallback
  #   tags: [all, web]
snippets:
  disk: df -h
  mem: free -m
  failed: systemctl --failed --no-legend
  top: ps aux --sort=-%cpu | head -15
EOF
fi
chown root:sshconn "$ETC/servers.yaml"; chmod 640 "$ETC/servers.yaml"

say "Installing Python dependencies (first time takes ~1 min)"
runuser -u sshconn -- env HOME="$DATA" CLAUDE_PLUGIN_DATA="$DATA" SSH_CONNECTOR_CONFIG="$ETC/servers.yaml" \
  sh "$APP/plugins/ssh-connector/bin/run.sh" --help >/dev/null

say "Creating services"
cat > /etc/systemd/system/ssh-connector.service <<EOF
[Unit]
Description=ssh-connector MCP server (HTTP)
After=network-online.target
Wants=network-online.target

[Service]
User=sshconn
EnvironmentFile=$ETC/env
Environment=HOME=$DATA
Environment=CLAUDE_PLUGIN_DATA=$DATA
Environment=SSH_CONNECTOR_CONFIG=$ETC/servers.yaml
ExecStart=/bin/sh $APP/plugins/ssh-connector/bin/run.sh --http --host 127.0.0.1 --port $PORT
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# Disable any quick tunnel service installed by an earlier connector release.
# This does NOT affect unrelated Cloudflare services.
systemctl disable --now ssh-connector-tunnel.service >/dev/null 2>&1 || true

cat > /usr/local/bin/ssh-connector-info <<'EOF'
#!/bin/sh
# Shows the connection details for Claude and ChatGPT (run as root).
. /etc/ssh-connector/env
URL="https://bgssh.abrdns.com"
echo
echo "===================== ssh-connector ====================="
echo "CLAUDE  (Customize > Connectors > + Add > Add custom connector)"
echo "  URL:            $URL/mcp"
echo "  Authentication: No sign in"
echo "  Request header: Authorization = Bearer $SSH_CONNECTOR_TOKEN"
echo
echo "CHATGPT (Settings > Apps & Connectors > Advanced > Developer mode > Create)"
echo "  URL:            $URL/<SSH_CONNECTOR_TOKEN>/mcp"
echo "  Authentication: No authentication"
echo
echo "Add this public key to ~/.ssh/authorized_keys on every server you want to reach:"
cat /var/lib/ssh-connector/.ssh/id_ed25519.pub
echo
echo "Server list: /etc/ssh-connector/servers.yaml   then: systemctl restart ssh-connector"
echo "Use HTTPS only after the public reverse proxy + certificate are verified."
echo "The token is in /etc/ssh-connector/env (root-only). Never publish it."
echo "Keep the token secret. Anyone with it can run commands on your servers."
echo "========================================================="
EOF
chmod 755 /usr/local/bin/ssh-connector-info

# Allow the connector to manage this server itself (key login as root from localhost).
mkdir -p /root/.ssh && chmod 700 /root/.ssh
grep -qF "$(cat "$DATA/.ssh/id_ed25519.pub")" /root/.ssh/authorized_keys 2>/dev/null \
  || cat "$DATA/.ssh/id_ed25519.pub" >> /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys

systemctl daemon-reload
systemctl enable --now ssh-connector >/dev/null 2>&1
systemctl restart ssh-connector

say "Checking"
for i in $(seq 1 30); do
  code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "http://127.0.0.1:$PORT/mcp" || true)
  [ "$code" = 401 ] && break
  sleep 2
done
echo "Local server answers without token: HTTP $code (401 = running and protected)"
echo "Public HTTPS must be configured separately at https://bgssh.abrdns.com."
echo "ClouDNS DNS / web redirect certificates alone do not proxy MCP traffic."
