# Connector session
state: running
tunnel: funnel   (funnel = permanent URL / постоянен адрес)
url: https://ssh-connector.tail675f12.ts.net
claude_url: https://ssh-connector.tail675f12.ts.net/mcp   (header: Authorization = Bearer <SSH_CONNECTOR_TOKEN>)
chatgpt_url: https://ssh-connector.tail675f12.ts.net/<SSH_CONNECTOR_TOKEN>/mcp
public_check_without_token: HTTP 401 (401 = protected, OK)
servers: GitHub session profile (BGDB + demo)
started: 2026-10-27T23:49:22Z
ends: 2026-10-28T04:49:22Z
run: https://github.com/ykinfohome7/ssh-connector/actions/runs/40604493116

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
{"ts": "23:49:22", "method": "POST", "path": "/mcp", "headers": ["accept", "accept-encoding", "content-length", "host", "tailscale-headers-info", "tailscale-user-login", "tailscale-user-name", "tailscale-user-profile-pic", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "23:50:43", "method": "GET", "path": "/<\u0422\u041e\u041a\u0415\u041d>/mcp", "headers": ["accept", "accept-encoding", "accept-language", "host", "priority", "sec-fetch-dest", "sec-fetch-mode", "sec-fetch-site", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "23:50:43", "method": "GET", "path": "/favicon.ico", "headers": ["accept", "accept-encoding", "accept-language", "host", "priority", "referer", "sec-fetch-dest", "sec-fetch-mode", "sec-fetch-site", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "23:51:23", "method": "GET", "path": "/", "headers": ["accept", "accept-encoding", "accept-language", "host", "priority", "sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform", "sec-fetch-dest", "sec-fetch-mode", "sec-fetch-site", "sec-fetch-user", "tailscale-funnel-request", "upgrade-insecure-requests", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "23:51:43", "method": "GET", "path": "/<\u0422\u041e\u041a\u0415\u041d>/mcp", "headers": ["accept", "accept-encoding", "accept-language", "host", "priority", "sec-fetch-dest", "sec-fetch-mode", "sec-fetch-site", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "23:54:15", "method": "GET", "path": "/", "headers": ["accept", "accept-encoding", "accept-language", "cache-control", "host", "pragma", "priority", "sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform", "sec-fetch-dest", "sec-fetch-mode", "sec-fetch-site", "sec-fetch-user", "tailscale-funnel-request", "upgrade-insecure-requests", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "23:54:16", "method": "GET", "path": "/favicon.ico", "headers": ["accept", "accept-encoding", "accept-language", "cache-control", "host", "pragma", "priority", "referer", "sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform", "sec-fetch-dest", "sec-fetch-mode", "sec-fetch-site", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "23:54:16", "method": "GET", "path": "/", "headers": ["accept", "accept-encoding", "accept-language", "cache-control", "host", "pragma", "priority", "sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform", "sec-fetch-dest", "sec-fetch-mode", "sec-fetch-site", "sec-fetch-user", "tailscale-funnel-request", "upgrade-insecure-requests", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "23:54:16", "method": "GET", "path": "/favicon.ico", "headers": ["accept", "accept-encoding", "accept-language", "cache-control", "host", "pragma", "priority", "referer", "sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform", "sec-fetch-dest", "sec-fetch-mode", "sec-fetch-site", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "23:55:10", "method": "GET", "path": "/", "headers": ["accept", "accept-encoding", "accept-language", "host", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "23:55:10", "method": "GET", "path": "/favicon.ico", "headers": ["accept", "accept-encoding", "host", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
```
