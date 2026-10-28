#!/usr/bin/env python3
"""Publish only allowlisted CI metadata. NEVER publish raw SSH/MCP test logs.

This repository is public: job summaries and artifacts are readable by others.
No IPs, hostnames, command output, bearer tokens, URLs or exception text.
"""
import datetime as dt
import json
import os
from pathlib import Path

SAFE_TEST_NAMES = (
    "run_command rebex",
    "failover",
    "run_on_group demo",
    "run_snippet",
    "sftp_list /",
    "sftp_read readme",
    "sftp_manage stat",
    "shell_open",
    "shell_send pwd",
    "shell_close",
    "history",
    "list_servers",
    "http mode",
    "plugin launcher",
    "server installer + public tunnel",
)
SAFE_OUTCOMES = {"success", "failure", "cancelled", "skipped", "unknown"}


def normalize_outcome(value):
    return value if value in SAFE_OUTCOMES else "unknown"


def clean_check(item):
    """Refuse to echo arbitrary fields (especially raw SSH output and URLs)."""
    if not isinstance(item, dict) or item.get("test") not in SAFE_TEST_NAMES:
        return None
    raw_seconds = item.get("seconds")
    seconds = round(float(raw_seconds), 1) if isinstance(raw_seconds, (int, float)) and not isinstance(raw_seconds, bool) and 0 <= raw_seconds <= 1800 else None
    passed = item.get("passed")
    if not isinstance(passed, bool):
        return None
    return {"test": item["test"], "passed": passed, "seconds": seconds}


def make_report(report_path, outcomes, now=None):
    """Pure, offline-safe report builder, suitable for unit tests."""
    checks = []
    if report_path.is_file():
        try:
            source = json.loads(report_path.read_text(encoding="utf-8"))
            if isinstance(source, dict) and source.get("schema_version") == 1 and isinstance(source.get("checks"), list):
                seen = set()
                for check in source["checks"]:
                    c = clean_check(check)
                    if c and c["test"] not in seen:
                        checks.append(c)
                        seen.add(c["test"])
        except (OSError, ValueError, UnicodeError):
            pass  # Never echo a parser exception or untrusted file contents.
    outcomes = {key: normalize_outcome(outcomes.get(key, "unknown")) for key in ("profiles", "plugins", "integration")}
    return {
        "schema_version": 1,
        "suite": "ssh-connector",
        "timestamp_utc": (now or dt.datetime.now(dt.timezone.utc)).isoformat(),
        "outcomes": outcomes,
        "checks": checks,
        "result_available": bool(checks),
        "redaction": "Only static test names, outcomes, durations. No raw logs or credentials.",
    }


def render_markdown(report):
    lines = [
        "## SSH Connector — безопасен CI отчет",
        "",
        "Този отчет съдържа само имена на проверки, резултати и продължителност.",
        "GitHub хранилището е публично; не се записват токени, команди, IP адреси и URL.",
        "",
        "| Проверка | Резултат |",
        "|---|---|",
    ]
    for label, key in (("SSH профили", "profiles"), ("Claude/Codex плъгини", "plugins"), ("SSH/MCP интеграция", "integration")):
        lines.append(f"| {label} | {report['outcomes'][key]} |")
    lines.extend(["", "| Интеграционен тест | Резултат | Секунди |", "|---|---|---:|"])
    for check in report["checks"]:
        value = f"{check['seconds']:.1f}" if check["seconds"] is not None else "—"
        lines.append(f"| {check['test']} | {'PASS' if check['passed'] else 'FAIL'} | {value} |")
    if not report["checks"]:
        lines.append("| Няма подробности (тестът може да е прекъснал рано) | — | — |")
    lines.append("")
    return "\n".join(lines)


def main():
    root = Path(os.environ.get("SSH_CI_REPORT_DIR", os.environ.get("RUNNER_TEMP", "/tmp") + "/ssh-ci-report"))
    root.mkdir(parents=True, exist_ok=True)
    integration_path = Path(os.environ.get("SSH_CONNECTOR_CI_REPORT", str(root / "integration.json")))
    outcomes = {
        "profiles": os.environ.get("SSH_CI_PROFILE_OUTCOME", "unknown"),
        "plugins": os.environ.get("SSH_CI_PLUGIN_OUTCOME", "unknown"),
        "integration": os.environ.get("SSH_CI_INTEGRATION_OUTCOME", "unknown"),
    }
    report = make_report(integration_path, outcomes)
    (root / "summary.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    markdown = render_markdown(report)
    (root / "summary.md").write_text(markdown, encoding="utf-8")
    gh_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if gh_summary:
        with open(gh_summary, "a", encoding="utf-8") as output:
            output.write(markdown + "\n")
    print("Sanitized CI report created: summary.json + summary.md; raw logs omitted.")


if __name__ == "__main__":
    main()
