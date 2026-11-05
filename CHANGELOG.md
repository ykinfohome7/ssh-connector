# Changelog / Промени по версии

All notable changes. Format: [Keep a Changelog](https://keepachangelog.com/), versions: [SemVer](https://semver.org/).
> _Всички по-важни промени. Най-новото е най-горе._

## [Unreleased] — snippet library (Draft PR #17, not merged; active on the KSSH server)
### Added / Добавено
- Snippet library: 143 READ_ONLY command templates in 12 categories with EN/BG name, description, OS, privilege, typed parameters, risk level, approval flag, expected result and error handling (`plugins/ssh-connector/snippets/*.yaml`, engine `snippet_library.py`, docs `docs/SNIPPETS.md` / `docs/SNIPPETS.bg.md`, tests `tests/test_snippet_library.py`). No MCP tool added (60).
  > _Библиотека със 143 шаблона само за четене в 12 категории, с описание на EN и BG._
- 2026-11-05: 16 parameter-less snippets tried on pmg were added to the KSSH server's live `servers.yaml` and are run with `run_snippet` (18 snippets with `disk` and `mem`).
### Fixed / Поправено
- `network.vlans` returns 0 when a host has no VLAN interfaces.

## [1.4.1] — not released (Draft PR #14, not merged)
Version 1.4.0 was never released; 1.4.1 contains all of its changes below.
> _1.4.0 не е издавана; 1.4.1 съдържа всички промени по-долу._
### Changed / Променено
- Version 1.4.1 in `VERSION`, both `plugin.json`, README (EN/BG), `docs/PLUGIN-AND-ENDPOINT.md`. 60 MCP tools (48 existing + 8 SNMP + 4 RDP/Windows), measured in the isolated installed-plugin test.
### Added / Добавено
- Four read-only RDP / Windows MCP tools (60 total): `rdp_check` (RDP negotiation, NLA enforced or not, legacy security, verified TLS certificate, latency; no login), `rdp_tunnel` (SSH tunnel on 127.0.0.1 + `.rdp` file without password), `windows_health` (fixed PowerShell over SSH), `rdp_sessions` (`quser` over SSH). Mandatory `rdp.allowed_networks`. See `docs/RDP.md`.
  > _Четири RDP / Windows команди само за четене (общо 60): проверка без вход, SSH тунел с .rdp файл, здраве на Windows, активни сесии._
- `tailscale_status` returns an `endpoint` report: transport (`stdio` plugin / `http` backend), configured address (host only), Tailscale Serve (tailnet) vs Funnel (public) vs unknown, whether reachability was checked (`verify_reachability=true`, expects 401 without token), and safe MCP templates `https://<host>/<TOKEN>/mcp` / `Authorization: Bearer <TOKEN>`. Read-only: never runs `tailscale up/login/serve/funnel`.
  > _`tailscale_status` показва режима (stdio/HTTP, Serve/Funnel/unknown), конфигурирания адрес и дали е проверен — без токени._
- Isolated installed-plugin test (`tests/test_installed_plugin.py`, run from `tests/test_plugins.py`): only the plugin folder, real launcher, real MCP stdio, no repository root, no `PYTHONPATH`.
- `docs/PLUGIN-AND-ENDPOINT.md`: plugin update vs. connector Refresh; endpoint modes.
- Eight read-only SNMP MCP tools (56 total): `snmp_health`, `snmp_device_info`, `snmp_get`, `snmp_getnext`, `snmp_getbulk`, `snmp_walk`, `snmp_interfaces`, `snmp_interface_stats`. Configured device names only, mandatory `snmp.allowed_networks`, bounded requests, no SNMP SET. See `docs/SNMP.md`.
  > _Осем SNMP команди само за четене (общо 56). Само конфигурирани устройства, задължителен списък с разрешени мрежи, без SNMP SET._
- Standalone read-only monitoring engine in `monitoring/` (SNMP, 10GbE interfaces, persistent state, rate-limited HTTPS notifications, JSON logs). Not deployed.
### Security / Сигурност
- HTTP backend: uvicorn access log disabled, because it printed the secret-path URL (`/<TOKEN>/mcp`) in full.
- `tailscale` CLI calls are killed on timeout; tool output redacts the connector token, secret URL paths, bearer values and `tskey-…` keys.
- SNMPv3 by default; v1/v2c and DES only with explicit per-device opt-in; secrets only via environment-variable names; backend error texts never returned.
### Not verified / Непроверено
- The PySNMP backend has not been executed against any agent (dependency could not be installed in the development environment).
- RDP / Windows tools: only a local fake RDP listener and faked Windows command output; no real Windows host contacted.
- Tailscale endpoint report: only mock `tailscale` CLI/HTTP responses; no real tailnet, Serve, Funnel or backend was contacted. Codex plugin update steps were not executed (Codex CLI not available).

## [1.3.3] — 2026-10-28
### Added / Добавено
- Three MCP tools (48 total): `codespace_status` (all or exact name), `codespace_start` (wake via GitHub API), and `codespace_stop` (requires `confirm=true`).
- GitHub Codespaces lifecycle actions use the authenticated `gh` CLI and require the account's `codespace` scope / Codespaces lifecycle admin repository permission.
- Offline tests for safe name validation, list/start and refusal to stop without confirmation.
### Security / Сигурност
- Never accept GitHub tokens as tool parameters; invoke CLI with explicit arguments and no shell.
- Stop can disconnect a connector hosted inside the same Codespace; an offline Codespace cannot wake its own MCP backend.
### Docs / Документация
- Updated BG/EN README, command generator, references and plugin manifests to 1.3.3.

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
