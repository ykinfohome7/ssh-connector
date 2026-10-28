"""Ensure public CI diagnostic artifacts cannot include tokens/URLs/SSH output."""
import datetime as dt
import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.ci_summary import make_report, render_markdown


def main():
    marker = "SUPER_SECRET_TEST_TOKEN_1234567890"
    with tempfile.TemporaryDirectory() as directory:
        path = pathlib.Path(directory) / "integration.json"
        path.write_text(json.dumps({
            "schema_version": 1,
            "checks": [
                {"test": "http mode", "seconds": 3.22, "passed": True,
                 "token": marker, "url": "https://example.com/" + marker,
                 "stdout": marker},
                {"test": "server installer + public tunnel", "seconds": 8,
                 "passed": False, "exception": marker},
                {"test": marker, "seconds": 1, "passed": True},
            ],
        }))
        report = make_report(
            path,
            {"profiles": "success", "plugins": "failure",
             "integration": "failure; " + marker},
            now=dt.datetime(2026, 10, 27, tzinfo=dt.timezone.utc),
        )
        exported = json.dumps(report) + render_markdown(report)
        assert marker not in exported, "Secret leaked into public report!"
        assert "example.com" not in exported
        assert report["outcomes"]["integration"] == "unknown"
        assert len(report["checks"]) == 2
        assert report["checks"][0]["seconds"] == 3.2
        assert report["checks"][1]["passed"] is False
        assert report["checks"][0]["test"] == "http mode"
        assert report["schema_version"] == 1
    print("Safe CI report redaction/allowlist tests PASSED")


if __name__ == "__main__":
    main()
