# Security / code review — monitoring (PR #12 and follow-up)

- **Reviewer:** CLAUDE_CODE (agent_id `CLAUDE_CODE`)
- **Reviewed:** PR #12, branch `feature/health-monitor-mvp`, SHA `85bb7cb`
- **Fixes in:** branch `claude/monitor-hardening-snmp`
- **Scope:** offline review and offline tests only. No real device, no production KSSH, no deployment.

## Findings

| ID | Severity | Finding | Status | Fix / evidence |
|---|---|---|---|---|
| — | CRITICAL | none found | — | — |
| H1 | HIGH | HTTPS webhook followed redirects incl. HTTPS→HTTP | FIXED (`85bb7cb`) | `_NoRedirect` opener; `test_webhook_redirect_is_refused`, `test_redirect_not_followed_end_to_end` (real local 307 server, second server never hit) |
| H2 | HIGH | SNMPv3 SHA + DES with pysnmp 7 unverified; crypto dependency not declared | **BLOCKED / NOT TESTED** | PyPI returned HTTP 403 in the dev environment; policy not bypassed. `requirements-monitoring.txt` notes the possible `pycryptodomex` need |
| H3 | HIGH | All SNMP errors collapsed into one reason | FIXED | `errors.ErrorCode`, `snmp_client.classify_error_indication`; `test_probe_error_classification`, `test_indications` |
| M1 | MEDIUM | Missing pysnmp / secret counted as device DOWN (false alarm) | FIXED | `UNKNOWN` status never changes state or alerts; `test_missing_pysnmp_does_not_alert_down`, `test_unknown_never_changes_state` |
| M2 | MEDIUM | `retries=0` | FIXED | default `retries=1`, configurable 0–5 |
| M3 | MEDIUM | Only authPriv + SHA | FIXED | noAuthNoPriv / authNoPriv / authPriv; SHA, SHA224–512; AES, AES192, AES256; DES only with `allow_legacy_des` |
| M4 | MEDIUM | Targets polled sequentially | FIXED | bounded `asyncio.gather`; `test_poll_runs_targets_concurrently` |
| M5 | MEDIUM | No tests for probe/poll | FIXED | 69 offline tests (local); not yet in CI, see M6 |
| M6 | MEDIUM | CI did not run monitoring tests | **PREPARED, NOT APPLIED** | GitHub rejected the workflow change from Claude's integration (HTTP 403, no `workflows` permission). Ready patch: [`docs/CI-MONITORING-STEP.md`](CI-MONITORING-STEP.md) — the owner must apply it |
| L1 | LOW | `tcp_port` mandatory for SNMP-only | FIXED | `test_snmp_only_target_needs_no_tcp_port` |
| L2 | LOW | Unused `seen` field | FIXED | removed; legacy field dropped on load |
| L3 | LOW | No fsync on state write | FIXED | file + directory fsync; `test_state_file_private_and_complete` |

## New controls added

* **Mandatory allowlist** (`allowed_networks`) checked at config load and again in `SnmpClient`.
* **No write path:** no SET in client or backend; test asserts absence.
* **No downgrade:** v1/v2c require per-device `allow_legacy_snmp`; v3 failures stay v3 failures.
* **Bounded walks:** result and time limits with hard ceilings; loop detection on non-increasing OIDs.
* **Concurrency limits** per client and per poll.
* **Secrets:** only env-var names in config; values read at request time, min length 8 for v3 keys, registered for log scrubbing; exception texts are never logged (type only).

## Residual risks / not verified

* PySNMP backend never executed (H2). Its error-text mapping is based on documented messages.
* DES is cryptographically weak; required by the Real HD switch. Restrict UDP/161.
* Hostname allowlist entries trust DNS; prefer IP entries.
* Webhook destination is not allowlisted (only HTTPS + no redirect).
* SNMP module is not exposed as MCP tools yet (would change the 48-tool contract tested in `test_plugins.py`).
