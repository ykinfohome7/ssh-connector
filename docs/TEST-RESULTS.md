# Test results — monitoring

Local ≠ CI. Each entry states where it ran. Nothing below was run against a real device.

## Run L5 — RDP / Windows tools (CLAUDE_CODE)

| Field | Value |
|---|---|
| Time (UTC) | 2026-11-05T05:35Z |
| Command A (local, stdlib + PyYAML + openssl CLI) | `python3 -W error::ResourceWarning -m unittest tests/test_monitoring_mvp.py tests/test_monitoring_snmp.py tests/test_monitoring_engine.py tests/test_plugin_snmp.py tests/test_tailscale_endpoint.py tests/test_rdp_tools.py` |
| Result A | **Ran 163 — OK (skipped=1)**; `tests/test_rdp_tools.py` alone: 22 OK |
| Command B (local, asyncssh stub + mcp-2 shim, not committed) | `tests/test_plugins.py` (+ isolated installed-plugin test) and the old mock tests |
| Result B | all PASSED; `plugin tests PASSED (version 1.4.0, commands 60)`; installed plugin: 60 unique tools; `rdp_check` on a closed port → `DOWN/UNREACHABLE`, unknown target → `UNKNOWN/CONFIG_ERROR`, `windows_health` on unknown profile → `CONFIG_ERROR` |
| CI | see PR #14 report for the run on the final SHA |

`tests/test_rdp_tools.py` (22): request bytes; response parsing (selected / failure / no negotiation / not RDP); NLA required, NLA optional + legacy accepted; not RDP (HTTP answer); timeout; closed port; unknown target; TLS with untrusted cert reported (no data from unverified handshake); TLS verified with pinned `ca_file` + expiry warning; check through `via` forwarder (closed afterwards); audit entry; config validation (9 invalid cases) and example configs; tunnel + `.rdp` file (no password), remote-backend note, errors without leaked text; fixed read-only PowerShell; health parsing + warnings; not Windows / timeout / garbage / unknown profile; `quser` parsing incl. disconnected session; source has no `CERT_NONE` / disabled hostname check.

Not executed: any real Windows host, RDP server or OpenSSH on Windows.

## Run L4 — plugin 1.4.0 + Tailscale endpoint (CLAUDE_CODE)

| Field | Value |
|---|---|
| Time (UTC) | 2026-11-04T22:15Z |
| Command A (local, stdlib) | `python3 -W error::ResourceWarning -m unittest tests/test_monitoring_mvp.py tests/test_monitoring_snmp.py tests/test_monitoring_engine.py tests/test_plugin_snmp.py tests/test_tailscale_endpoint.py` |
| Result A | **Ran 141 — OK (skipped=1)**; `tests/test_tailscale_endpoint.py` alone: 28 OK |
| Command B (local, asyncssh stub + mcp 2.x shim, not committed) | `tests/test_v13_session_tailscale_mock.py`, `test_sudo_password_mock.py`, `test_v13_mock.py`, `test_codespaces.py`, `test_profiles.py`, `test_plugins.py` |
| Result B | all PASSED; `plugin tests PASSED (version 1.4.0, commands 56)` |
| **CI** (real `mcp<2`, `asyncssh`), SHA `371d643` | [run 41922900652](https://github.com/ykinfohome7/ssh-connector/actions/runs/41922900652/job/126899678499) — **success**. The step `python tests/test_plugins.py` now also runs the isolated installed-plugin test |

Isolated installed-plugin test (`tests/test_installed_plugin.py`): only `plugins/ssh-connector` copied to a temporary plugin cache; real launcher `sh bin/run.sh` (venv pre-seeded, no pip); cwd outside the repo; no `PYTHONPATH` (harness run with `python -I`). Measured locally:

```
launcher:     tools 56 (unique), snmp_health without pysnmp -> UNKNOWN / DEPENDENCY_MISSING,
              tailscale calls only after tailscale_status: status --json, serve status --json, version
              exposure: serve (tailnet only), reachability not verified
fake backend: tools 56, snmp_health UP, snmp_get UP, snmp_walk UP, raw IP refused (CONFIG_ERROR),
              backend created only after the first call_tool
```

Tailscale scenarios (mock CLI/HTTP), all passing: not installed; daemon not running; NeedsLogin / NeedsMachineAuth; stopped; valid DNSName; missing DNSName (never taken from HostName); invalid DNSName; invalid JSON (status and serve); timeout (status, serve, HTTP probe); Serve without Funnel; Funnel configured but not verified; nothing configured; configured address without check (no network call); health check failing (0/404/502), OK (401), unprotected (200); address from file / unreadable file; non-HTTPS rejected; configured vs Tailscale mismatch; stdio vs HTTP templates; token-bearing URL reduced to host; user-info removed; redaction of token, secret path, bearer, `tskey-…`; only read-only CLI commands; no `serve` call when not running.

Not executed: real Tailscale, Serve, Funnel or HTTP backend; Codex CLI plugin update; Claude Code `plugin update` against the real marketplace (`claude plugin validate` passed for the plugin and the marketplace manifest).

## Run L3 — local, CLAUDE_CODE (SNMP MCP tools)

| Field | Value |
|---|---|
| Time (UTC) | 2026-11-04T21:45Z |
| Environment | Python 3.13.18; `pysnmp` and `asyncssh` not installable (PyPI 403); installed `mcp` is 2.x while the plugin pins `mcp<2` |
| Command A | `python3 -W error::ResourceWarning -m unittest tests/test_monitoring_mvp.py tests/test_monitoring_snmp.py tests/test_monitoring_engine.py tests/test_plugin_snmp.py` |
| Result A | **Ran 113 — OK (skipped=1)**: the skipped test imports `server.py`, which needs `mcp<2` + `asyncssh` |
| Command B | same + `PYTHONPATH=<local stubs>` (minimal stand-ins for `asyncssh` and `mcp.server.fastmcp`, **not committed**) |
| Result B | **Ran 113 — OK**; `tests/test_plugins.py` → `plugin tests PASSED (version 1.3.3, commands 56)` |

Result B uses stubs, so it proves registration logic (56 tools = 56 HELP entries) but **not** the real MCP runtime. The real check is `tests/test_plugins.py` in GitHub Actions, which installs `mcp<2` and `asyncssh` and now asserts 56.

New `tests/test_plugin_snmp.py` (15 tests): config errors are `UNKNOWN`, only configured device names (a raw IP is refused), missing secret, health/device info/GET/GETNEXT/GETBULK (repetitions capped)/bounded WALK, invalid OIDs and injection-like input refused, interface filter, rates from two samples (1 Gbit/s, 10 %, 2 errors/s), device errors `DOWN`, secrets never echoed, values capped at 1024 chars, no write operation in code, vendored library in sync, example configs valid, server registration with BG/EN help.

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
* **The monitoring tests are not part of CI (M6 BLOCKED).** The workflow change was refused for Claude's GitHub integration (HTTP 403). Ready step (now listing all four monitoring/SNMP test files): [`docs/CI-MONITORING-STEP.md`](CI-MONITORING-STEP.md).

## Not executed

| Test | Status | Reason |
|---|---|---|
| PySNMP backend (any version, SHA/DES/AES) | **BLOCKED / NOT TESTED** | PyPI HTTP 403 in the dev environment |
| Real HD switch 192.168.30.10 | PENDING_EXPLICIT_APPROVAL | production device |
| pve1 / pve2 | PENDING_EXPLICIT_APPROVAL | production hosts; Proxmox API module is CODEX's (#13) |
| docker-compose test agent (snmpd) | NOT DONE | in-process fake agent used instead |
| Windows (non-POSIX) state lock | NOT TESTED | `fcntl` unavailable there; lock is skipped by design |
