# Connector session
state: running
tunnel: funnel   (funnel = permanent URL / постоянен адрес)
url: https://ssh-connector.tail675f12.ts.net
claude_url: https://ssh-connector.tail675f12.ts.net/mcp   (header: Authorization = Bearer <SSH_CONNECTOR_TOKEN>)
chatgpt_url: https://ssh-connector.tail675f12.ts.net/<SSH_CONNECTOR_TOKEN>/mcp
public_check_without_token: HTTP 401 (401 = protected, OK)
servers: GitHub session profile (BGDB + demo)
started: 2026-10-28T05:36:48Z
ends: 2026-10-28T10:36:48Z
run: https://github.com/ykinfohome7/ssh-connector/actions/runs/40638777106

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
{"ts": "05:36:48", "method": "POST", "path": "/mcp", "headers": ["accept", "accept-encoding", "content-length", "host", "tailscale-headers-info", "tailscale-user-login", "tailscale-user-name", "tailscale-user-profile-pic", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 64, "result": "DENIED: no credential header"}
{"ts": "05:37:24", "method": "POST", "path": "/<token>/mcp", "headers": ["accept", "accept-encoding", "content-length", "content-type", "host", "mcp-method", "mcp-name", "mcp-protocol-version", "mcp-session-id", "tailscale-funnel-request", "user-agent", "x-anthropic-client", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 64, "result": "ok (secret path)"}
{"ts": "05:37:28", "method": "GET", "path": "/", "headers": ["accept", "accept-encoding", "host", "tailscale-funnel-request", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 64, "result": "DENIED: no credential header"}
{"ts": "05:37:35", "method": "POST", "path": "/<token>/mcp", "headers": ["accept", "accept-encoding", "content-length", "content-type", "host", "mcp-method", "tailscale-funnel-request", "user-agent", "x-anthropic-client", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 64, "result": "ok (secret path)"}
{"ts": "05:37:41", "method": "POST", "path": "/<token>/mcp", "headers": ["accept", "accept-encoding", "content-length", "content-type", "host", "mcp-method", "mcp-protocol-version", "mcp-session-id", "tailscale-funnel-request", "user-agent", "x-anthropic-client", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 64, "result": "ok (secret path)"}
{"ts": "05:37:42", "method": "POST", "path": "/<token>/mcp", "headers": ["accept", "accept-encoding", "content-length", "content-type", "host", "mcp-method", "mcp-protocol-version", "mcp-session-id", "tailscale-funnel-request", "user-agent", "x-anthropic-client", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 64, "result": "ok (secret path)"}
{"ts": "05:37:42", "method": "POST", "path": "/<token>/mcp", "headers": ["accept", "accept-encoding", "content-length", "content-type", "host", "mcp-method", "mcp-protocol-version", "mcp-session-id", "tailscale-funnel-request", "user-agent", "x-anthropic-client", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 64, "result": "ok (secret path)"}
{"ts": "05:37:47", "method": "POST", "path": "/<token>/mcp", "headers": ["accept", "accept-encoding", "content-length", "content-type", "host", "mcp-method", "mcp-protocol-version", "tailscale-funnel-request", "user-agent", "x-anthropic-client", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 64, "result": "ok (secret path)"}
{"ts": "05:37:50", "method": "POST", "path": "/<token>/mcp", "headers": ["accept", "accept-encoding", "content-length", "content-type", "host", "mcp-method", "mcp-name", "mcp-protocol-version", "mcp-session-id", "tailscale-funnel-request", "user-agent", "x-anthropic-client", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 64, "result": "ok (secret path)"}
{"ts": "05:37:59", "method": "POST", "path": "/<token>/mcp", "headers": ["accept", "accept-encoding", "content-length", "content-type", "host", "mcp-method", "mcp-name", "mcp-protocol-version", "mcp-session-id", "tailscale-funnel-request", "user-agent", "x-anthropic-client", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 64, "result": "ok (secret path)"}
{"ts": "05:38:38", "method": "GET", "path": "/", "headers": ["accept", "accept-encoding", "host", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 64, "result": "DENIED: no credential header"}
{"ts": "05:39:45", "method": "GET", "path": "/wallet", "headers": ["accept", "accept-encoding", "cache-control", "host", "pragma", "priority", "sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform", "sec-fetch-dest", "sec-fetch-mode", "sec-fetch-site", "sec-fetch-user", "tailscale-funnel-request", "upgrade-insecure-requests", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 64, "result": "DENIED: no credential header"}
```
