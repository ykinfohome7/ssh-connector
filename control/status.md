# Connector session
state: running
url: https://notified-violation-taxi-unsubscribe.trycloudflare.com
claude_url: https://notified-violation-taxi-unsubscribe.trycloudflare.com/mcp   (header: Authorization = Bearer <SSH_CONNECTOR_TOKEN>)
chatgpt_url: https://notified-violation-taxi-unsubscribe.trycloudflare.com/<SSH_CONNECTOR_TOKEN>/mcp
public_check_without_token: HTTP 401 (401 = protected, OK)
servers: public test server (tests/servers.test.yaml)
started: 2026-10-27T17:10:48Z
ends: 2026-10-27T22:10:48Z
run: https://github.com/ykinfohome7/ssh-connector/actions/runs/40547792135

Stop: put 'stop' in control/session. Restart: put 'start' plus anything new on line 2.

## Last incoming requests (UTC, no secrets)
```
{"ts": "17:10:48", "method": "POST", "path": "/mcp", "headers": ["accept", "accept-encoding", "cdn-loop", "cf-connecting-ip", "cf-ew-via", "cf-ipcountry", "cf-ray", "cf-visitor", "cf-warp-tag-id", "cf-worker", "connection", "content-length", "host", "user-agent", "x-forwarded-for", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
```
