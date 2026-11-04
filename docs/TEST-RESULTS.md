# Test results — monitoring

Local ≠ CI. Each entry states where it ran. Nothing below was run against a real device.

## Run L2 — local, CLAUDE_CODE (round 2)

| Field | Value |
|---|---|
| Time (UTC) | 2026-11-04T21:10Z |
| Branch | `claude/monitor-hardening-snmp` (tree published in the round-2 commits; SHA in PR #14 report) |
| Environment | isolated Linux sandbox, Python 3.13.18, stdlib only, pysnmp **not installed** |
| Command | `python3 -W error::ResourceWarning -m unittest tests/test_monitoring_mvp.py tests/test_monitoring_snmp.py tests/test_monitoring_engine.py` |
| Result | **Ran 98 tests — OK** (21 + 48 + 29; 0 failures, 0 errors, 0 skipped) |

New in `tests/test_monitoring_engine.py` (29 tests):

| Area | Tests |
|---|---|
| Regression | v1 state migration; v1 state loads through `main()`; corrupt persisted sample → baseline; unknown future schema rejected |
| Persistence | corrupt file moved aside (not deleted); oversized file rejected; round trip with mode 0600 |
| Concurrency | second process cannot take the state lock; `max_concurrency=2` observed as peak 2 of 6 targets |
| Timeout | hung target → `UNKNOWN/DEADLINE_EXCEEDED` in < 2 s, other targets still `UP`, hung task cancelled cleanly, no alert |
| Security | webhook URL validation (HTTPS only, no `user:pass@`, no control chars, host allowlist); disallowed host never contacted; URL never printed and scrubbed from logs; payload only whitelisted fields; real local 302 refused; allowlist not bypassed by `::ffff:`, octal, hex, integer, trailing-dot or CIDR spellings; unsafe inventories rejected (name with `/`, > 256 targets, interfaces without SNMP) |
| Notifications | per-key cooldown, hourly cap, DOWN/RECOVERED as separate keys; webhook failure never raises |
| Interfaces | config validation; include/exclude; LINK_DOWN only for admin-up ports; error-rate threshold; utilisation is an event not an outage; flapping across polls + cleanup; persistence across a restart (rates computed from the sample saved on disk); interface limit |
| CLI | exit codes 0 / 2 (bad config) / 3 (state locked) |

### Mutation check (do the tests catch real bugs?)

Each bug below was injected one at a time; the suite failed for every one and passed again after restoring the code:

| Injected bug | Result |
|---|---|
| admin-down ports reported as link outages | caught |
| notifier cooldown disabled | caught |
| webhook URLs with credentials accepted | caught |
| corrupt state file deleted instead of moved aside | caught |
| per-target deadline removed | caught |
| SNMP walk loop detection removed | caught |

## Run L1 — local, CLAUDE_CODE (round 1)

| Field | Value |
|---|---|
| Time (UTC) | 2026-11-04T20:45Z |
| Command | `python3 -W error::ResourceWarning -m unittest -v tests/test_monitoring_mvp.py tests/test_monitoring_snmp.py` |
| Result | **Ran 69 tests — OK** on the published tree `2825501` |

## Run CI — GitHub Actions

* Round 1, SHA `2825501`: [run 41911057412](https://github.com/ykinfohome7/ssh-connector/actions/runs/41911057412/job/126858399970) — **success**. This proves existing KSSH tests still pass. It does **not** run the monitoring tests.
* **The monitoring tests are not part of CI (M6 BLOCKED).** The workflow change was refused for Claude's GitHub integration (HTTP 403). Ready step: [`docs/CI-MONITORING-STEP.md`](CI-MONITORING-STEP.md). With round 2 the step should also list `tests/test_monitoring_engine.py`.

## Not executed

| Test | Status | Reason |
|---|---|---|
| PySNMP backend (any version, SHA/DES/AES) | **BLOCKED / NOT TESTED** | PyPI HTTP 403 in the dev environment |
| Real HD switch 192.168.30.10 | PENDING_EXPLICIT_APPROVAL | production device |
| pve1 / pve2 | PENDING_EXPLICIT_APPROVAL | production hosts; Proxmox API module is CODEX's (#13) |
| docker-compose test agent (snmpd) | NOT DONE | in-process fake agent used instead |
| Windows (non-POSIX) state lock | NOT TESTED | `fcntl` unavailable there; lock is skipped by design |
