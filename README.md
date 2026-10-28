<div align="center">

# 🔐 SSH Connector

**Work directly over SSH on many servers — from Claude and ChatGPT.**
Commands, interactive terminals, SFTP, tunnels, failover, events and a safe `sudo` password — no gateway in between.

[![Version](https://img.shields.io/badge/version-1.3.2-blue)](CHANGELOG.md)
[![Tests](https://github.com/ykinfohome7/ssh-connector/actions/workflows/test.yml/badge.svg)](https://github.com/ykinfohome7/ssh-connector/actions/workflows/test.yml)
[![License: GPL-3.0](https://img.shields.io/badge/license-GPL--3.0-green)](LICENSE)
[![Stars](https://img.shields.io/github/stars/ykinfohome7/ssh-connector?style=social)](https://github.com/ykinfohome7/ssh-connector/stargazers)

**English** · [Български](README.bg.md)

[Install](#-install) · [Quick start](#-quick-start) · [Commands](docs/COMMANDS.md) · [Security](docs/SECURITY-STANDARDS.md) · [Changelog](CHANGELOG.md)

</div>

---

## ✨ What it does

| | |
|---|---|
| 🖥️ **Many servers** | Debian and Red Hat, primary + fallback addresses, automatic failover, retries, keepalive |
| ⌨️ **Real terminal** | Interactive shell with PTY that keeps state (`cd`, variables, running programs, Ctrl+C) |
| 🔑 **Safe sudo** | `sudo_password` — type it on a one-time page, take it from the profile, or generate it with *your* length and characters. Never in the chat |
| 📁 **Files** | SFTP: list, read, write, upload, download, mkdir, remove, rename |
| 🚇 **Tunnels** | Local port forwarding, jump hosts (bastion) |
| 👀 **Events** | Watch errors, crashes / OOM and logins without asking |
| 🧩 **Groups & snippets** | Run one command on a whole group; saved commands |
| 🌐 **Tailscale** | Status, devices, auth keys — and a permanent HTTPS address via Funnel |
| 📖 **Help built in** | `help` lists all **45 commands** in BG and EN with a ready example |

## 📦 Install

Pick the way that fits you.

### Claude Code — plugin (recommended)
```bash
claude plugin marketplace add ykinfohome7/ssh-connector
claude plugin install ssh-connector@ykinfohome7-tools
```
Inside a session: `/plugin marketplace add ykinfohome7/ssh-connector`, then `/plugin install ssh-connector@ykinfohome7-tools`.
The first start creates a private virtualenv (~30 s, only once).

### ChatGPT Codex — plugin
```bash
codex plugin marketplace add ykinfohome7/ssh-connector
```
Then enable **ssh-connector** in the plugin list.

### ChatGPT / Claude apps (web, phone) — connector over HTTPS
They need a public HTTPS address. Use the [always-on server](#-always-on-server) or the [GitHub Actions session](#%EF%B8%8F-github-actions-session), then add the connector:
- **ChatGPT:** Settings → Apps & Connectors → Advanced → Developer mode → *Create* → URL `https://<host>/<TOKEN>/mcp`, no authentication.
- **Claude:** Settings → Connectors → *Add custom connector* → URL `https://<host>/mcp`, header `Authorization: Bearer <TOKEN>`.

After an update press **Refresh** on the connector to load new commands. With Tailscale Funnel the address stays the same.

### Download
- ⬇️ **[Latest version (ZIP)](https://github.com/ykinfohome7/ssh-connector/archive/refs/heads/main.zip)**
- 🏷️ **[Releases](https://github.com/ykinfohome7/ssh-connector/releases)**
- `git clone https://github.com/ykinfohome7/ssh-connector`

### Manual MCP (no plugin)
```bash
git clone https://github.com/ykinfohome7/ssh-connector && cd ssh-connector
claude mcp add ssh -- sh $(pwd)/plugins/ssh-connector/bin/run.sh     # Claude Code
codex  mcp add ssh -- sh $(pwd)/plugins/ssh-connector/bin/run.sh     # Codex
```

## 🚀 Quick start

1. Create `~/.ssh-connector/servers.yaml` from [`servers.example.yaml`](servers.example.yaml) (or set `SSH_CONNECTOR_CONFIG`). Needs `python3`.
2. Ask in plain words, e.g. *"show disk usage on all web servers"* — or call commands directly:

```json
{"tool": "server_test", "arguments": {"name": "web1"}}
{"tool": "run_command", "arguments": {"server": "web1", "command": "df -h"}}
{"tool": "help", "arguments": {}}
```

Full list with parameters and examples: **[docs/COMMANDS.md](docs/COMMANDS.md)**.

## 🔑 sudo password (new in 1.3.2)

When a command needs `sudo`, the connector does not hang — it asks you to choose:

| Mode | What happens |
|---|---|
| `prompt` | You get a **one-time HTTPS link** (2 min). Type the password there; it is checked on the server |
| `profile` | Uses a preset value from an environment variable / GitHub Secret. Only its **name** is stored |
| `generate` | Random password — **you choose** length (16–128) and characters. Shown once; set on the server only after you press *"I saved it"* |

The password is never in the chat, in the command, in the logs or in the history. It reaches `sudo` over stdin.

## 🌍 Always-on server
Run once on one of your servers (e.g. from Termius):
```bash
curl -fsSL https://raw.githubusercontent.com/ykinfohome7/ssh-connector/main/install-server.sh | sudo bash
```
Installs a systemd service, an HTTPS tunnel, a token and an SSH key, and prints what to paste into Claude and ChatGPT. Show it again: `sudo ssh-connector-info`.

## ☁️ GitHub Actions session
An on-demand backend in GitHub Actions with a **permanent** address `https://ssh-connector.<tailnet>.ts.net` (Tailscale Funnel; fallback: Cloudflare quick tunnel).
- Start / restart: edit [`control/session`](control/session) (`start` + anything new on line 2) or *Actions → connector-session → Run workflow*.
- Stop: put `stop` in `control/session`.
- Status and address: [`control/status.md`](control/status.md).

Full setup (secrets, Tailscale, BGDB Codespaces): **[docs/GITHUB-SESSION.md](docs/GITHUB-SESSION.md)**.

## 🛡️ Security
- Passwords, keys and tokens are **never** shown or stored in files — only environment-variable names and paths.
- SSH keys: **Ed25519**, RSA 4096 only for old systems, rotation every **40–90 days** (`credentials_rotate`).
- Requests without the token get `401`. Treat the token like an SSH key.
- Found a vulnerability? See **[SECURITY.md](SECURITY.md)**.

## 📚 Documentation
| Document | English | Български |
|---|---|---|
| Commands | [COMMANDS.md](docs/COMMANDS.md) | [COMMANDS.bg.md](docs/COMMANDS.bg.md) |
| Security standards | [SECURITY-STANDARDS.md](docs/SECURITY-STANDARDS.md) | [SECURITY-STANDARDS.bg.md](docs/SECURITY-STANDARDS.bg.md) |
| GitHub Actions session | [GITHUB-SESSION.md](docs/GITHUB-SESSION.md) | [GITHUB-SESSION.md](docs/GITHUB-SESSION.md) |
| Changelog | [CHANGELOG.md](CHANGELOG.md) | [CHANGELOG.md](CHANGELOG.md) |
| Contributing | [CONTRIBUTING.md](CONTRIBUTING.md) | [CONTRIBUTING.md](CONTRIBUTING.md) |

## ❤️ Like it? Want something?
- ⭐ **Like it** — give the project a [Star](https://github.com/ykinfohome7/ssh-connector/stargazers).
- 💡 **Want a feature** — [open a feature request](https://github.com/ykinfohome7/ssh-connector/issues/new?template=feature_request.yml).
- 🐞 **Found a bug** — [report it](https://github.com/ykinfohome7/ssh-connector/issues/new?template=bug_report.yml).

## 📄 License
[GPL-3.0](LICENSE) © ykinfohome7
