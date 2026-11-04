# CI step for monitoring tests — to be applied by the repository owner

Claude Code's GitHub integration is **not allowed to change files under `.github/workflows/`** (GitHub API: `403 Resource not accessible by integration`). This is a GitHub permission boundary; it was not worked around.

Apply this change to `.github/workflows/test.yml` (insert after the "Check Codespaces lifecycle tools" step) on the branch `claude/monitor-hardening-snmp` or on `main` after review:

```diff
       - name: Check Codespaces lifecycle tools (offline, no GitHub calls)
         run: python tests/test_codespaces.py
+      - name: Check read-only monitoring engine and SNMP module (offline, no devices)
+        id: monitoring
+        # Fake in-memory SNMP agent only. pysnmp is intentionally NOT installed
+        # here, so the real PySNMP backend is not exercised by this step.
+        run: python -m unittest -v tests/test_monitoring_mvp.py tests/test_monitoring_snmp.py
+      - name: Check Proxmox read-only API module when present (offline, Issue #13)
+        # Owned by CODEX (branch codex/proxmox-readonly-api); runs only once that file exists.
+        run: |
+          if [ -f tests/test_proxmox_api.py ]; then
+            python -m unittest -v tests/test_proxmox_api.py
+          else
+            echo "tests/test_proxmox_api.py not present on this ref; skipped."
+          fi
       - name: Check Claude Code and Codex plugins (v1.3.3, 48 tools)
```

The step needs only the Python standard library (the job already uses Python 3.12). It makes no network calls except to `127.0.0.1` (local test HTTP server for the webhook redirect test).

## На български

GitHub не позволява на интеграцията на Claude Code да променя `.github/workflows/` (грешка 403). Собственикът на хранилището трябва да добави горната стъпка ръчно (през уеб интерфейса на GitHub: файл `.github/workflows/test.yml` → Edit → вмъкване след стъпката „Check Codespaces lifecycle tools“). Без тази стъпка CI **не изпълнява** monitoring тестовете.
