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
{"ts": "00:00:50", "method": "GET", "path": "/actuator/env", "headers": ["accept-encoding", "host", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "00:00:51", "method": "GET", "path": "/trace.axd", "headers": ["accept-encoding", "host", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "00:00:52", "method": "GET", "path": "/@vite/env", "headers": ["accept-encoding", "host", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "00:00:54", "method": "GET", "path": "/.vscode/sftp.json", "headers": ["accept-encoding", "host", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "00:00:55", "method": "OPTIONS", "path": "/", "headers": ["accept-encoding", "host", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "00:00:56", "method": "GET", "path": "/", "headers": ["accept-encoding", "host", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "00:00:58", "method": "GET", "path": "/debug/default/view", "headers": ["accept-encoding", "host", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "00:01:07", "method": "GET", "path": "/.git/config", "headers": ["accept", "accept-encoding", "accept-language", "host", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "00:01:10", "method": "GET", "path": "/.git/config", "headers": ["accept", "accept-encoding", "accept-language", "host", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "00:02:00", "method": "GET", "path": "/", "headers": ["accept", "accept-encoding", "accept-language", "cache-control", "host", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "00:04:22", "method": "GET", "path": "/", "headers": ["accept", "accept-encoding", "accept-language", "host", "sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform", "sec-fetch-dest", "sec-fetch-mode", "sec-fetch-site", "sec-fetch-user", "sec-gpc", "tailscale-funnel-request", "upgrade-insecure-requests", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "00:04:24", "method": "GET", "path": "/", "headers": ["accept", "accept-encoding", "accept-language", "host", "referer", "tailscale-funnel-request", "upgrade-insecure-requests", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "00:04:25", "method": "GET", "path": "/favicon.ico", "headers": ["accept", "accept-encoding", "accept-language", "host", "referer", "sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform", "sec-fetch-dest", "sec-fetch-mode", "sec-fetch-site", "sec-fetch-user", "sec-gpc", "tailscale-funnel-request", "upgrade-insecure-requests", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "00:04:54", "method": "GET", "path": "/", "headers": ["accept", "accept-encoding", "accept-language", "host", "sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform", "sec-fetch-dest", "sec-fetch-mode", "sec-fetch-site", "sec-fetch-user", "sec-gpc", "tailscale-funnel-request", "upgrade-insecure-requests", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "00:04:56", "method": "GET", "path": "/favicon.ico", "headers": ["accept", "accept-encoding", "accept-language", "host", "referer", "sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform", "sec-fetch-dest", "sec-fetch-mode", "sec-fetch-site", "sec-fetch-user", "sec-gpc", "tailscale-funnel-request", "upgrade-insecure-requests", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
```
