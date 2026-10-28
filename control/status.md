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
{"ts": "00:16:40", "method": "GET", "path": "/app/.env", "headers": ["accept", "accept-encoding", "accept-language", "host", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "00:16:40", "method": "GET", "path": "/api/.env", "headers": ["accept", "accept-encoding", "accept-language", "host", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "00:16:40", "method": "GET", "path": "/backend/.env", "headers": ["accept", "accept-encoding", "accept-language", "host", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "00:16:41", "method": "GET", "path": "/config/.env", "headers": ["accept", "accept-encoding", "accept-language", "host", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "00:16:42", "method": "GET", "path": "/deploy/.env", "headers": ["accept", "accept-encoding", "accept-language", "host", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "00:16:43", "method": "GET", "path": "/.git/config.bak", "headers": ["accept", "accept-encoding", "accept-language", "host", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "00:16:44", "method": "GET", "path": "/.git/credentials.bak", "headers": ["accept", "accept-encoding", "accept-language", "host", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "00:16:44", "method": "GET", "path": "/.git/config~", "headers": ["accept", "accept-encoding", "accept-language", "host", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "00:16:44", "method": "GET", "path": "/.git/config.old", "headers": ["accept", "accept-encoding", "accept-language", "host", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "00:16:45", "method": "GET", "path": "/.git-credentials.bak", "headers": ["accept", "accept-encoding", "accept-language", "host", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "00:16:45", "method": "GET", "path": "/.gitconfig.bak", "headers": ["accept", "accept-encoding", "accept-language", "host", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "00:16:46", "method": "GET", "path": "/.netrc.bak", "headers": ["accept", "accept-encoding", "accept-language", "host", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "00:16:46", "method": "GET", "path": "/_netrc.bak", "headers": ["accept", "accept-encoding", "accept-language", "host", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "00:16:48", "method": "GET", "path": "/.npmrc.bak", "headers": ["accept", "accept-encoding", "accept-language", "host", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
{"ts": "00:16:49", "method": "GET", "path": "/.npmrc.old", "headers": ["accept", "accept-encoding", "accept-language", "host", "tailscale-funnel-request", "user-agent", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"], "cred_header": null, "cred_len": 0, "expected_len": 86, "result": "DENIED: no credential header"}
```
