# Security / code review — monitoring (PR #12 and follow-up)

- **Reviewer:** CLAUDE_CODE (agent_id `CLAUDE_CODE`)
- **Reviewed:** PR #12, branch `feature/health-monitor-mvp`, SHA `85bb7cb`; then own round-2 code
- **Fixes in:** branch `claude/monitor-hardening-snmp` (Draft PR #14)
- **Scope:** offline review and offline tests only. No real device, no production KSSH, no deployment.

## Round 1 — findings in PR #12

| ID | Severity | Finding | Status | Fix / evidence |
|---|---|---|---|---|
| — | CRITICAL | none found | — | — |
| H1 | HIGH | HTTPS webhook followed redirects incl. HTTPS→HTTP | FIXED (`85bb7cb`) | `_NoRedirect` opener; redirect tests incl. real local 302/307 servers |
| H2 | HIGH | SNMPv3 SHA + DES with pysnmp 7 unverified; crypto dependency not declared | **BLOCKED / NOT TESTED** | PyPI returned HTTP 403 in the dev environment; policy not bypassed. `requirements-monitoring.txt` notes the possible `pycryptodomex` need |
| H3 | HIGH | All SNMP errors collapsed into one reason | FIXED | `errors.ErrorCode`, `classify_error_indication` |
| M1 | MEDIUM | Missing pysnmp / secret counted as device DOWN (false alarm) | FIXED | `UNKNOWN` status never changes state or alerts |
| M2 | MEDIUM | `retries=0` | FIXED | default 1, configurable 0–5 |
| M3 | MEDIUM | Only authPriv + SHA | FIXED | all v3 levels; SHA–SHA512; AES/192/256; DES only with `allow_legacy_des` |
| M4 | MEDIUM | Targets polled sequentially | FIXED | bounded `asyncio.gather` |
| M5 | MEDIUM | No tests for probe/poll | FIXED | 98 offline tests (local); not in CI, see M6 |
| M6 | MEDIUM | CI did not run monitoring tests | **BLOCKED** | workflow edit refused for Claude's integration (403). Patch: [`CI-MONITORING-STEP.md`](CI-MONITORING-STEP.md); owner must apply |
| L1 | LOW | `tcp_port` mandatory for SNMP-only | FIXED | |
| L2 | LOW | Unused `seen` field | FIXED | |
| L3 | LOW | No fsync on state write | FIXED | |

## Round 2 — issues found in the round-1 engine and fixed

| ID | Severity | Finding | Status | Fix / evidence |
|---|---|---|---|---|
| R2-1 | HIGH | A hung check (e.g. a backend that never returns) could block the whole poll cycle indefinitely | FIXED | per-target `target_deadline_seconds`; result `UNKNOWN/DEADLINE_EXCEEDED`; `test_hanging_target_hits_deadline_without_blocking_others` |
| R2-2 | MEDIUM | Two monitor processes on the same state file could overwrite each other | FIXED | `fcntl.flock` on `<state>.lock`, exit code 3; `test_second_process_cannot_take_lock` |
| R2-3 | MEDIUM | Corrupt state file was silently replaced, losing evidence | FIXED | moved to `*.corrupt-<UTC>`, ERROR log; size limit 8 MiB |
| R2-4 | MEDIUM | Alert storm possible (flapping check → one webhook per transition) | FIXED | per-key cooldown 5 min, cap 30/hour |
| R2-5 | MEDIUM | Webhook could be any HTTPS host and could carry `user:pass@` | FIXED | optional `KSSH_MONITOR_WEBHOOK_HOSTS` allowlist; credentials-in-URL refused; URL registered for log scrubbing |
| R2-6 | LOW | Webhook payload built from free-form text | FIXED | JSON payload contains only whitelisted event fields |
| R2-7 | LOW | Log handler bound to the stderr object at import time | FIXED | handler follows the current `sys.stderr` |
| R2-8 | LOW | Target names could contain `/`, colliding with check keys | FIXED | names 1..64 chars, no `/`; ≤ 256 targets |

## Controls in place

* Mandatory allowlist (`allowed_networks`) at config load and in `SnmpClient`; alternate IP spellings do not bypass it (tested).
* No write path: no SNMP SET anywhere (tested).
* No SNMP version downgrade; legacy v1/v2c and DES need explicit per-device opt-in.
* Bounded walks (results, seconds, hard ceilings), loop detection, concurrency limits, per-target deadline.
* Secrets only via env-var names; values never logged, never in results; exception texts logged by type only.
* State file 0600, atomic + fsync, versioned, locked, corruption-safe.
* Admin-down ports are not outages; utilisation is not an outage; missing data is `UNAVAILABLE`/`UNKNOWN`, never invented.

## Residual risks / not verified

* PySNMP backend never executed (H2).
* DES is weak; required by the Real HD switch. Restrict UDP/161 to the management host.
* Hostname allowlist entries trust DNS; prefer IPs.
* Without `KSSH_MONITOR_WEBHOOK_HOSTS`, any HTTPS host is accepted as webhook.
* On non-POSIX systems the state lock is not available.
* Monitoring tests not in CI (M6).
