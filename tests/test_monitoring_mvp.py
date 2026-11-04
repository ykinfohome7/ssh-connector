"""Offline tests for the read-only KSSH monitoring MVP."""
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "monitoring" / "monitor.py"
spec = importlib.util.spec_from_file_location("kssh_health_monitor", SCRIPT)
monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor)


class MonitorTests(unittest.TestCase):
    def test_consecutive_failures_and_recovery(self):
        state = {}
        f = lambda ok: monitor.update_state(state, "pve1/tcp", ok, 3, 2)
        self.assertIsNone(f(False))
        self.assertIsNone(f(False))
        self.assertEqual(f(False), "DOWN")
        self.assertIsNone(f(False))
        self.assertIsNone(f(True))
        self.assertEqual(f(True), "RECOVERED")
        self.assertIsNone(f(True))

    def test_transient_failure_does_not_alert(self):
        state = {}
        self.assertIsNone(monitor.update_state(state, "realhd/snmp", False, 3, 2))
        self.assertIsNone(monitor.update_state(state, "realhd/snmp", True, 3, 2))
        self.assertIsNone(monitor.update_state(state, "realhd/snmp", False, 3, 2))
        self.assertEqual(state["realhd/snmp"]["healthy"], True)

    def test_example_config_and_secrets_not_embedded(self):
        path = SCRIPT.with_name("targets.example.json")
        config = monitor.load_config(path)
        self.assertEqual([t["name"] for t in config["targets"]],
                         ["realhd-switch", "pve1", "pve2"])
        self.assertEqual(config["targets"][0]["snmp"]["version"], "3")
        for word in ("auth_pass", "priv_pass", "community"):
            self.assertNotIn('"'+word+'":', path.read_text(encoding="utf-8"))

    def test_reject_invalid_version_and_duplicate_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            base = {"targets": [{"name": "x", "host": "127.0.0.1", "tcp_port": 8006}]}
            path.write_text(json.dumps(base))
            self.assertEqual(monitor.load_config(path)["targets"][0]["name"], "x")
            base["targets"][0]["snmp"] = {"version": "4"}
            path.write_text(json.dumps(base))
            with self.assertRaises(ValueError):
                monitor.load_config(path)
            base["targets"] = [
                {"name": "x", "host": "127.0.0.1", "tcp_port": 8006},
                {"name": "x", "host": "127.0.0.2", "tcp_port": 8006},
            ]
            path.write_text(json.dumps(base))
            with self.assertRaises(ValueError):
                monitor.load_config(path)

    def test_state_file_not_world_readable(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            monitor.save_state(path, {"x": {"healthy": False}})
            self.assertEqual(json.loads(path.read_text())["x"]["healthy"], False)
            if os.name == "posix":
                self.assertEqual(path.stat().st_mode & 0o077, 0)

    def test_http_webhook_rejected(self):
        with patch.dict(os.environ, {"KSSH_MONITOR_WEBHOOK": "http://example.invalid"}):
            with patch.object(monitor.urllib.request, "urlopen") as opener:
                monitor.notify("test status")
                opener.assert_not_called()


if __name__ == "__main__":
    unittest.main()
