# Connector session
state: running
url: https://pediatric-caught-marine-references.trycloudflare.com
claude_url: https://pediatric-caught-marine-references.trycloudflare.com/mcp   (header: Authorization = Bearer <SSH_CONNECTOR_TOKEN>)
chatgpt_url: https://pediatric-caught-marine-references.trycloudflare.com/<SSH_CONNECTOR_TOKEN>/mcp
public_check_without_token: HTTP 401 (401 = protected, OK)
servers: GitHub session profile (BGDB + demo)
started: 2026-10-27T21:56:50Z
ends: 2026-10-28T02:56:50Z
run: https://github.com/ykinfohome7/ssh-connector/actions/runs/40590776315

Stop: put 'stop' in control/session. Restart: put 'start' plus anything new on line 2.

## Last incoming requests (UTC, no secrets)
```
{"ts": "21:56:50", "method": "POST", "path": "/mcp", "headers": ["accept", "accept-encoding", "cdn-loop", "cf-connecting-ip", "cf-ew-via", "cf-ipcountry", "cf-ray", "cf-visitor", "cf-warp-tag-id", "cf-worker", "connection", "content-length", "host", "user-agent", "x-forwarded-for", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
```
