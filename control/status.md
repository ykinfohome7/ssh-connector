# Connector session
state: running
tunnel: funnel   (funnel = permanent URL / постоянен адрес)
url: https://ssh-connector.tail675f12.ts.net
claude_url: https://ssh-connector.tail675f12.ts.net/mcp   (header: Authorization = Bearer <SSH_CONNECTOR_TOKEN>)
chatgpt_url: https://ssh-connector.tail675f12.ts.net/<SSH_CONNECTOR_TOKEN>/mcp
public_check_without_token: HTTP 401 (401 = protected, OK)
servers: GitHub session profile (BGDB + demo)
started: 2026-10-28T05:01:41Z
ends: 2026-10-28T10:01:41Z
run: https://github.com/ykinfohome7/ssh-connector/actions/runs/40635348507

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
{"ts": "05:04:38", "method": "POST", "path": "/<token>/mcp", "headers": ["accept", "accept-encoding", "content-length", "content-type", "host", "mcp-protocol-version", "mcp-session-id", "tailscale-funnel-request", "traceparent", "tracestate", "user-agent", "x-datadog-parent-id", "x-datadog-sampling-priority", "x-datadog-tags", "x-datadog-trace-id", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto", "x-openai-session", "x-openai-subject"], "cred_header": null, "cred_len": 0, "expected_len": 64, "result": "ok (secret path)"}
{"ts": "05:04:38", "method": "POST", "path": "/<token>/mcp", "headers": ["accept", "accept-encoding", "content-length", "content-type", "host", "mcp-protocol-version", "mcp-session-id", "tailscale-funnel-request", "traceparent", "tracestate", "user-agent", "x-datadog-parent-id", "x-datadog-sampling-priority", "x-datadog-tags", "x-datadog-trace-id", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto", "x-openai-session", "x-openai-subject"], "cred_header": null, "cred_len": 0, "expected_len": 64, "result": "ok (secret path)"}
{"ts": "05:05:06", "method": "POST", "path": "/<token>/mcp", "headers": ["accept", "accept-encoding", "content-length", "content-type", "host", "tailscale-funnel-request", "traceparent", "tracestate", "user-agent", "x-datadog-parent-id", "x-datadog-sampling-priority", "x-datadog-tags", "x-datadog-trace-id", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto", "x-openai-session", "x-openai-subject"], "cred_header": null, "cred_len": 0, "expected_len": 64, "result": "ok (secret path)"}
{"ts": "05:05:06", "method": "POST", "path": "/<token>/mcp", "headers": ["accept", "accept-encoding", "content-length", "content-type", "host", "mcp-protocol-version", "mcp-session-id", "tailscale-funnel-request", "traceparent", "tracestate", "user-agent", "x-datadog-parent-id", "x-datadog-sampling-priority", "x-datadog-tags", "x-datadog-trace-id", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto", "x-openai-session", "x-openai-subject"], "cred_header": null, "cred_len": 0, "expected_len": 64, "result": "ok (secret path)"}
{"ts": "05:05:06", "method": "POST", "path": "/<token>/mcp", "headers": ["accept", "accept-encoding", "content-length", "content-type", "host", "mcp-protocol-version", "mcp-session-id", "tailscale-funnel-request", "traceparent", "tracestate", "user-agent", "x-datadog-parent-id", "x-datadog-sampling-priority", "x-datadog-tags", "x-datadog-trace-id", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto", "x-openai-session", "x-openai-subject"], "cred_header": null, "cred_len": 0, "expected_len": 64, "result": "ok (secret path)"}
{"ts": "05:05:07", "method": "GET", "path": "/<token>/mcp", "headers": ["accept", "accept-encoding", "cache-control", "content-type", "host", "mcp-protocol-version", "mcp-session-id", "tailscale-funnel-request", "traceparent", "tracestate", "user-agent", "x-datadog-parent-id", "x-datadog-sampling-priority", "x-datadog-tags", "x-datadog-trace-id", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto", "x-openai-session", "x-openai-subject"], "cred_header": null, "cred_len": 0, "expected_len": 64, "result": "ok (secret path)"}
{"ts": "05:05:36", "method": "POST", "path": "/<token>/mcp", "headers": ["accept", "accept-encoding", "content-length", "content-type", "host", "tailscale-funnel-request", "traceparent", "tracestate", "user-agent", "x-datadog-parent-id", "x-datadog-sampling-priority", "x-datadog-tags", "x-datadog-trace-id", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto", "x-openai-session", "x-openai-subject"], "cred_header": null, "cred_len": 0, "expected_len": 64, "result": "ok (secret path)"}
{"ts": "05:05:36", "method": "GET", "path": "/<token>/mcp", "headers": ["accept", "accept-encoding", "cache-control", "content-type", "host", "mcp-protocol-version", "mcp-session-id", "tailscale-funnel-request", "traceparent", "tracestate", "user-agent", "x-datadog-parent-id", "x-datadog-sampling-priority", "x-datadog-tags", "x-datadog-trace-id", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto", "x-openai-session", "x-openai-subject"], "cred_header": null, "cred_len": 0, "expected_len": 64, "result": "ok (secret path)"}
{"ts": "05:05:36", "method": "POST", "path": "/<token>/mcp", "headers": ["accept", "accept-encoding", "content-length", "content-type", "host", "mcp-protocol-version", "mcp-session-id", "tailscale-funnel-request", "traceparent", "tracestate", "user-agent", "x-datadog-parent-id", "x-datadog-sampling-priority", "x-datadog-tags", "x-datadog-trace-id", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto", "x-openai-session", "x-openai-subject"], "cred_header": null, "cred_len": 0, "expected_len": 64, "result": "ok (secret path)"}
{"ts": "05:05:37", "method": "POST", "path": "/<token>/mcp", "headers": ["accept", "accept-encoding", "content-length", "content-type", "host", "mcp-protocol-version", "mcp-session-id", "tailscale-funnel-request", "traceparent", "tracestate", "user-agent", "x-datadog-parent-id", "x-datadog-sampling-priority", "x-datadog-tags", "x-datadog-trace-id", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto", "x-openai-session", "x-openai-subject"], "cred_header": null, "cred_len": 0, "expected_len": 64, "result": "ok (secret path)"}
{"ts": "05:07:06", "method": "GET", "path": "/", "headers": ["accept", "baggage", "host", "range", "tailscale-funnel-request", "traceparent", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 64, "result": "DENIED: no credential header"}
{"ts": "05:10:50", "method": "POST", "path": "/<token>/mcp", "headers": ["accept", "accept-encoding", "content-length", "content-type", "host", "tailscale-funnel-request", "traceparent", "tracestate", "user-agent", "x-datadog-parent-id", "x-datadog-sampling-priority", "x-datadog-tags", "x-datadog-trace-id", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto", "x-openai-session", "x-openai-subject"], "cred_header": null, "cred_len": 0, "expected_len": 64, "result": "ok (secret path)"}
{"ts": "05:10:51", "method": "GET", "path": "/<token>/mcp", "headers": ["accept", "accept-encoding", "cache-control", "content-type", "host", "mcp-protocol-version", "mcp-session-id", "tailscale-funnel-request", "traceparent", "tracestate", "user-agent", "x-datadog-parent-id", "x-datadog-sampling-priority", "x-datadog-tags", "x-datadog-trace-id", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto", "x-openai-session", "x-openai-subject"], "cred_header": null, "cred_len": 0, "expected_len": 64, "result": "ok (secret path)"}
{"ts": "05:10:51", "method": "POST", "path": "/<token>/mcp", "headers": ["accept", "accept-encoding", "content-length", "content-type", "host", "mcp-protocol-version", "mcp-session-id", "tailscale-funnel-request", "traceparent", "tracestate", "user-agent", "x-datadog-parent-id", "x-datadog-sampling-priority", "x-datadog-tags", "x-datadog-trace-id", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto", "x-openai-session", "x-openai-subject"], "cred_header": null, "cred_len": 0, "expected_len": 64, "result": "ok (secret path)"}
{"ts": "05:10:51", "method": "POST", "path": "/<token>/mcp", "headers": ["accept", "accept-encoding", "content-length", "content-type", "host", "mcp-protocol-version", "mcp-session-id", "tailscale-funnel-request", "traceparent", "tracestate", "user-agent", "x-datadog-parent-id", "x-datadog-sampling-priority", "x-datadog-tags", "x-datadog-trace-id", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto", "x-openai-session", "x-openai-subject"], "cred_header": null, "cred_len": 0, "expected_len": 64, "result": "ok (secret path)"}
```
