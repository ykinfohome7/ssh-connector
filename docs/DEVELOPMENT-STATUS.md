# Development status — read-only monitoring

Updated: 2026-11-04 (UTC) by CLAUDE_CODE. Version of the connector itself: 1.3.3 (48 MCP tools) — unchanged.

| Area | State | Owner | Notes |
|---|---|---|---|
| Monitor engine (poll, state, alerts) | implemented, offline-tested | CLAUDE_CODE | PR #12 + `claude/monitor-hardening-snmp` |
| SNMP client (GET/GETNEXT/GETBULK/WALK) | implemented, fake-agent tested | CLAUDE_CODE | no SET |
| SNMP PySNMP backend | written, **never executed** | CLAUDE_CODE | blocked: PyPI 403 |
| IF-MIB / IF-X-MIB interfaces + rates | implemented, tested | CLAUDE_CODE | rollover, reboot, renumbering, flapping |
| ENTITY-MIB / ENTITY-SENSOR-MIB | implemented, tested | CLAUDE_CODE | UNAVAILABLE when absent |
| Real HD adapter | standard MIBs only | CLAUDE_CODE | no vendor OID verified |
| Cisco / UniFi adapters | placeholders | — | |
| JSON logging + redaction | implemented, tested | CLAUDE_CODE | |
| CI for monitoring tests | **prepared, blocked** | owner | workflow edit refused for Claude's integration (403); patch in `docs/CI-MONITORING-STEP.md` |
| Proxmox VE read-only API | not started here | CODEX | Issue #13, branch `codex/proxmox-readonly-api` |
| MCP tools for SNMP (`snmp_get`, `snmp_walk`, …) | not exposed | — | would change the 48-tool contract; needs a decision |
| RDP / Windows checks | not started | — | |
| Deployment / systemd | not started | — | requires explicit approval |

## Proposed MCP tool names (not registered yet)

`snmp_get`, `snmp_getnext`, `snmp_walk`, `snmp_getbulk`, `snmp_device_info`, `snmp_interfaces`, `snmp_interface_stats`, `snmp_health` — no name conflicts with existing KSSH tools were found by name. Registering them requires updating the 48-tool assertions in `tests/test_plugins.py` and the plugin manifests.

## Integration contract for CODEX (Proxmox module)

The engine consumes any async check that returns:

```json
{"ok": true, "status": "UP|DOWN|UNKNOWN", "error_code": null, "detail": "...", "...": "data"}
```

`DOWN` only for device-side failures (unreachable, timeout, auth, API error); `UNKNOWN` for our own setup problems (missing token, missing dependency, config). A `proxmox` section per target can then be dispatched from `monitor._check_target` without changing state logic.
