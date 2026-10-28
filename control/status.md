# Connector session
state: running
tunnel: cloudflare   (Funnel name is tied to this temporary runner)
url: https://programs-commander-phi-row.trycloudflare.com
claude_url: https://programs-commander-phi-row.trycloudflare.com/mcp   (header: Authorization = Bearer <SSH_CONNECTOR_TOKEN>)
chatgpt_url: https://programs-commander-phi-row.trycloudflare.com/<SSH_CONNECTOR_TOKEN>/mcp
public_check_without_token: HTTP 401 (401 = protected, TLS verified)
url_lifetime: temporary GitHub Actions runner; DNS name may change after restart
servers: GitHub session profile (BGDB + demo)
started: 2026-10-28T13:06:41Z
ends: 2026-10-28T18:06:41Z
run: https://github.com/ykinfohome7/ssh-connector/actions/runs/40692535025

Stop: put 'stop' in control/session. Restart: put 'start' plus anything new on line 2.

## Tailscale diagnostics
```
tailscale_dns_name: ssh-connector.tail675f12.ts.net
https_probe: 401 (TLS verified, unauthenticated access blocked)
```

## Last incoming requests (UTC, no secrets)
```
{"ts": "13:06:41", "method": "POST", "path": "/mcp", "headers": ["accept", "accept-encoding", "cdn-loop", "cf-connecting-ip", "cf-ew-via", "cf-ipcountry", "cf-ray", "cf-visitor", "cf-warp-tag-id", "cf-worker", "connection", "content-length", "host", "user-agent", "x-forwarded-for", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 64, "result": "DENIED: no credential header"}
{"ts": "14:16:41", "method": "GET", "path": "/", "headers": ["accept", "accept-encoding", "baggage", "cdn-loop", "cf-connecting-ip", "cf-ew-via", "cf-ipcountry", "cf-ray", "cf-visitor", "cf-warp-tag-id", "cf-worker", "connection", "host", "range", "traceparent", "user-agent", "x-forwarded-for", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 64, "result": "DENIED: no credential header"}
{"ts": "14:16:41", "method": "GET", "path": "/", "headers": ["accept", "accept-encoding", "baggage", "cdn-loop", "cf-connecting-ip", "cf-ew-via", "cf-ipcountry", "cf-ray", "cf-visitor", "cf-warp-tag-id", "cf-worker", "connection", "host", "range", "traceparent", "user-agent", "x-forwarded-for", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 64, "result": "DENIED: no credential header"}
{"ts": "14:16:41", "method": "GET", "path": "/mcp", "headers": ["accept", "accept-encoding", "baggage", "cdn-loop", "cf-connecting-ip", "cf-ew-via", "cf-ipcountry", "cf-ray", "cf-visitor", "cf-warp-tag-id", "cf-worker", "connection", "host", "range", "traceparent", "user-agent", "x-forwarded-for", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 64, "result": "DENIED: no credential header"}
```
