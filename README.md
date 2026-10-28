# ssh-connector

**Version: 1.3.0** · GitHub Actions SSH backend + Tailscale + MCP profile management. The current live connector may still run an older release until its GitHub Actions session is restarted. Use MCP `version_info` to check the actual running version.

Local MCP server that lets **Claude Code** and **ChatGPT Codex** work directly over SSH on multiple Debian and Red Hat servers, Termius-style. No gateway in between.

## Features
- Primary + fallback addresses, automatic failover, retries, keepalive, transparent reconnect
- Jump hosts (bastion / ProxyJump) via `jump:` in the config
- Tags / groups — run one command on a whole group
- Snippets — saved commands
- `sudo` option on every command
- Interactive shell sessions with PTY that keep state (cd, env, running programs, Ctrl+C)
- SFTP: list, read, write, upload, download, mkdir, remove, rename, stat
- Local port forwarding (tunnels)
- Background jobs for long commands
- Event watchers via journalctl: `service_errors`, `crashes`, `logins`
- Command history
- Up to 10 parallel sessions per server

## 1. Your server list
Create `~/.ssh-connector/servers.yaml` from [`servers.example.yaml`](servers.example.yaml)
(or point `SSH_CONNECTOR_CONFIG` to another file). Needs `python3` on the machine.

## 2a. Claude Code — plugin (recommended)
```bash
claude plugin marketplace add ykinfohome7/ssh-connector
claude plugin install ssh-connector@ykinfohome7-tools
```
Inside a session: `/plugin marketplace add ykinfohome7/ssh-connector`, then `/plugin install ssh-connector@ykinfohome7-tools`.
The first start creates a private virtualenv and installs dependencies (takes ~30 s once).

## 2b. ChatGPT Codex — plugin
```bash
codex plugin marketplace add ykinfohome7/ssh-connector
```
then enable `ssh-connector` from the plugin list (ChatGPT desktop app / Codex).

## 2c. Without plugins (manual MCP)
```bash
git clone https://github.com/ykinfohome7/ssh-connector && cd ssh-connector
claude mcp add ssh -- sh $(pwd)/plugins/ssh-connector/bin/run.sh     # Claude Code
codex  mcp add ssh -- sh $(pwd)/plugins/ssh-connector/bin/run.sh     # Codex
```

## Always-on server (use from iPhone / anywhere)
SSH into one of your servers (e.g. with Termius) and run:
```bash
curl -fsSL https://raw.githubusercontent.com/ykinfohome7/ssh-connector/main/install-server.sh | sudo bash
```
It installs the connector as a systemd service, opens a public HTTPS Cloudflare tunnel, creates a token and an
SSH key, and prints exactly what to paste into Claude and ChatGPT. Show it again any time with `sudo ssh-connector-info`.
Edit `/etc/ssh-connector/servers.yaml`, then `sudo systemctl restart ssh-connector`.
Note: a Cloudflare *quick* tunnel gets a new address when the tunnel restarts; for a fixed address use a named
Cloudflare tunnel or your own domain.

## ChatGPT (web / app) — HTTP mode (manual)
ChatGPT cannot start local programs, it needs a public HTTPS URL. Run the connector in HTTP mode,
protected by a secret token, and expose it with a tunnel.

```bash
export SSH_CONNECTOR_TOKEN=$(python3 -c 'import secrets;print(secrets.token_urlsafe(32))')
echo $SSH_CONNECTOR_TOKEN            # keep it secret
sh plugins/ssh-connector/bin/run.sh --http --port 8765
# in another terminal: public HTTPS URL via Cloudflare quick tunnel
cloudflared tunnel --url http://127.0.0.1:8765
```
In ChatGPT: Settings → Apps & Connectors → Advanced → enable Developer mode → Create connector.
- URL: `https://<your-tunnel>.trycloudflare.com/<SSH_CONNECTOR_TOKEN>/mcp`
- Authentication: No authentication (the secret is in the URL — never share it)

Clients that support headers (e.g. remote Codex) can use `https://<host>/mcp` with
`Authorization: Bearer <SSH_CONNECTOR_TOKEN>`:
```toml
[mcp_servers.ssh_remote]
url = "https://<host>/mcp"
bearer_token_env_var = "SSH_CONNECTOR_TOKEN"
```

Requests without the token get `401 unauthorized`. Anyone with the token can run commands on your servers —
treat it like an SSH key, and stop the HTTP server/tunnel when not in use.

## Tools
Full list with parameters and a ready-to-run example for every command:
**[docs/COMMANDS.md](docs/COMMANDS.md)** · на български: **[docs/COMMANDS.bg.md](docs/COMMANDS.bg.md)**.
Inside ChatGPT/Claude, the `help` command lists the same in BG and EN.

| Area | Tools |
|---|---|
| Info | `help`, `version_info`, `health_status` |
| Server profiles | `list_servers`, `server_get`, `server_add`, `server_update`, `server_rename`, `server_set_primary`, `server_failover`, `server_test`, `server_remove` |
| Credentials | `credentials_set`, `credentials_rotate` |
| Session | `session_configure` |
| Tailscale | `tailscale_status`, `tailscale_devices`, `tailscale_keys`, `tailscale_key_create`, `tailscale_key_revoke` |
| Commands | `run_command`, `run_on_many`, `run_on_group`, `list_snippets`, `run_snippet`, `history` |
| Jobs | `start_job`, `job_status` |
| Shell | `shell_open`, `shell_send`, `shell_close`, `list_shells` |
| SFTP | `sftp_list`, `sftp_read`, `sftp_write`, `sftp_upload`, `sftp_download`, `sftp_manage` |
| Tunnels | `port_forward`, `list_forwards`, `stop_forward` |
| Events | `start_watch`, `stop_watch`, `get_events` |

The command docs are generated from the code: after changing a command run
`python3 scripts/gen_commands_docs.py` (CI can run it with `--check`).
> _Документацията се генерира от кода — след промяна пуснете скрипта._

## Documentation / Документация
| Document | EN | BG |
|---|---|---|
| Commands / Команди | [COMMANDS.md](docs/COMMANDS.md) | [COMMANDS.bg.md](docs/COMMANDS.bg.md) |
| Security standards / Сигурност | [SECURITY-STANDARDS.md](docs/SECURITY-STANDARDS.md) | [SECURITY-STANDARDS.bg.md](docs/SECURITY-STANDARDS.bg.md) |
| v1.3 handoff brief / Задание | — | [HANDOFF-1.3.md](docs/HANDOFF-1.3.md) |

Keep `servers.yaml` and keys out of git (already in .gitignore).


## GitHub Actions -> BGDB Codespaces through Tailscale

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
