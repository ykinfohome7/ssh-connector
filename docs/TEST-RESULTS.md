# Test results — monitoring

Local ≠ CI. Each entry states where it ran. Nothing below was run against a real device.

## Run L1 — local, CLAUDE_CODE

| Field | Value |
|---|---|
| Time (UTC) | 2026-11-04T20:45Z |
| Branch | `claude/monitor-hardening-snmp` (working tree before first commit) |
| Environment | isolated Linux sandbox, Python 3.13.18, stdlib only, pysnmp **not installed** |
| Command | `python3 -W error::ResourceWarning -m unittest -v tests/test_monitoring_mvp.py tests/test_monitoring_snmp.py` |
| Result | **Ran 69 tests — OK** (0 failures, 0 errors, 0 skipped) |

Bugs found by these tests during development and fixed before commit:
1. With a non-PySNMP backend, missing secrets were not detected and the check became `DOWN/PROTOCOL_ERROR` instead of `UNKNOWN/SECRET_MISSING` → secrets are now resolved in `SnmpClient` before any backend call.
2. Unclosed test HTTP server sockets (ResourceWarning) → `server_close()`.

CLI smoke test (localhost only, closed port 9, secrets absent): exit 0, TCP `DOWN/UNREACHABLE`, SNMP `UNKNOWN/SECRET_MISSING`, state file mode `600`.

## Run CI — GitHub Actions

**The monitoring tests are not yet part of CI.** The workflow change was rejected for Claude's GitHub integration (HTTP 403 — no permission to modify `.github/workflows/`). The ready step is in [`docs/CI-MONITORING-STEP.md`](CI-MONITORING-STEP.md). Until the owner applies it, a green CI run on this branch proves only that existing KSSH tests still pass.

## Not executed

| Test | Status | Reason |
|---|---|---|
| PySNMP backend (any version, SHA/DES/AES) | **BLOCKED / NOT TESTED** | PyPI HTTP 403 in the dev environment |
| Real Real HD switch 192.168.30.10 | PENDING_EXPLICIT_APPROVAL | production device |
| pve1 / pve2 | PENDING_EXPLICIT_APPROVAL | production hosts; Proxmox API module is CODEX's (#13) |
| docker-compose test agent (snmpd) | NOT DONE | in-process fake agent used instead |
