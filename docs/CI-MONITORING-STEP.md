# CI step for monitoring tests — to be applied by the repository owner

Claude Code's GitHub integration is **not allowed to change files under `.github/workflows/`** (GitHub API: `403 Resource not accessible by integration`). This is a GitHub permission boundary; it was not worked around.

Apply this change to `.github/workflows/test.yml` (insert after the "Check Codespaces lifecycle tools" step) on the branch `claude/monitor-hardening-snmp` or on `main` after review:

Status 2026-11-05: the owner authorized this change, but the push was refused again
(`POST /git/trees: 403 Resource not accessible by integration`). The owner has to apply it.

```diff
--- a/.github/workflows/test.yml
+++ b/.github/workflows/test.yml
@@ -46,7 +46,12 @@ jobs:
         run: python tests/test_profiles.py
       - name: Check Codespaces lifecycle tools (offline, no GitHub calls)
         run: python tests/test_codespaces.py
-      - name: Check Claude Code and Codex plugins (v1.3.3, 48 tools)
+      - name: Check read-only monitoring, SNMP, Tailscale endpoint and RDP modules (offline, no devices)
+        id: monitoring
+        # Fake in-memory SNMP agent and fake local RDP listener only; pysnmp is NOT installed here,
+        # so the real PySNMP backend is not exercised by this step.
+        run: python -m unittest -v tests/test_monitoring_mvp.py tests/test_monitoring_snmp.py tests/test_monitoring_engine.py tests/test_plugin_snmp.py tests/test_tailscale_endpoint.py tests/test_rdp_tools.py tests/test_snippet_library.py
+      - name: Check Claude Code and Codex plugins (v1.4.1, 60 tools, isolated install)
         id: plugins
         run: python tests/test_plugins.py
       - name: Check public log redaction and schema
```

The step needs Python 3.12, PyYAML (installed by the job from `requirements.txt`) and the `openssl` CLI (present on `ubuntu-latest`, used for a throw-away RDP test certificate). It makes no network calls except to `127.0.0.1` (local webhook and fake RDP test servers).

## На български

GitHub не позволява на интеграцията на Claude Code да променя `.github/workflows/` (грешка 403). Собственикът на хранилището трябва да добави горната стъпка ръчно (през уеб интерфейса на GitHub: файл `.github/workflows/test.yml` → Edit → вмъкване след стъпката „Check Codespaces lifecycle tools“). Без тази стъпка CI **не изпълнява** monitoring тестовете.
