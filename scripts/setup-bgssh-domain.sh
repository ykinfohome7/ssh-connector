#!/usr/bin/env bash
# Configure bgssh.abrdns.com HTTPS ingress on a PUBLICLY REACHABLE Debian host.
# Never runs on Codespaces or GitHub Actions. Never changes DNS or SSH firewalls.
set -Eeuo pipefail
DOMAIN=bgssh.abrdns.com
BACKEND=http://127.0.0.1:8765
SITE=/etc/caddy/sites-enabled/bgssh.caddy
MAIN=/etc/caddy/Caddyfile

info() { printf '[BGSSH] %s\n' "$*"; }
fail() { printf '[BGSSH] ERROR: %s\n' "$*" >&2; exit 1; }
[[ "${EUID}" -eq 0 ]] || fail "Run as root: sudo bash scripts/setup-bgssh-domain.sh"
[[ "${GITHUB_ACTIONS:-false}" != true && -z "${CODESPACES:-}" ]] || fail "Requires a persistent public Debian server, not GitHub Actions or Codespaces."
[[ -r /etc/os-release ]] || fail 'Cannot detect operating system'
. /etc/os-release
[[ "${ID:-}" == debian ]] || fail 'Requires Debian'
command -v systemctl >/dev/null || fail 'systemd is required'

mode="${1:---check}"
case "$mode" in --check|--install) ;; *) fail 'Usage: setup-bgssh-domain.sh [--check|--install]' ;; esac

info 'Checking local MCP backend'
systemctl is-active --quiet ssh-connector || fail 'ssh-connector is not running; install it first.'
code="$(curl -sS -X POST -o /dev/null -w '%{http_code}' --connect-timeout 3 --max-time 8 "$BACKEND/mcp" 2>/dev/null || true)"
[[ "$code" == 401 ]] || fail "Local MCP is not protected/ready (HTTP $code; expected 401)."
info 'Local MCP responds HTTP 401 without authentication (expected).'

info 'Public DNS A records (compare with this host public IP):'
getent ahostsv4 "$DOMAIN" 2>/dev/null | awk '{print $1}' | sort -u || true
info 'Ensure domain points to this host, and TCP 80/443 are publicly reachable.'

if [[ "$mode" == --check ]]; then
  info 'Read-only checks complete. Run --install on the intended public Debian host.'
  exit 0
fi

# Do not overwrite an existing Caddy config for other HTTPS sites.
main_existed=0
[[ -e "$MAIN" ]] && main_existed=1
if [[ "$main_existed" == 1 ]] && ! grep -Fq 'import /etc/caddy/sites-enabled/*.caddy' "$MAIN"; then
  fail "$MAIN exists without an import. Add 'import /etc/caddy/sites-enabled/*.caddy' manually, preserving other sites."
fi

if ! command -v caddy >/dev/null 2>&1; then
  info 'Installing Caddy from Debian packages'
  apt-get update
  DEBIAN_FRONTEND=noninteractive apt-get install -y caddy
fi
install -d -m 0755 /etc/caddy/sites-enabled
cat > "$SITE" <<'CADDY'
# BGSSH custom-domain HTTPS. Caddy handles its own certificate renewal.
# Backend port 8765 must listen ONLY on 127.0.0.1.
bgssh.abrdns.com {
    @health path /health
    respond @health 404
    reverse_proxy 127.0.0.1:8765
}
CADDY
chmod 0644 "$SITE"
if [[ "$main_existed" == 0 ]]; then
  printf 'import /etc/caddy/sites-enabled/*.caddy\n' > "$MAIN"
fi
caddy validate --config "$MAIN" --adapter caddyfile || fail 'Caddy validation failed'
systemctl enable --now caddy
systemctl reload caddy || systemctl restart caddy
info 'Checking public HTTPS with verified TLS certificate'
code="$(curl -sS -X POST -o /dev/null -w '%{http_code}' --connect-timeout 5 --max-time 20 "https://$DOMAIN/mcp" 2>/dev/null || true)"
if [[ "$code" == 401 ]]; then
  info 'SUCCESS: public HTTPS works with valid TLS and requires authentication.'
else
  info "Public HTTPS not verified (HTTP $code, expected 401). Check DNS, NAT, TCP 80/443, and: journalctl -u caddy"
  exit 2
fi
