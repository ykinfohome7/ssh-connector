# Proxmox VE read-only HTTPS API for KSSH

Issue #13 · independent branch: codex/proxmox-readonly-api  
Standalone and opt-in: **NOT deployed; NOT tested against real devices**.

## Isolation from PR #12

The files monitoring/proxmox_api.py and monitoring/proxmox_format.py implement a real Proxmox VE HTTPS API client with no connection to Claude Code's PR #12 monitoring engine. Tests are in tests/test_proxmox_api.py and tests/test_proxmox_security.py. We did NOT edit monitoring/monitor.py, tests/test_monitoring_mvp.py or .github/workflows/test.yml. No existing KSSH tools were changed.

A successful TCP connection to port 8006 is NOT evidence of a healthy Proxmox API.

## Security model

- Require HTTPS origin with port **8006**, no credentials, path, query or fragment in base URL.
- Explicit exact hostname/IP allowlist, no wildcards or implicit targets. Invalid targets are rejected before network I/O.
- Verified TLS chain and hostname, with optional approved custom CA bundle. Never disable certificate checking. Connecting to an IP requires a matching certificate IP SAN.
- API token ID and secret are looked up by environment variable references at request time. No passwords, inline credentials or root password authentication. Use a separate least-privileged token with privilege separation.
- Only hard-coded GET endpoints are implemented. No POST, PUT, PATCH, DELETE, arbitrary URLs, redirects, inherited proxies, VM power actions or config changes.
- Configurable 0–60 second timeout (zero is rejected), 2 MiB response cap, no retries, no background polling.
- Structured JSON logs include UTC time, correlation ID, node, resource, status and error code only; no token, URL, raw HTTP response or raw exception.

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
| backup_tasks(node) | /api2/json/nodes/{node}/tasks?typefilter=vzdump&limit=100 | Visible Proxmox VE vzdump task outcomes |
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
