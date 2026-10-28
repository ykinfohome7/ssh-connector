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
{"ts": "06:51:47", "method": "POST", "path": "/<token>/mcp", "headers": ["accept", "accept-encoding", "content-length", "content-type", "host", "mcp-method", "mcp-name", "mcp-protocol-version", "mcp-session-id", "tailscale-funnel-request", "user-agent", "x-anthropic-client", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 64, "result": "ok (secret path)"}
{"ts": "06:52:23", "method": "POST", "path": "/<token>/mcp", "headers": ["accept", "accept-encoding", "content-length", "content-type", "host", "mcp-method", "mcp-name", "mcp-protocol-version", "mcp-session-id", "tailscale-funnel-request", "user-agent", "x-anthropic-client", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 64, "result": "ok (secret path)"}
{"ts": "06:52:27", "method": "POST", "path": "/<token>/mcp", "headers": ["accept", "accept-encoding", "content-length", "content-type", "host", "mcp-method", "mcp-name", "mcp-protocol-version", "mcp-session-id", "tailscale-funnel-request", "user-agent", "x-anthropic-client", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 64, "result": "ok (secret path)"}
{"ts": "06:52:33", "method": "POST", "path": "/<token>/mcp", "headers": ["accept", "accept-encoding", "content-length", "content-type", "host", "mcp-method", "mcp-name", "mcp-protocol-version", "mcp-session-id", "tailscale-funnel-request", "user-agent", "x-anthropic-client", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 64, "result": "ok (secret path)"}
{"ts": "06:52:40", "method": "POST", "path": "/<token>/mcp", "headers": ["accept", "accept-encoding", "content-length", "content-type", "host", "mcp-method", "mcp-name", "mcp-protocol-version", "mcp-session-id", "tailscale-funnel-request", "user-agent", "x-anthropic-client", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 64, "result": "ok (secret path)"}
{"ts": "06:52:47", "method": "POST", "path": "/<token>/mcp", "headers": ["accept", "accept-encoding", "content-length", "content-type", "host", "mcp-method", "mcp-name", "mcp-protocol-version", "mcp-session-id", "tailscale-funnel-request", "user-agent", "x-anthropic-client", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 64, "result": "ok (secret path)"}
{"ts": "07:00:18", "method": "POST", "path": "/<token>/mcp", "headers": ["accept", "accept-encoding", "content-length", "content-type", "host", "mcp-method", "mcp-protocol-version", "tailscale-funnel-request", "user-agent", "x-anthropic-client", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 64, "result": "ok (secret path)"}
{"ts": "07:00:18", "method": "POST", "path": "/<token>/mcp", "headers": ["accept", "accept-encoding", "content-length", "content-type", "host", "mcp-method", "tailscale-funnel-request", "user-agent", "x-anthropic-client", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 64, "result": "ok (secret path)"}
{"ts": "07:00:19", "method": "POST", "path": "/<token>/mcp", "headers": ["accept", "accept-encoding", "content-length", "content-type", "host", "mcp-method", "mcp-protocol-version", "mcp-session-id", "tailscale-funnel-request", "user-agent", "x-anthropic-client", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 64, "result": "ok (secret path)"}
{"ts": "07:00:19", "method": "POST", "path": "/<token>/mcp", "headers": ["accept", "accept-encoding", "content-length", "content-type", "host", "mcp-method", "mcp-protocol-version", "mcp-session-id", "tailscale-funnel-request", "user-agent", "x-anthropic-client", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 64, "result": "ok (secret path)"}
{"ts": "07:12:03", "method": "POST", "path": "/<token>/mcp", "headers": ["accept", "accept-encoding", "content-length", "content-type", "host", "mcp-method", "mcp-protocol-version", "tailscale-funnel-request", "user-agent", "x-anthropic-client", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 64, "result": "ok (secret path)"}
{"ts": "07:12:05", "method": "POST", "path": "/<token>/mcp", "headers": ["accept", "accept-encoding", "content-length", "content-type", "host", "mcp-method", "mcp-name", "mcp-protocol-version", "mcp-session-id", "tailscale-funnel-request", "user-agent", "x-anthropic-client", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 64, "result": "ok (secret path)"}
{"ts": "07:12:16", "method": "POST", "path": "/<token>/mcp", "headers": ["accept", "accept-encoding", "content-length", "content-type", "host", "mcp-method", "mcp-name", "mcp-protocol-version", "mcp-session-id", "tailscale-funnel-request", "user-agent", "x-anthropic-client", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 64, "result": "ok (secret path)"}
{"ts": "07:12:22", "method": "POST", "path": "/<token>/mcp", "headers": ["accept", "accept-encoding", "content-length", "content-type", "host", "mcp-method", "mcp-name", "mcp-protocol-version", "mcp-session-id", "tailscale-funnel-request", "user-agent", "x-anthropic-client", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 64, "result": "ok (secret path)"}
{"ts": "07:12:26", "method": "POST", "path": "/<token>/mcp", "headers": ["accept", "accept-encoding", "content-length", "content-type", "host", "mcp-method", "mcp-name", "mcp-protocol-version", "mcp-session-id", "tailscale-funnel-request", "user-agent", "x-anthropic-client", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 64, "result": "ok (secret path)"}
```
