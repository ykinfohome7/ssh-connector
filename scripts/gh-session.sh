#!/usr/bin/env bash
# Runs ssh-connector + a public HTTPS address (Tailscale Funnel, fallback trycloudflare) inside a GitHub Actions job, for testing and development.
# Controlled by control/session (first word: start | stop). Publishes the URL (never the token) to control/status.md.
# Secrets (repo Settings > Secrets and variables > Actions):
#   SSH_CONNECTOR_TOKEN    required - the access token (same idea as on a server)
#   SSH_CONNECTOR_SERVERS  optional - full servers.yaml content (default: public test server)
#   SSH_CONNECTOR_KEY      optional - private SSH key, saved as ~/.ssh/id_ed25519
set -euo pipefail
cd "$(dirname "$0")/.."

HOURS="${HOURS:-5}"
STATUS=control/status.md
CMD="$(awk 'NR==1{print $1}' control/session 2>/dev/null || true)"
CMD="${CMD:-start}"

publish() {  # write status file and push it without triggering other workflows
  git config user.name "connector-session"
  git config user.email "actions@github.com"
  printf '%s\n' "$1" > "$STATUS"
  git add "$STATUS"
  git commit -q -m "session status: $2 [skip ci]" || return 0
  for i in 1 2 3 4 5; do
    git pull -q --rebase origin main && git push -q origin HEAD:main && return 0
    sleep 3
  done
}

if [ "$CMD" = stop ]; then
  publish "# Connector session
state: stopped
time: $(date -u +%FT%TZ)" stopped
  echo "Session stopped."
  exit 0
fi

if [ -z "${SSH_CONNECTOR_TOKEN:-}" ] || [ "${#SSH_CONNECTOR_TOKEN}" -lt 24 ]; then
  publish "# Connector session
state: error
reason: repository secret SSH_CONNECTOR_TOKEN is missing or shorter than 24 characters
time: $(date -u +%FT%TZ)" error
  echo "::error::Add repository secret SSH_CONNECTOR_TOKEN (24+ random characters)"
  exit 1
fi
echo "::add-mask::$SSH_CONNECTOR_TOKEN"

echo "Installing dependencies"
python3 -m venv /tmp/venv
/tmp/venv/bin/pip install -q -r plugins/ssh-connector/requirements.txt

CFG=/tmp/servers.yaml
if [ -n "${SSH_CONNECTOR_SERVERS:-}" ]; then
  printf '%s\n' "$SSH_CONNECTOR_SERVERS" > "$CFG"; SRC="secret SSH_CONNECTOR_SERVERS"
else
  cp config/github-session.yaml "$CFG"; SRC="GitHub session profile (BGDB + demo)"
fi
mkdir -p ~/.ssh && chmod 700 ~/.ssh
if [ -n "${SSH_CONNECTOR_KEY:-}" ]; then
  printf '%s\n' "$SSH_CONNECTOR_KEY" > ~/.ssh/id_ed25519 && chmod 600 ~/.ssh/id_ed25519
fi
# SSH host keys must be independently verified before the runner trusts BGDB.
if [ -n "${SSH_CONNECTOR_KNOWN_HOSTS:-}" ]; then
  printf '%s\n' "$SSH_CONNECTOR_KNOWN_HOSTS" > ~/.ssh/known_hosts
  chmod 600 ~/.ssh/known_hosts
fi


start_server() {
  SSH_CONNECTOR_CONFIG="$CFG" SSH_CONNECTOR_AUTH_LOG=/tmp/auth.log SSH_CONNECTOR_PUBLIC_URL="${PUBLIC_URL:-}" nohup /tmp/venv/bin/python plugins/ssh-connector/server.py \
    --http --host 127.0.0.1 --port 8765 >> /tmp/server.log 2>&1 &
  echo $! > /tmp/server.pid
}
start_server

# --- Публичен HTTPS адрес / Public HTTPS address ---
# 1) Tailscale Funnel: ПОСТОЯНЕН адрес https://ssh-connector.<tailnet>.ts.net (не се сменя при рестарт)
# 2) Резерва: временен trycloudflare тунел (адресът се сменя при всеки рестарт)
TUNNEL=""
URL=""
if command -v tailscale >/dev/null 2>&1 && tailscale status >/dev/null 2>&1; then
  # Постоянно име на устройството -> постоянен адрес https://ssh-connector.<tailnet>.ts.net
  sudo tailscale set --hostname=ssh-connector || true
  # При край или спиране махаме устройството от мрежата, за да остане името свободно (без ssh-connector-1, -2 ...)
  trap 'sudo tailscale funnel reset >/dev/null 2>&1 || true; sudo tailscale logout >/dev/null 2>&1 || true' EXIT INT TERM
  sleep 5
  # Името на устройството в Tailscale (напр. ssh-connector.tail1234.ts.net), без крайната точка
  TS_NAME=$(tailscale status --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["Self"]["DNSName"].rstrip("."))' || true)
  # Изрично издаваме HTTPS сертификата (Let's Encrypt), за да не чакаме първата заявка; резултатът отива в диагностиката
  if [ -n "$TS_NAME" ]; then
    if timeout 120 sudo tailscale cert --cert-file /tmp/ts.crt --key-file /tmp/ts.key "$TS_NAME" >/tmp/ts-cert.log 2>&1; then
      echo "cert: OK" >> /tmp/ts-diag.log
    else
      { echo "cert: FAILED"; tail -3 /tmp/ts-cert.log; } >> /tmp/ts-diag.log
    fi
    sudo rm -f /tmp/ts.key /tmp/ts.crt   # ключа не го пазим на диска
  fi
  # Пускаме Funnel във фонов режим: публичен 443 -> локалния сървър на порт 8765
  if [ -n "$TS_NAME" ] && timeout 60 sudo tailscale funnel --bg http://127.0.0.1:8765 >/tmp/tunnel.log 2>&1; then
    URL="https://$TS_NAME"; TUNNEL=funnel
  else
    echo "::warning::Tailscale Funnel failed, falling back to trycloudflare"; cat /tmp/tunnel.log || true
  fi
fi

if [ -z "$URL" ]; then
  # Резервен вариант: временен тунел на Cloudflare
  curl -fsSL -o /tmp/cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
  chmod +x /tmp/cloudflared
  nohup /tmp/cloudflared tunnel --no-autoupdate --url http://127.0.0.1:8765 > /tmp/tunnel.log 2>&1 &
  for i in $(seq 1 60); do
    URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/tunnel.log | head -1 || true)
    [ -n "$URL" ] && break
    sleep 2
  done
  [ -n "$URL" ] || { echo "::error::Tunnel did not start"; cat /tmp/tunnel.log; exit 1; }
  TUNNEL=cloudflare
fi

# v1.3.2: рестарт на сървъра с публичния адрес, за да работят еднократните връзки за sudo паролата
kill "$(cat /tmp/server.pid)" 2>/dev/null || true
sleep 1
export PUBLIC_URL="$URL"   # остава и при автоматичен рестарт по-долу
start_server

# Проверка: без токен адресът трябва да връща 401 (защитен). Първият сертификат на Funnel може да отнеме до минута.
code=000
for i in $(seq 1 40); do
  code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$URL/mcp" || true)
  [ "$code" = 401 ] && break
  sleep 3
done

# Диагностика на Tailscale (без тайни): версия, сертификат, Funnel
if [ "$TUNNEL" = funnel ]; then
  { echo "tailscale: $(tailscale version | head -1)"; echo "funnel status:"; sudo tailscale funnel status 2>&1 | head -8; } >> /tmp/ts-diag.log
fi
DIAG=$(cat /tmp/ts-diag.log 2>/dev/null || true)

START=$(date -u +%FT%TZ)
END_TS=$(( $(date +%s) + $(awk "BEGIN{print int($HOURS*3600)}") ))
END=$(date -u -d "@$END_TS" +%FT%TZ)
STATUS_BASE="# Connector session
state: running
tunnel: $TUNNEL   (funnel = permanent URL / постоянен адрес)
url: $URL
claude_url: $URL/mcp   (header: Authorization = Bearer <SSH_CONNECTOR_TOKEN>)
chatgpt_url: $URL/<SSH_CONNECTOR_TOKEN>/mcp
public_check_without_token: HTTP $code (401 = protected, OK)
servers: $SRC
started: $START
ends: $END
run: ${GITHUB_SERVER_URL:-}/${GITHUB_REPOSITORY:-}/actions/runs/${GITHUB_RUN_ID:-}

Stop: put 'stop' in control/session. Restart: put 'start' plus anything new on line 2.

## Tailscale diagnostics
\`\`\`
$DIAG
\`\`\`"
publish "$STATUS_BASE" running

echo "Running until $END  ($URL)"
last_lines=0; last_pub=0
while [ "$(date +%s)" -lt "$END_TS" ]; do
  sleep 30
  # Publish the latest incoming requests (header names / lengths / result only, never secrets), max once a minute.
  if [ -s /tmp/auth.log ]; then
    lines=$(wc -l < /tmp/auth.log)
    if [ "$lines" != "$last_lines" ] && [ $(( $(date +%s) - last_pub )) -ge 60 ]; then
      publish "$STATUS_BASE

## Last incoming requests (UTC, no secrets)
\`\`\`
$(tail -15 /tmp/auth.log)
\`\`\`" requests
      last_lines=$lines; last_pub=$(date +%s)
    fi
  fi
  if ! kill -0 "$(cat /tmp/server.pid)" 2>/dev/null; then
    echo "Server died, restarting"; tail -20 /tmp/server.log; start_server
  fi
  # Проверка дали тунелът още работи
  if [ "$TUNNEL" = cloudflare ] && ! pgrep -f "cloudflared tunnel" >/dev/null; then
    echo "::error::Tunnel stopped"; break
  fi
  if [ "$TUNNEL" = funnel ] && ! sudo tailscale funnel status 2>/dev/null | grep -q 8765; then
    echo "Funnel lost, re-enabling"; timeout 60 sudo tailscale funnel --bg http://127.0.0.1:8765 || true
  fi
done

publish "# Connector session
state: finished
url: $URL
started: $START
ended: $(date -u +%FT%TZ)" finished
