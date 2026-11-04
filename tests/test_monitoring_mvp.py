"""Offline tests for the read-only KSSH monitoring engine (state, config, webhook)."""
import asyncio
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from monitoring import monitor  # noqa: E402
from monitoring.errors import ErrorCode, MonitorError  # noqa: E402
from monitoring.snmp_client import NO_SUCH  # noqa: E402

SCRIPT = ROOT / "monitoring" / "monitor.py"


def write_cfg(tmp, cfg):
    path = Path(tmp) / "config.json"
    path.write_text(json.dumps(cfg))
    return path


BASE = {"allowed_networks": ["127.0.0.0/8"],
        "targets": [{"name": "x", "host": "127.0.0.1", "tcp_port": 8006}]}


class FakeBackend:
    def __init__(self, values=None, error=None):
        self.values = values or {}
        self.error = error
        self.calls = []

    async def get(self, oids):
        self.calls.append(("get", oids))
        if self.error:
            raise self.error
        return [(o, self.values.get(o, NO_SUCH)) for o in oids]

    async def getnext(self, oids):
        raise AssertionError("not expected")

    async def getbulk(self, n, m, oids):
        raise AssertionError("not expected")


class StateTests(unittest.TestCase):
    def test_consecutive_failures_and_recovery(self):
        state = {}
        f = lambda ok: monitor.update_state(state, "pve1/tcp", ok, 3, 2)  # noqa: E731
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

    def test_unknown_never_changes_state(self):  # M1
        state = {}
        for _ in range(10):
            self.assertIsNone(monitor.update_state(state, "sw/snmp", None, 3, 2))
        self.assertEqual(state["sw/snmp"], {"healthy": True, "pending": 0})
        monitor.update_state(state, "sw/snmp", False, 3, 2)
        monitor.update_state(state, "sw/snmp", None, 3, 2)
        self.assertEqual(state["sw/snmp"]["pending"], 1)

    def test_legacy_seen_field_dropped(self):  # L2
        state = {"a": {"healthy": True, "pending": 0, "seen": True}}
        monitor.update_state(state, "a", True, 3, 2)
        self.assertNotIn("seen", state["a"])

    def test_state_file_private_and_complete(self):  # L3
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sub" / "state.json"
            with patch.object(monitor.os, "fsync", wraps=os.fsync) as fsync:
                monitor.save_state(path, {"x": {"healthy": False}})
                self.assertGreaterEqual(fsync.call_count, 1)
            self.assertEqual(json.loads(path.read_text())["x"]["healthy"], False)
            self.assertFalse(path.with_suffix(".tmp").exists())
            if os.name == "posix":
                self.assertEqual(path.stat().st_mode & 0o077, 0)


class ConfigTests(unittest.TestCase):
    def test_example_config_and_secrets_not_embedded(self):
        path = SCRIPT.with_name("targets.example.json")
        config = monitor.load_config(path)
        self.assertEqual([t["name"] for t in config["targets"]], ["realhd-switch", "pve1", "pve2"])
        snmp = config["targets"][0]["snmp"]
        self.assertEqual(snmp["version"], "3")
        self.assertTrue(snmp["allow_legacy_des"])
        text = path.read_text(encoding="utf-8")
        for word in ("auth_pass", "priv_pass", '"community"', "authKey", "privKey"):
            self.assertNotIn(word, text)

    def test_reject_invalid_version_and_duplicate_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(monitor.load_config(write_cfg(tmp, BASE))["targets"][0]["name"], "x")
            bad = json.loads(json.dumps(BASE))
            bad["targets"][0]["snmp"] = {"version": "4"}
            with self.assertRaises(ValueError):
                monitor.load_config(write_cfg(tmp, bad))
            dup = dict(BASE, targets=[BASE["targets"][0], dict(BASE["targets"][0], host="127.0.0.2")])
            with self.assertRaises(ValueError):
                monitor.load_config(write_cfg(tmp, dup))

    def test_allowlist_required_and_enforced(self):
        with tempfile.TemporaryDirectory() as tmp:
            no_list = {"targets": BASE["targets"]}
            with self.assertRaisesRegex(ValueError, "allowed_networks"):
                monitor.load_config(write_cfg(tmp, no_list))
            outside = dict(BASE, allowed_networks=["10.0.0.0/8"])
            with self.assertRaisesRegex(ValueError, "not in allowed_networks"):
                monitor.load_config(write_cfg(tmp, outside))

    def test_snmp_only_target_needs_no_tcp_port(self):  # L1
        cfg = {"allowed_networks": ["127.0.0.1"], "targets": [{
            "name": "sw", "host": "127.0.0.1",
            "snmp": {"version": "3", "user": "u", "security_level": "noAuthNoPriv"}}]}
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(len(monitor.load_config(write_cfg(tmp, cfg))["targets"]), 1)
            cfg["targets"][0].pop("snmp")
            with self.assertRaisesRegex(ValueError, "tcp_port and/or snmp"):
                monitor.load_config(write_cfg(tmp, cfg))

    def test_des_and_legacy_versions_need_explicit_opt_in(self):
        base_v3 = {"version": "3", "user": "u", "security_level": "authPriv",
                   "auth_env": "A_ENV", "priv_env": "P_ENV", "priv_protocol": "DES"}
        cases = [
            (base_v3, "allow_legacy_des"),
            ({"version": "2c", "community_env": "C_ENV"}, "allow_legacy_snmp"),
            ({"version": "1", "community_env": "C_ENV"}, "allow_legacy_snmp"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            for snmp, msg in cases:
                cfg = {"allowed_networks": ["127.0.0.1"],
                       "targets": [{"name": "s", "host": "127.0.0.1", "snmp": snmp}]}
                with self.assertRaisesRegex(ValueError, msg):
                    monitor.load_config(write_cfg(tmp, cfg))


class ProbeAndPollTests(unittest.TestCase):
    SNMP = {"version": "3", "user": "u", "security_level": "authPriv",
            "auth_env": "T_AUTH", "priv_env": "T_PRIV", "priv_protocol": "AES"}
    ENV = {"T_AUTH": "auth-secret-123", "T_PRIV": "priv-secret-456"}

    def probe(self, backend, env=None):
        with patch.dict(os.environ, env if env is not None else self.ENV, clear=False):
            return asyncio.run(monitor.snmp_probe("127.0.0.1", self.SNMP, backend=backend))

    def test_probe_success(self):
        r = self.probe(FakeBackend({"1.3.6.1.2.1.1.3.0": 4242, "1.3.6.1.2.1.1.5.0": "sw1"}))
        self.assertEqual((r["ok"], r["status"], r["uptime_ticks"], r["sys_name"]), (True, "UP", 4242, "sw1"))

    def test_probe_error_classification(self):  # H3
        for code, status in [(ErrorCode.TIMEOUT, "DOWN"), (ErrorCode.AUTH_FAILED, "DOWN"),
                             (ErrorCode.DEPENDENCY_MISSING, "UNKNOWN")]:
            r = self.probe(FakeBackend(error=MonitorError(code)))
            self.assertEqual((r["error_code"], r["status"], r["ok"]), (code.value, status, False))

    def test_missing_secret_is_unknown_not_down(self):  # M1
        with patch.dict(os.environ, {}, clear=True):
            r = asyncio.run(monitor.snmp_probe("127.0.0.1", self.SNMP, backend=FakeBackend()))
        self.assertEqual((r["status"], r["error_code"]), ("UNKNOWN", "SECRET_MISSING"))

    def test_probe_never_leaks_secret(self):
        err = MonitorError(ErrorCode.AUTH_FAILED)
        r = self.probe(FakeBackend(error=err))
        self.assertNotIn("auth-secret-123", json.dumps(r))

    def test_missing_pysnmp_does_not_alert_down(self):  # M1 end-to-end
        cfg = {"allowed_networks": ["127.0.0.1"], "failure_threshold": 1, "recovery_threshold": 1,
               "targets": [{"name": "sw", "host": "127.0.0.1", "snmp": self.SNMP}]}
        with tempfile.TemporaryDirectory() as tmp:
            config = monitor.load_config(write_cfg(tmp, cfg))
        state = {}
        factory = lambda t: FakeBackend(error=MonitorError(ErrorCode.DEPENDENCY_MISSING))  # noqa: E731
        with patch.dict(os.environ, self.ENV), patch.object(monitor, "notify") as notify:
            for _ in range(5):
                asyncio.run(monitor.poll(config, state, backend_factory=factory))
        notify.assert_not_called()
        self.assertTrue(state["sw/snmp"]["healthy"])

    def test_poll_runs_targets_concurrently(self):  # M4
        cfg = {"allowed_networks": ["127.0.0.1"], "max_concurrency": 4,
               "targets": [{"name": f"t{i}", "host": "127.0.0.1", "snmp": self.SNMP} for i in range(4)]}
        with tempfile.TemporaryDirectory() as tmp:
            config = monitor.load_config(write_cfg(tmp, cfg))

        class SlowBackend(FakeBackend):
            async def get(self, oids):
                await asyncio.sleep(0.3)
                return [(oids[0], 1), (oids[1], "n")]

        async def run():
            loop = asyncio.get_running_loop()
            t0 = loop.time()
            await monitor.poll(config, {}, backend_factory=lambda t: SlowBackend())
            return loop.time() - t0

        with patch.dict(os.environ, self.ENV):
            elapsed = asyncio.run(run())
        self.assertLess(elapsed, 0.9)  # sequential would be >= 1.2 s

    def test_down_alert_includes_error_code(self):
        cfg = {"allowed_networks": ["127.0.0.1"], "failure_threshold": 2, "recovery_threshold": 1,
               "targets": [{"name": "sw", "host": "127.0.0.1", "snmp": self.SNMP}]}
        with tempfile.TemporaryDirectory() as tmp:
            config = monitor.load_config(write_cfg(tmp, cfg))
        state = {}
        factory = lambda t: FakeBackend(error=MonitorError(ErrorCode.TIMEOUT))  # noqa: E731
        with patch.dict(os.environ, self.ENV), patch.object(monitor, "notify") as notify:
            asyncio.run(monitor.poll(config, state, backend_factory=factory))
            notify.assert_not_called()
            asyncio.run(monitor.poll(config, state, backend_factory=factory))
        notify.assert_called_once()
        self.assertIn("DOWN: sw/snmp (TIMEOUT)", notify.call_args[0][0])


class WebhookTests(unittest.TestCase):
    def test_http_webhook_rejected(self):
        with patch.dict(os.environ, {"KSSH_MONITOR_WEBHOOK": "http://example.invalid"}):
            with patch.object(monitor._WEBHOOK_OPENER, "open") as opener:
                monitor.notify("test status")
                opener.assert_not_called()

    def test_webhook_redirect_is_refused(self):
        req = monitor.urllib.request.Request("https://example.invalid/hook")
        handler = monitor._NoRedirect()
        self.assertIsNone(handler.redirect_request(req, None, 302, "Found", {}, "http://example.invalid/"))

    def test_https_webhook_uses_no_redirect_opener(self):
        with patch.dict(os.environ, {"KSSH_MONITOR_WEBHOOK": "https://example.invalid/hook"}):
            with patch.object(monitor._WEBHOOK_OPENER, "open") as opener:
                monitor.notify("test status")
                opener.assert_called_once()

    def test_redirect_not_followed_end_to_end(self):
        """Real local HTTP server answers 302 -> second server must never be hit."""
        import http.server
        import threading

        hits = {"target": 0}

        class Target(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                hits["target"] += 1
                self.send_response(200)
                self.end_headers()

            def log_message(self, *a):
                pass

        target = http.server.HTTPServer(("127.0.0.1", 0), Target)

        class Redirector(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                self.send_response(307)
                self.send_header("Location", f"http://127.0.0.1:{target.server_port}/leak")
                self.end_headers()

            def log_message(self, *a):
                pass

        redir = http.server.HTTPServer(("127.0.0.1", 0), Redirector)
        for srv in (target, redir):
            threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            req = monitor.urllib.request.Request(
                f"http://127.0.0.1:{redir.server_port}/hook", data=b"{}", method="POST")
            with self.assertRaises(monitor.urllib.error.HTTPError) as ctx:
                monitor._WEBHOOK_OPENER.open(req, timeout=5)
            self.assertEqual(ctx.exception.code, 307)
            self.assertEqual(hits["target"], 0)
        finally:
            for srv in (target, redir):
                srv.shutdown()
                srv.server_close()


if __name__ == "__main__":
    unittest.main()
