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

## Install
```bash
git clone https://github.com/ykinfohome7/ssh-connector && cd ssh-connector
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp servers.example.yaml servers.yaml   # edit it
```

## Claude Code
```bash
claude mcp add ssh -- $(pwd)/.venv/bin/python $(pwd)/server.py
```

## ChatGPT Codex (CLI / IDE) — local, same as Claude Code
```bash
codex mcp add ssh -- $(pwd)/.venv/bin/python $(pwd)/server.py
```
or in `~/.codex/config.toml`:
```toml
[mcp_servers.ssh]
command = "/path/to/ssh-connector/.venv/bin/python"
args = ["/path/to/ssh-connector/server.py"]
```

## ChatGPT (web / app) — HTTP mode
ChatGPT cannot start local programs, it needs a public HTTPS URL. Run the connector in HTTP mode,
protected by a secret token, and expose it with a tunnel.

```bash
export SSH_CONNECTOR_TOKEN=$(python3 -c 'import secrets;print(secrets.token_urlsafe(32))')
echo $SSH_CONNECTOR_TOKEN            # keep it secret
.venv/bin/python server.py --http --port 8765
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
