# ssh-connector

Local MCP server that lets **Claude Code** and **ChatGPT Codex** run commands directly over SSH on multiple Debian and Red Hat servers. No gateway in between.

## Features
- Primary + fallback addresses per server, automatic failover
- Connect / login timeouts, keepalive, retries with backoff, transparent reconnect
- Up to 10 parallel sessions per server (sshd MaxSessions default)
- Background jobs for long commands (`start_job`, `job_status`)
- Event watchers via journalctl: `service_errors`, `crashes` (OOM, segfault, failed units), `logins`

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
`list_servers`, `run_command`, `run_on_many`, `start_job`, `job_status`, `start_watch`, `stop_watch`, `get_events`

Keep `servers.yaml` and keys out of git (already in .gitignore).
