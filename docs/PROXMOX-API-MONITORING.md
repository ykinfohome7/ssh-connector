# Proxmox VE read-only HTTPS API for KSSH

Issue #13 · independent branch: codex/proxmox-readonly-api  
Standalone and opt-in: **mock-tested only**; **NOT deployed; NOT tested against real devices**.

## Isolation from PR #12

The files monitoring/proxmox_api.py and monitoring/proxmox_format.py implement a real Proxmox VE HTTPS API client with no connection to Claude Code's PR #12 monitoring engine. Tests are in tests/test_proxmox_api.py and tests/test_proxmox_security.py. We did NOT edit monitoring/monitor.py, tests/test_monitoring_mvp.py or .github/workflows/test.yml. No existing KSSH tools were changed.

A successful TCP connection to port 8006 is NOT evidence of a healthy Proxmox API.

## Security model

- Require HTTPS origin with port **8006**, no credentials, path, query or fragment in base URL.
- Explicit exact hostname/IP allowlist (port is pinned to 8006), no wildcards or implicit targets. Invalid targets are rejected before network I/O.
- Verified TLS chain and hostname, with optional approved custom CA bundle. Never disable certificate checking. Connecting to an IP requires a matching certificate IP SAN.
- API token ID and secret are looked up by environment variable references at request time. No passwords, inline credentials or root password authentication. Use a separate least-privileged token with privilege separation.
- Only hard-coded GET endpoints are implemented. No POST, PUT, PATCH, DELETE, arbitrary URLs, redirects, VM power actions or config changes.
- Configurable 0–60 second timeout (zero is rejected), configurable response cap up to 2 MiB, no retries, no background polling.
- Structured JSON logs include UTC time, correlation ID, resource, status and error code only (node names are omitted from logs); no token, URL, raw HTTP response or raw exception.

For an authorized future installation, grant only the Proxmox audit/view privileges required by the chosen endpoints. Common privileges to review include Sys.Audit, VM.Audit and Datastore.Audit on appropriately scoped ACL paths. Do not use administrator or VM.PowerMgmt roles. A 403 becomes PERMISSION_DENIED, never an empty or stopped VM list.

## API methods

| Method | HTTPS GET path | What is reported |
| --- | --- | --- |
| version() | /api2/json/version | API version/release |
| discover_nodes() | /api2/json/nodes | Dynamic node names/status |
| node_status(node) | /api2/json/nodes/{node}/status | CPU, uptime, RAM, swap, optional network |
| storage(node) | /api2/json/nodes/{node}/storage | Capacity, optional 90% warning, inactive storage |
| qemu(node) | /api2/json/nodes/{node}/qemu | Dynamically discovered QEMU status |
| lxc(node) | /api2/json/nodes/{node}/lxc | Dynamically discovered LXC status |
| guest_status(node, kind, vmid) | /api2/json/nodes/{node}/{qemu or lxc}/{vmid}/status/current | Current guest status and available CPU/RAM/network/disk counters |
| backup_jobs() | /api2/json/cluster/backup | Visible configured PVE backup schedules (not execution history) |
| backup_tasks(node) | /api2/json/nodes/{node}/tasks?typefilter=vzdump&limit=100&source=all | Visible Proxmox VE vzdump task outcomes |
| snapshot(node) | Six fixed GET calls above | Aggregated adapter output |

Optional netin/netout are emitted only when the official API response includes numeric values. Missing values are omitted; do not invent zeroes. Empty QEMU/LXC lists are valid only after a successful API response.

**Backups:** This endpoint is **PVE task history**, not Proxmox Backup Server (PBS) health. It does not verify actual backup files, backup completeness, PBS datastore state or backup scheduling. Results are limited to 100 task records and may omit older activity. Missing permissions mean UNAVAILABLE or PERMISSION_DENIED, not a successful backup. In-progress tasks without endtime are not considered failed.

## Setup example (not to be executed on production)

Use a unique hostname with a trusted certificate; example.invalid has no real target.

~~~python
from monitoring.proxmox_api import ProxmoxReadOnlyClient

client = ProxmoxReadOnlyClient(
    "https://lab-pve.example.invalid:8006",
    allowed_hosts=["lab-pve.example.invalid"],
    token_id_env="KSSH_PROXMOX_TOKEN_ID",
    token_secret_env="KSSH_PROXMOX_TOKEN_SECRET",
    timeout=5.0,
    # ca_bundle="/secure/path/to/approved-CA.pem"
)
# No I/O occurs until the caller explicitly invokes a read method.
# result = client.snapshot("lab-node")
~~~

Set both named environment variables with an authorized secrets manager. Never commit or paste actual token values. No default endpoints, account secrets, or production IPs are stored in this client.

## Result contract and failure semantics

Each method returns **ok**, **status**, **node**, **resource**, **timestamp_utc**, **data**, **error_code**, **source**, **capabilities**. UTC timestamps end in Z and source is proxmox-ve-api. A successful call has ok=true and error_code=null; missing capabilities are false or absent. A failed call has ok=false, data=null and an explicit error:

API_UNREACHABLE, TLS_ERROR, AUTH_FAILED, PERMISSION_DENIED, RESOURCE_NOT_FOUND, MALFORMED_RESPONSE or UNAVAILABLE.

Snapshot status is OK when all six reads succeed, DEGRADED when only some succeed, and UNAVAILABLE when none succeeds. For DEGRADED, successful data remains under data.resources and failures are named in data.errors. **Never convert unavailable data into STOPPED or zero resource usage.**

Illustrative simulated JSON output, not derived from pve1/pve2:

~~~json
{
  "ok": true,
  "status": "DEGRADED",
  "node": "lab-node",
  "resource": "snapshot",
  "timestamp_utc": "2026-11-04T20:00:00Z",
  "data": {
    "resources": {
      "api_version": {"version": "8.4"},
      "node_status": {"cpu": 0.12, "memory": {"total": 1000, "used": 450}},
      "storage": null,
      "qemu": [{"vmid": 501, "name": "demo", "status": "running"}],
      "lxc": [],
      "backup_tasks": {"tasks": [], "failures": [], "total_returned": 0}
    },
    "errors": {"storage": "PERMISSION_DENIED"}
  },
  "error_code": null,
  "source": "proxmox-ve-api",
  "capabilities": {
    "api_version": true, "node_status": true, "storage": false,
    "qemu": true, "lxc": true, "backup_tasks": true,
    "network_metrics": false, "pbs_health": false
  }
}
~~~

## Adapter proposal to the PR #12 polling engine

The new module does not edit or import the PR #12 code.

1. Configure the exact approved API host, trusted CA, read-only token env references, node scope and timeout independently of SNMP/SSH.
2. During a future authorized poll, call snapshot(node); use discover_nodes() only when explicitly authorized. Preserve all fields and resource-specific errors.
3. Feed only successful, real VM/CT statuses into monitoring transitions. Do not assume VMID ranges or consider access denial a device DOWN event.
4. Apply existing debouncing/recovery/alert policies in the PR #12 engine in a separately reviewed integration PR. Treat DEGRADED as partial evidence, not a failed TCP probe.
5. Never claim PBS health from this API and do not assume per-interface network metrics exist.

## Reproducible offline tests

From the repository root on Python 3.10+ (stdlib only):

~~~bash
python3 -m unittest discover -s tests -p 'test_proxmox_*.py' -v
~~~

Tests mock the HTTP opener and cover valid JSON, errors, timeouts, 401/403/404, TLS failures, malformed responses, missing VM list, running/stopped VM, storage warnings, failed backup task, absent network metrics, target allowlisting, URL validation, redirect refusal, GET-only surface and redacted logs. **Published tests are not by themselves a PASS:** report the actual result only when the exact code has been executed. PR #12 retains responsibility for modifying the shared test.yml workflow.

## Накратко на български

Самостоятелен read-only клиент за Proxmox VE HTTPS API. Няма връзка с продукционните pve1/pve2, няма root пароли, промени по VM или deployment. Изисква валиден TLS сертификат, предварително разрешен host и отделен API токен с минимални права. Връща само действително достъпните през API данни, различава забранени права от спрян сървър и не представя PVE backup task history за PBS health.

## Hardened validation and adapter semantics

Operator configuration (not free-form tool arguments) owns base_url, allowed_hosts,
optional allowed_origins, CA path, timeout and credential references. Every accepted
host is pinned to HTTPS port 8006, so allowed_hosts denotes exact origins at that
port; optional allowed_origins adds an explicit canonical HTTPS-origin constraint.
No DNS/IP discovery or wildcard matching is performed. DNS integrity and the trusted
CA remain deployment prerequisites; the managed environment's configured HTTPS proxy
is retained so network policy and injected authentication are not bypassed.

Present numeric metrics must be finite, nonnegative numbers (not booleans or strings).
Malformed supplied fields fail the sample; absent metrics remain absent with false
capability flags. Per-guest flags distinguish missing status/network counters from
stopped/zero. Per-storage capacity flags avoid inferring capacity for every storage
from one available record. Backup tasks with no explicit type are not inferred to
be vzdump; missing endtime or status means outcome unavailable, never failed.

Individual successful reads have status UP: the API request succeeded, not a claim
that every physical node or guest is running. Failed reads have status UNKNOWN.
This collector never emits physical-node DOWN. An engine may establish DOWN only
from separately authorized, explicit evidence and its reviewed debounce policy.
Snapshot retains OK/DEGRADED/UNAVAILABLE as aggregate collection states; map failed
collection states to UNKNOWN in the future engine adapter. Never map TLS, credentials,
permissions, missing data, or API connection failure to physical-node DOWN.

The tasks query explicitly requests source=all (visible active and archived tasks),
with a fixed first-page limit of 100. There is no automatic pagination in this client.
Even a short/empty page is not proof of full history: permissions, retention, task
rotation and concurrent changes limit visibility. history_complete and
backup_recency_assurance are always false; history_may_be_truncated is always true.
The API describes PVE vzdump tasks only, not PBS health or backup-file integrity.
The adapter must preserve per-resource errors and capabilities; snapshot calls are
sequential, not atomic, and can take up to six configured request timeouts.

Minimum privileges must be checked against the deployed PVE API schema:
Sys.Audit on the intended /nodes scope, VM.Audit on intended /vms, and
Datastore.Audit on intended /storage are typical audit requirements. Token privilege
separation intersects token ACLs with the user's ACLs. Task visibility may remain
restricted to the token's visible tasks even with audit permissions. Do not grant
power/configuration privileges to broaden monitoring visibility.

Exact primary offline command from the repository root:

```bash
python3 tests/test_proxmox_api.py
```

Full Proxmox/security suite and proposed future CI integration command:

```bash
python3 -m unittest discover -s tests -p 'test_proxmox_*.py' -v
```

Redirect tests run urllib's actual dispatch against a synthetic HTTPS transport
for 301/302/303/307/308, including same-origin and downgrade destinations. They
assert exactly one authorized request and no forwarding to a second target.
No sockets or real-device TLS handshakes are used. Production TLS, permissions,
engine integration and real-device behavior remain **NOT TESTED**.

БГ: неизвестни данни не означават нула, STOPPED или физически DOWN. Само offline
проверки; няма разрешение за връзки към реални устройства или deployment.

## Current guest details and configured backup jobs

Use qemu(node) or lxc(node) for dynamic inventory before selecting a VMID for
`guest_status(node, kind, vmid)`. Selectors accept only kind `qemu`/`lxc` and an
integer VMID in 100..999999999 (booleans and strings are rejected). There is no
power-action endpoint. Current status reads expose status, uptime, CPU, mem,
maxmem, and optional netin/netout/diskread/diskwrite only when the API supplies
them. Missing status is unknown, never assumed stopped. The caller controls how
many discovered guests to poll; no automatic fan-out or unbounded task creation.
VM.Audit and the effective token/user ACLs constrain visible guests.

`backup_jobs()` separately queries `/cluster/backup` and emits only job id, node,
storage, schedule and enabled fields with per-job capability flags. It excludes
mail addresses, notes and other arbitrary configuration. Availability depends on
the deployed PVE schema and the token's audit rights (typically Sys.Audit at the
cluster scope `/` for reading this configuration). A narrow token may receive 403;
do not broaden it automatically. A configured/enabled job does not prove that it
ran, succeeded, or produced a recent usable backup. Conversely, an empty visible
job list does not prove the absence of backups. Jobs are deliberately not added
to the six-call node snapshot because cluster configuration is a separate scope.
The 2 MiB body limit also applies to this list. No job mutation endpoints exist.

## Contract review against Claude PR #14 (no integration performed)

Read-only review refs at the time of this change:

- PR #12: `85bb7cbe863013b9606f7155ccbea8fae39ce762`.
- PR #14: `282550196b0a51476668434a3aafe0e26d661708`.

PR #14's `.github/workflows/test.yml` does **not** invoke its 69 monitoring tests.
Its prepared `docs/CI-MONITORING-STEP.md` remains the owner's integration task.
This branch does not change that workflow or duplicate that fix. The existing
separate `proxmox-api-offline` workflow only covers the Proxmox suite; its presence
is not evidence that any Actions run passed. Local tests and CI results must be
reported separately and matched to a full commit SHA.

PR #14's engine evaluates `checks[name].status` and translates UNKNOWN to
`ok=None` for the debounce state machine. Passing snapshot's aggregate OK or
DEGRADED directly would instead be treated as a failure. The future adapter must
explicitly translate these collection states, retain the raw sample and its
resource_capabilities, and avoid calling status_for(AUTH_FAILED) for API errors:
that helper currently maps auth failures to DOWN, which does not establish a
powered-off physical node. Example **proposal only**, not installed into engine:

```python
import asyncio

async def proposed_proxmox_probe(client, node):
    sample = await asyncio.to_thread(client.snapshot, node)
    collected = sample['ok'] and sample['status'] == 'OK'
    return {
        'ok': collected,
        'status': 'UP' if collected else 'UNKNOWN',
        'error_code': None if collected else (sample['error_code'] or 'UNAVAILABLE'),
        'detail': 'API collection complete' if collected else 'API collection incomplete',
        'sample': sample,
    }
```

Run this behind the engine's existing concurrency bound; own worker cancellation
and shutdown explicitly because cancellation of to_thread does not stop blocking
urllib I/O. Socket timeout is per blocking operation, not a whole-snapshot deadline.
Use independent named checks for CPU/RAM/storage thresholds and selected critical
guests only after a reviewed operator policy; an API-collection UP does not assert
all guests are running. Preserve unknown metrics so they cannot reset alert state
or create false recovery events. The snapshot now preserves each sub-sample's
capabilities in `data.resource_capabilities`, including unavailable metrics.

БГ: CI пропускът за 69-те теста е документиран, без промяна на чуждия workflow.
API грешки остават UNKNOWN. Новите GET методи не стартират/спират VM и не променят
backup jobs. Реална интеграция с engine-а остава отделна задача.

Schema references checked during implementation (public upstream source only):
[PVE JSONSchema: pve-vmid](https://github.com/proxmox/pve-common/blob/master/src/PVE/JSONSchema.pm)
sets VMID bounds 100..999999999;
[PVE API2 Backup](https://github.com/proxmox/pve-manager/blob/master/PVE/API2/Backup.pm)
defines the GET schedule list with Sys.Audit at `/`. Verify the deployed release's
schema independently before a separately authorized real-device test.
