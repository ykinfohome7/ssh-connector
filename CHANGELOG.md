# Changelog / Промени по версии

All notable changes. Format: [Keep a Changelog](https://keepachangelog.com/), versions: [SemVer](https://semver.org/).
> _Всички по-важни промени. Най-новото е най-горе._

## [1.3.2] — 2026-10-28
### Added / Добавено
- `sudo_password` (45th command): choose how the sudo password is provided — `prompt` (one-time HTTPS page), `profile` (preset from an environment variable / secret) or `generate` (your length 16–128 and character set). Never in chat, command, logs or history.
  > _Нова команда `sudo_password`: напиши / от профила / генерирай — ти избираш дължина и символи. Никога в чата._
- `run_command(sudo=true)` no longer hangs: it answers `sudo_password_required` with the three choices; with a password it uses `sudo -S` over stdin.
- `shell_send`: detects `[sudo] password for…` (`sudo_prompt: true`); `use_sudo_password=true` types the password.
- The connector reads its public address from `SSH_CONNECTOR_PUBLIC_URL` or `SSH_CONNECTOR_PUBLIC_URL_FILE` at use time — no restart when the address changes.
### Docs / Документация
- New README in English and Bulgarian, `CHANGELOG`, `CONTRIBUTING`, `SECURITY`, issue templates (💡 feature, 🐞 bug).

## [1.3.1] — 2026-10-28
### Fixed / Поправено
- ChatGPT / Codex plugin: `codex-mcp.json` wrapped in `mcpServers`, `cwd` added.
- Sanitized CI diagnostic logs; test credentials are never published.

## [1.3.0] — 2026-10-27
### Added / Добавено
- 44 commands: server profiles (`server_get`, `server_rename`, `server_set_primary`, `server_failover`), `credentials_set`, `credentials_rotate` (Ed25519 / RSA 4096, 40–90 days), `session_configure`, Tailscale (`tailscale_status`, `tailscale_devices`, `tailscale_keys`, `tailscale_key_create`, `tailscale_key_revoke`), `help` in BG/EN with examples.
- Command docs generated from the code (`docs/COMMANDS.md`, `docs/COMMANDS.bg.md`).
- Plugins report the right version when installed.

## [1.2.0]
### Added / Добавено
- Permanent HTTPS address through **Tailscale Funnel** (fallback: Cloudflare quick tunnel).
- `version_info`, `-v / --version`.
- Server profile management: `server_add`, `server_update`, `server_remove`, `server_test`, aliases.
- BGDB Codespaces over Tailscale in the GitHub Actions session; verified host keys; passwords only from secrets.

## [1.0.0]
### Added / Добавено
- First release: many servers with failover, jump hosts, groups, snippets, `sudo`, interactive shells, SFTP, port forwarding, background jobs, event watchers, history, HTTP mode with token.
- Always-on server installer (`install-server.sh`) and on-demand GitHub Actions session.

[1.3.2]: https://github.com/ykinfohome7/ssh-connector/compare/d06f28c...main
[1.3.1]: https://github.com/ykinfohome7/ssh-connector/commit/d06f28c
[1.3.0]: https://github.com/ykinfohome7/ssh-connector/pull/2
