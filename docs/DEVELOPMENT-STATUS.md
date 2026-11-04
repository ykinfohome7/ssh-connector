# Development status — read-only monitoring

Updated: 2026-11-04 ~21:10 UTC by CLAUDE_CODE. Connector version: 1.3.3 (48 MCP tools) — unchanged.

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
| MCP tools for SNMP | not exposed | — | changes the 48-tool contract; needs a decision |
| RDP / Windows checks | not started | — | |
| Deployment / systemd | not started | — | requires explicit approval |

## Coordination with the Proxmox branch

Observed at 21:08 UTC: branch `codex/proxmox-readonly-api` (head `f6d5936`) adds only its own files: `monitoring/proxmox_api.py`, `monitoring/proxmox_format.py`, `tests/test_proxmox_api.py`, `tests/test_proxmox_security.py`, `docs/PROXMOX-API-MONITORING.md`, `.github/workflows/proxmox-api-offline.yml`. **No file overlaps with this branch.** Commit author names there are YAVOR / BGDB; this report does not attribute them to any agent.

Note for integration: this branch makes `monitoring/` a Python package (`monitoring/__init__.py`). Modules there should import siblings relatively (`from .errors import ...`).

## Integration contract for the Proxmox module

The engine consumes any async check returning:

```json
{"ok": true, "status": "UP|DOWN|UNKNOWN", "error_code": null, "detail": "...", "...": "data"}
```

`DOWN` only for device-side failures (unreachable, timeout, auth, API error); `UNKNOWN` for our own setup problems (missing token, dependency, config, deadline). A `proxmox` section per target can then be dispatched from `monitor._run_checks` without changing state, notification or deadline logic.

## Proposed MCP tool names (not registered yet)

`snmp_get`, `snmp_getnext`, `snmp_walk`, `snmp_getbulk`, `snmp_device_info`, `snmp_interfaces`, `snmp_interface_stats`, `snmp_health`.
