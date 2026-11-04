# Proxmox offline test evidence

agent_id=CODEX

Recorded UTC: 2026-11-04T21:19:46.937023+00:00

Branch: `codex/proxmox-readonly-api`

Tested implementation commit: `55c0e132ee14ebd634fa0f8f571ad7b010df17f9`

Python: **3.12.14**. Working directory: `/workspace/ssh-connector`.

This evidence was captured after committing the implementation. A following
documentation-only commit adds this report; it does not change the tested code.

| Exact command | Result |
| --- | --- |
| `python3 tests/test_proxmox_api.py` | 41 tests, OK |
| `python3 -m unittest discover -s tests -p 'test_proxmox_*.py' -v` | 71 tests, OK |
| `.venv/bin/python tests/test_cloudns_ddns.py` | Exit 0; passed (no unittest count emitted) |
| `.venv/bin/python tests/test_profiles.py` | Exit 0; passed (no unittest count emitted) |
| `.venv/bin/python tests/test_codespaces.py` | Exit 0; passed (no unittest count emitted) |
| `.venv/bin/python tests/test_plugins.py` | Exit 0; passed (no unittest count emitted) |
| `.venv/bin/python tests/test_ci_summary.py` | Exit 0; passed (no unittest count emitted) |
| `.venv/bin/python tests/test_sudo_password_mock.py` | Exit 0; passed (no unittest count emitted) |
| `.venv/bin/python tests/test_v13_mock.py` | Exit 0; passed (no unittest count emitted) |
| `.venv/bin/python tests/test_v13_session_tailscale_mock.py` | Exit 0; passed (no unittest count emitted) |
| `bash -n scripts/gh-session.sh` | Exit 0; passed (no unittest count emitted) |
| `bash -n scripts/cloudns-ddns.sh` | Exit 0; passed (no unittest count emitted) |
| `bash -n scripts/setup-bgssh-domain.sh` | Exit 0; passed (no unittest count emitted) |
| `bash -n install-server.sh` | Exit 0; passed (no unittest count emitted) |
| `.venv/bin/python -m pip check` | Exit 0; passed (no unittest count emitted) |
| `git diff --check` | Exit 0; passed (no unittest count emitted) |

## What the run demonstrates

All 71 full-suite tests completed: 41 HTTP/API tests, 13 security tests, 8 pure
normalizer tests and 9 async adapter tests. The direct API command runs its 41-test
subset; these are not 112 distinct tests. No tests were skipped in this suite.

The eight existing offline scripts each completed successfully. They do not
produce a uniform aggregate assertion count, so none is invented.

The new cases cover huge numbers and pure-normalizer overflow; duplicate keys,
NaN/Infinity and deep JSON; contradictory storage capacity/boolean flags; unknown
backup outcomes versus explicit failures/warnings; credential echo; fixed guest/job
paths; all-failed per-resource errors; UP/UNKNOWN translation and cancellation.
The existing real urllib redirect-dispatch test still checks all 301/302/303/307/308
scenarios without credential forwarding to a second target.

## Execution limits and unrun checks

- **Mock-tested only.** HTTP responses and redirect transport are synthetic.
- API/adapter tests install a socket-connect guard. Async tests need event-loop
  local wakeups, not connections to PVE. In the command sandbox, full-suite attempts
  stalled at thread-to-loop wakeups and were terminated; those attempts are not PASS.
  The complete recorded suite ran in the approved executor context outside that sandbox.
- `tests/test_connect.py`: **NOT RUN**; it includes remote SSH and installer/service actions.
- Real-device TLS handshakes, deployed API schema/ACLs, engine registration, production
  devices, backup-file integrity/recency and PBS health: **NOT TESTED / NOT INTEGRATED**.
- No production credentials, device connections, deployment or merge to main.

## Review and CI separation

- PR #12 inspected at `85bb7cbe863013b9606f7155ccbea8fae39ce762`.
- PR #14 inspected at `4722bec732b30fd00ca458cd6d9a6469670a89b1`.
- Its shared `test.yml` still does not run the monitoring suites. Its current report
  claims 98 local tests, following a 69-test baseline; these are Claude-reported
  results, not tests executed by this task. No shared CI or Claude files were changed.
- GitHub Actions for this implementation SHA: **NOT VERIFIED at report creation**.
  The existing separate Proxmox workflow is not evidence of a passed run.
- An older Issue #13 comment reports CI for `9ab86a9`; it does not validate this SHA.

## Publication blocker and next steps

Native Git fetch/push works. `gh api` returns Forbidden. A credential-free HTTPS
probe also failed at proxy CONNECT with 403, before GitHub authentication. The
current runtime allowlist omits `api.github.com`. A draft adds exactly that domain
while preserving presets and existing rules; saving the draft does not apply or
publish it. Review/save the environment settings and publish the configuration,
allow propagation, then retry the API before deciding whether credentials need changes.

Until that succeeds, Issue/PR comment publication and PR-body editing remain blocked.
Ready-to-post reports are retained outside the checkout. Future engine integration
must be reviewed separately and preserve UNKNOWN for API/TLS/auth/permission errors.

БГ: резултатите са локални и offline, върху точния implementation SHA. Няма
твърдение за нов CI PASS, production тест или свързан monitoring engine.
