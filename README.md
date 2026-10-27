# ssh-connector

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
| Area | Tools |
|---|---|
| Servers | `list_servers`, `run_command`, `run_on_many`, `run_on_group`, `history` |
| Snippets | `list_snippets`, `run_snippet` |
| Shell | `shell_open`, `shell_send`, `shell_close`, `list_shells` |
| SFTP | `sftp_list`, `sftp_read`, `sftp_write`, `sftp_upload`, `sftp_download`, `sftp_manage` |
| Tunnels | `port_forward`, `list_forwards`, `stop_forward` |
| Jobs | `start_job`, `job_status` |
| Events | `start_watch`, `stop_watch`, `get_events` |

Keep `servers.yaml` and keys out of git (already in .gitignore).
