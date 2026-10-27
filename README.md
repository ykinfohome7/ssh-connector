# ssh-connector

MCP SSH connector for Claude - run commands on multiple Debian and Red Hat servers.

## Tools
- `list_servers` - list configured servers
- `run_command` - run a shell command on a server
- `detect_os` - detect Debian or Red Hat family
- `install_package` - install a package with apt or dnf/yum

## Setup
```bash
git clone https://github.com/ykinfohome7/ssh-connector.git
cd ssh-connector
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp servers.example.yaml servers.yaml   # edit with your servers
```

## Claude Desktop config
```json
{
  "mcpServers": {
    "ssh-connector": {
      "command": "/path/to/ssh-connector/.venv/bin/python",
      "args": ["/path/to/ssh-connector/server.py"]
    }
  }
}
```

## Security
- Never commit `servers.yaml`, keys or passwords (they are in `.gitignore`).
- Prefer SSH keys; passwords are read only from environment variables.
- Unknown host keys are rejected unless `auto_add_host_key: true`.
