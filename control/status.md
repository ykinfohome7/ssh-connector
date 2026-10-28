# Connector session
state: running
tunnel: funnel   (funnel = permanent URL / постоянен адрес)
url: https://ssh-connector.tail675f12.ts.net
claude_url: https://ssh-connector.tail675f12.ts.net/mcp   (header: Authorization = Bearer <SSH_CONNECTOR_TOKEN>)
chatgpt_url: https://ssh-connector.tail675f12.ts.net/<SSH_CONNECTOR_TOKEN>/mcp
public_check_without_token: HTTP 401 (401 = protected, OK)
servers: GitHub session profile (BGDB + demo)
started: 2026-10-28T00:42:20Z
ends: 2026-10-28T05:42:20Z
run: https://github.com/ykinfohome7/ssh-connector/actions/runs/40610215846

Stop: put 'stop' in control/session. Restart: put 'start' plus anything new on line 2.

## Tailscale diagnostics
```
cert: OK
tailscale: 1.104.2
funnel status:

# Funnel on:
#     - https://ssh-connector.tail675f12.ts.net

https://ssh-connector.tail675f12.ts.net (Funnel on)
|-- / proxy http://127.0.0.1:8765
```

## Last incoming requests (UTC, no secrets)
```
{"ts": "00:43:34", "method": "GET", "path": "/", "headers": ["accept", "accept-encoding", "accept-language", "host", "tailscale-funnel-request", "upgrade-insecure-requests", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "00:43:36", "method": "GET", "path": "/", "headers": ["accept", "accept-encoding", "cache-control", "host", "pragma", "priority", "sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform", "sec-fetch-dest", "sec-fetch-mode", "sec-fetch-site", "sec-fetch-user", "tailscale-funnel-request", "upgrade-insecure-requests", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "00:43:39", "method": "GET", "path": "/", "headers": ["accept", "accept-encoding", "cache-control", "host", "pragma", "priority", "sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform", "sec-fetch-dest", "sec-fetch-mode", "sec-fetch-site", "sec-fetch-user", "tailscale-funnel-request", "upgrade-insecure-requests", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "00:43:46", "method": "GET", "path": "/app", "headers": ["accept", "accept-encoding", "cache-control", "host", "pragma", "priority", "sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform", "sec-fetch-dest", "sec-fetch-mode", "sec-fetch-site", "sec-fetch-user", "tailscale-funnel-request", "upgrade-insecure-requests", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "00:43:53", "method": "GET", "path": "/wallet", "headers": ["accept", "accept-encoding", "cache-control", "host", "pragma", "priority", "sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform", "sec-fetch-dest", "sec-fetch-mode", "sec-fetch-site", "sec-fetch-user", "tailscale-funnel-request", "upgrade-insecure-requests", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "00:43:59", "method": "GET", "path": "/connect", "headers": ["accept", "accept-encoding", "cache-control", "host", "pragma", "priority", "sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform", "sec-fetch-dest", "sec-fetch-mode", "sec-fetch-site", "sec-fetch-user", "tailscale-funnel-request", "upgrade-insecure-requests", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "00:44:06", "method": "GET", "path": "/import", "headers": ["accept", "accept-encoding", "cache-control", "host", "pragma", "priority", "sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform", "sec-fetch-dest", "sec-fetch-mode", "sec-fetch-site", "sec-fetch-user", "tailscale-funnel-request", "upgrade-insecure-requests", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "00:47:15", "method": "GET", "path": "/robots.txt", "headers": ["accept", "accept-encoding", "host", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "00:47:15", "method": "GET", "path": "/", "headers": ["accept", "accept-encoding", "host", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "00:54:50", "method": "GET", "path": "/mcp", "headers": ["accept", "baggage", "host", "range", "tailscale-funnel-request", "traceparent", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "00:54:50", "method": "GET", "path": "/", "headers": ["accept", "baggage", "host", "range", "tailscale-funnel-request", "traceparent", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "00:55:57", "method": "GET", "path": "/.git/config", "headers": ["accept", "accept-encoding", "accept-language", "host", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "00:57:58", "method": "GET", "path": "/", "headers": ["accept-charset", "accept-encoding", "host", "referer", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "01:00:11", "method": "GET", "path": "/mcp", "headers": ["accept", "baggage", "host", "range", "tailscale-funnel-request", "traceparent", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "01:07:03", "method": "GET", "path": "/", "headers": ["accept", "baggage", "host", "range", "tailscale-funnel-request", "traceparent", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
```
