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
{"ts": "01:50:05", "method": "GET", "path": "/css/support_parent.css", "headers": ["accept", "accept-encoding", "accept-language", "host", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "01:50:05", "method": "GET", "path": "/js/twint_ch.js", "headers": ["accept", "accept-encoding", "accept-language", "host", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "01:50:05", "method": "GET", "path": "/robots.txt", "headers": ["accept", "accept-encoding", "accept-language", "host", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "01:50:05", "method": "GET", "path": "/js/antibot-client.js", "headers": ["accept", "accept-encoding", "accept-language", "host", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "02:34:04", "method": "GET", "path": "/", "headers": ["accept", "baggage", "host", "range", "tailscale-funnel-request", "traceparent", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "02:46:44", "method": "GET", "path": "/", "headers": ["accept", "accept-encoding", "host", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "02:46:45", "method": "GET", "path": "/", "headers": ["accept", "accept-encoding", "host", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "03:00:56", "method": "GET", "path": "/", "headers": ["accept", "baggage", "host", "range", "tailscale-funnel-request", "traceparent", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "04:03:39", "method": "GET", "path": "/robots.txt", "headers": ["accept", "accept-encoding", "accept-language", "host", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "04:03:39", "method": "GET", "path": "/", "headers": ["accept", "accept-encoding", "accept-language", "host", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "04:47:38", "method": "GET", "path": "/", "headers": ["accept-charset", "accept-encoding", "host", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "04:51:05", "method": "POST", "path": "/j34kYv8W0irZJARSCLfT4W384GWadygIyb8Y5pfgUXjE7WIRbEyH137bR9USJejK/mcp", "headers": ["accept", "accept-encoding", "content-length", "content-type", "host", "mcp-method", "mcp-protocol-version", "tailscale-funnel-request", "traceparent", "tracestate", "user-agent", "x-datadog-parent-id", "x-datadog-sampling-priority", "x-datadog-tags", "x-datadog-trace-id", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "04:56:35", "method": "POST", "path": "/j34kYv8W0irZJARSCLfT4W384GWadygIyb8Y5pfgUXjE7WIRbEyH137bR9USJejK/mcp", "headers": ["accept", "accept-encoding", "content-length", "content-type", "host", "mcp-method", "mcp-protocol-version", "tailscale-funnel-request", "traceparent", "tracestate", "user-agent", "x-datadog-parent-id", "x-datadog-sampling-priority", "x-datadog-tags", "x-datadog-trace-id", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "04:56:48", "method": "GET", "path": "/.git/config", "headers": ["accept-charset", "accept-encoding", "host", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "04:58:32", "method": "POST", "path": "/j34kYv8W0irZJARSCLfT4W384GWadygIyb8Y5pfgUXjE7WIRbEyH137bR9USJejK/mcp", "headers": ["accept", "accept-encoding", "content-length", "content-type", "host", "mcp-method", "mcp-protocol-version", "tailscale-funnel-request", "traceparent", "tracestate", "user-agent", "x-datadog-parent-id", "x-datadog-sampling-priority", "x-datadog-tags", "x-datadog-trace-id", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
```
