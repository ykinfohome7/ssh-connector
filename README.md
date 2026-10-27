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

## ChatGPT Codex (~/.codex/config.toml)
```toml
[mcp_servers.ssh]
command = "/path/to/ssh-connector/.venv/bin/python"
args = ["/path/to/ssh-connector/server.py"]
```

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
