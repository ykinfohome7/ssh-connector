# GitHub Actions session → BGDB Codespaces through Tailscale

[← README](../README.md) · [Български README](../README.bg.md)


The repository includes an on-demand GitHub Actions backend exposed over HTTPS through
**Tailscale Funnel** at a **permanent** URL `https://ssh-connector.<tailnet>.ts.net`
(fallback: a temporary Cloudflare quick tunnel if Tailscale is not configured).
> _Постоянен адрес през Tailscale Funnel; не се сменя при рестарт._

The backend session is **temporary** (5 hours by default).
It is NOT the same as the BGDB Codespace itself.

Default session host list: `config/github-session.yaml`. It keeps `rebex`
and `failover` and adds `BGDB-Codespaces` (alias `github_bgdb`):
`100.65.111.82:2222`, user `bgadmin`, Tailscale private route. SSH
port and IP must be rechecked after a Codespace rebuild or re-creation.

To authenticate **without committing passwords or Tailscale credentials**,
open this repository's **Settings -> Secrets and variables -> Actions** and
configure the following *repository secrets*:

1. `TAILSCALE_AUTHKEY`: tagged **ephemeral, reusable**, appropriately scoped
   Tailscale auth key for the CI runner to join the **same** tailnet as BGDB.
   Configure tailnet grants so the runner tag may reach BGDB SSH port 2222.
2. `BGDB_SSH_PASSWORD`: BGDB user's `bgadmin` SSH password. GitHub stores
   it encrypted and the connector references it through `password_env`,
   without adding the password to `servers.yaml` or logs.
3. `SSH_CONNECTOR_KNOWN_HOSTS`: **independently verified** SSH host public
   key line for the BGDB SSH daemon. For a nonstandard port the format is
   `[100.65.111.82]:2222 ssh-ed25519 AAAA...`. Inspect the server's
   `/etc/ssh/ssh_host_ed25519_key.pub` and compare its fingerprint locally;
   do not blindly trust a network-supplied fingerprint.

`SSH_CONNECTOR_TOKEN` remains required as before. If the optional
`SSH_CONNECTOR_SERVERS` secret is configured, its YAML **replaces** the
default profile list: add BGDB there too, or remove that override.

After creating secrets, restart the Actions session via workflow dispatch or
editing `control/session`. The Tailscale action connects first, then the
connector loads its hosts. Review `control/status.md` and the Actions logs.
With Funnel the URL stays the same across restarts (requires HTTPS certificates
and the `funnel` node attribute enabled in the tailnet, and `statedir` in the
workflow's Tailscale step). Only the Cloudflare fallback changes URL on restart. Do not put a token
in a publicly committed URL or support message.

The backend now exposes `server_add`, `server_update`, `server_remove`,
`server_test`, and server-name aliases. Runtime profile modifications persist
to the runner's local YAML **only until that runner ends**; for permanent
GitHub Actions configuration, update the reviewed `config/github-session.yaml`
or the encrypted `SSH_CONNECTOR_SERVERS` secret. SSH passwords must only be
set through GitHub Secrets or another suitable external secrets manager.

To control Claude Code inside BGDB, first authorize Claude Code interactively
as the Codespace's `vscode` user. Once private SSH actually works, normal
remote shell commands can work in `/workspaces/BGDB`; an MCP tunnel alone
does not authorize or log in to Claude Code.
