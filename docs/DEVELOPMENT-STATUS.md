# Development status — read-only monitoring

Updated: 2026-11-04 ~21:45 UTC by CLAUDE_CODE. Updated again ~22:15 UTC. Connector version on this branch: **1.4.1** (not released); MCP tools: **60** (48 + 8 read-only SNMP + 4 read-only RDP/Windows), SNMP approved by the owner on 2026-11-04; RDP requested by the owner on 2026-11-05.

| Area | State | Owner | Notes |
|---|---|---|---|
| Monitor engine (poll, debounce, alerts) | implemented, offline-tested | CLAUDE_CODE | bounded concurrency, per-target deadline, graceful SIGTERM/SIGINT |
| Persistent state | implemented, tested | CLAUDE_CODE | schema 2, v1 migration, lock, corruption recovery, 0600 |
| Notifications | implemented, tested | CLAUDE_CODE | HTTPS only, no redirects, host allowlist, cooldown, hourly cap |
| SNMP client (GET/GETNEXT/GETBULK/WALK) | implemented, fake-agent tested | CLAUDE_CODE | no SET |
| SNMP PySNMP backend | written, **never executed** | CLAUDE_CODE | **BLOCKED**: PyPI 403 |
| 10GbE / interface monitoring | implemented, tested | CLAUDE_CODE | link, error rate, flapping, utilisation events; rates survive restarts |
| ENTITY-MIB / ENTITY-SENSOR-MIB | implemented, tested | CLAUDE_CODE | UNAVAILABLE when absent |
| Real HD adapter | standard MIBs only | CLAUDE_CODE | no vendor OID verified |
| Cisco / UniFi adapters | placeholders | — | |
| JSON logging + redaction | implemented, tested | CLAUDE_CODE | |
| CI for monitoring tests | **BLOCKED** | owner | workflow edit refused (403); patch in `docs/CI-MONITORING-STEP.md` |
| Proxmox VE read-only API | in progress on `codex/proxmox-readonly-api` | CODEX (Issue #13) | not touched by CLAUDE_CODE |
| MCP tools for SNMP (8) | implemented, offline-tested | CLAUDE_CODE | `snmp_health`, `snmp_device_info`, `snmp_get`, `snmp_getnext`, `snmp_getbulk`, `snmp_walk`, `snmp_interfaces`, `snmp_interface_stats`; see `docs/SNMP.md` |
| Installed plugin (Claude Code / Codex) | 1.4.1, isolated install test in CI | CLAUDE_CODE | `tests/test_installed_plugin.py` via `tests/test_plugins.py`; update steps in `docs/PLUGIN-AND-ENDPOINT.md` |
| Connector address report (`tailscale_status`) | implemented, mock-tested | CLAUDE_CODE | stdio / HTTP, Serve / Funnel / unknown, verified or not; no real Tailscale contacted |
| RDP / Windows checks | implemented, offline-tested (fake RDP listener) | CLAUDE_CODE | `rdp_check`, `rdp_tunnel`, `windows_health`, `rdp_sessions`; see `docs/RDP.md`; no real Windows host contacted |
| Deployment / systemd | **NOT DEPLOYED** | owner / CLAUDE_CODE | approved by the owner on 2026-11-05, but the development sandbox has no SSH client, no route and no credentials to the KSSH server; runbook in PR #14 report |

## Coordination with the Proxmox branch

Observed at 21:08 UTC: branch `codex/proxmox-readonly-api` (head `f6d5936`) adds only its own files: `monitoring/proxmox_api.py`, `monitoring/proxmox_format.py`, `tests/test_proxmox_api.py`, `tests/test_proxmox_security.py`, `docs/PROXMOX-API-MONITORING.md`, `.github/workflows/proxmox-api-offline.yml`. **No file overlaps with this branch.** Commit author names there are YAVOR / BGDB; this report does not attribute them to any agent.

Note for integration: this branch makes `monitoring/` a Python package (`monitoring/__init__.py`). Modules there should import siblings relatively (`from .errors import ...`).

## Integration contract for the Proxmox module

The engine consumes any async check returning:

```json
{"ok": true, "status": "UP|DOWN|UNKNOWN", "error_code": null, "detail": "...", "...": "data"}
```

`DOWN` only for device-side failures (unreachable, timeout, auth, API error); `UNKNOWN` for our own setup problems (missing token, dependency, config, deadline). A `proxmox` section per target can then be dispatched from `monitor._run_checks` without changing state, notification or deadline logic.

## SNMP MCP tools — packaging

The plugin is installed as the folder `plugins/ssh-connector` only, so the SNMP library is copied from `monitoring/` into `plugins/ssh-connector/kssh_snmp/` by `scripts/sync_plugin_snmp.py`; `tests/test_plugin_snmp.py` fails when the copies differ. `pysnmp` is **not** added to the plugin requirements (unverified); without it the tools answer `UNKNOWN / DEPENDENCY_MISSING`.

`docs/COMMANDS*.md` were not regenerated: on `main` they already differ from the generator output and contain hand-written notes. The SNMP group is registered in `scripts/gen_commands_docs.py`; the SNMP commands are documented in `docs/SNMP.md`.
