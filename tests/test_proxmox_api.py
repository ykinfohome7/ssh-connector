"""Offline Proxmox VE API tests: synthetic responses only; no sockets."""
import json
import os
import socket
import ssl
import unittest
import urllib.error
from unittest.mock import patch

from monitoring.proxmox_api import ProxmoxReadOnlyClient, MAX_BODY


class Response:
    def __init__(self, body, status=200):
        self.status = status
        self.body = body if isinstance(body, bytes) else json.dumps(
            {"data": body}).encode("utf-8")

    def read(self, limit):
        return self.body[:limit]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class APITests(unittest.TestCase):
    def setUp(self):
        self.credentials = patch.dict(os.environ, {
            "KSSH_PROXMOX_TOKEN_ID": "monitor@pve!readonly",
            "KSSH_PROXMOX_TOKEN_SECRET": "test-value-not-real",
        })
        self.credentials.start()
        self.addCleanup(self.credentials.stop)
        self.client = ProxmoxReadOnlyClient(
            "https://example.invalid:8006", allowed_hosts=["example.invalid"],
            timeout=1)

    def read(self, method, data, *args):
        with patch.object(self.client._opener, "open", return_value=Response(data)) as mocked:
            result = getattr(self.client, method)(*args)
            self.assertTrue(result["ok"], result)
            self.assertEqual(mocked.call_count, 1)
            request = mocked.call_args.args[0]
            self.assertEqual(request.get_method(), "GET")
            self.assertEqual(
                request.get_header("Authorization"),
                "PVEAPIToken=monitor@pve!readonly=test-value-not-real")
            self.assertEqual(mocked.call_args.kwargs["timeout"], 1.0)
            return result, request.full_url

    def test_version_genuine_api_response(self):
        result, url = self.read("version", {"version": "8.4.0", "release": "8.4"})
        self.assertEqual(url, "https://example.invalid:8006/api2/json/version")
        self.assertEqual(result["data"]["version"], "8.4.0")
        for key in ("ok", "status", "node", "resource", "timestamp_utc",
                    "data", "error_code", "source", "capabilities"):
            self.assertIn(key, result)
        self.assertTrue(result["timestamp_utc"].endswith("Z"))

    def test_nodes_are_discovered_not_hardcoded(self):
        result, _ = self.read("discover_nodes", [
            {"node": "host-a", "status": "online"},
            {"node": "host-b", "status": "offline"}])
        self.assertEqual([r["node"] for r in result["data"]], ["host-a", "host-b"])

    def test_cpu_ram_swap_and_absent_network(self):
        result, url = self.read("node_status", {
            "cpu": 0.18, "uptime": 90, "memory": {"total": 1000, "used": 430},
            "swap": {"total": 300, "used": 0}}, "host-a")
        self.assertTrue(url.endswith("/nodes/host-a/status"))
        self.assertEqual(result["data"]["memory"]["used"], 430)
        self.assertEqual(result["data"]["swap"]["used"], 0)
        self.assertFalse(result["capabilities"]["network_metrics"])
        self.assertNotIn("netin", result["data"])

    def test_supported_network_metrics_preserved(self):
        result, _ = self.read("node_status", {"netin": 123, "netout": 0}, "host-a")
        self.assertTrue(result["capabilities"]["network_metrics"])
        self.assertEqual(result["data"]["netout"], 0)

    def test_empty_qemu_inventory_not_failure(self):
        result, _ = self.read("qemu", [], "host-a")
        self.assertTrue(result["capabilities"]["inventory"])
        self.assertEqual(result["data"], [])
        self.assertFalse(result["capabilities"]["network_metrics"])

    def test_running_and_stopped_vm_are_reported_as_given(self):
        result, _ = self.read("qemu", [
            {"vmid": 703, "name": "vm703", "status": "running", "netin": 8},
            {"vmid": 5, "name": "vm5", "status": "stopped"}], "host-a")
        self.assertEqual([vm["vmid"] for vm in result["data"]], [703, 5])
        self.assertEqual([vm["status"] for vm in result["data"]],
                         ["running", "stopped"])
        self.assertTrue(result["capabilities"]["network_metrics"])

    def test_lxc_inventory(self):
        result, url = self.read("lxc", [
            {"vmid": 220, "status": "running", "name": "container"}], "host-a")
        self.assertEqual(result["data"][0]["vmid"], 220)
        self.assertTrue(url.endswith("/nodes/host-a/lxc"))

    def test_storage_warning_and_unavailable_capacity(self):
        result, _ = self.read("storage", [
            {"storage": "fast", "used": 92, "total": 100, "active": 1},
            {"storage": "unknown", "active": 1},
            {"storage": "offline", "active": 0}], "host-a")
        self.assertTrue(result["capabilities"]["capacity"])
        self.assertTrue(result["data"][0]["warning"])
        self.assertIsNone(result["data"][1]["warning"])
        self.assertNotIn("usage_ratio", result["data"][1])
        self.assertTrue(result["data"][2]["warning"])

    def test_failed_backup_tasks_not_pbs_health(self):
        result, url = self.read("backup_tasks", [
            {"type": "vzdump", "upid": "task1", "status": "OK", "endtime": 12},
            {"type": "vzdump", "upid": "task2", "status": "ERROR", "endtime": 15},
            {"type": "vzdump", "upid": "task3", "status": "unknown"},
            {"type": "apt", "upid": "not-a-backup", "status": "ERROR", "endtime": 18},
        ], "host-a")
        self.assertIn("typefilter=vzdump", url)
        self.assertEqual([t["upid"] for t in result["data"]["failures"]], ["task2"])
        self.assertEqual(result["data"]["total_returned"], 3)
        self.assertFalse(result["capabilities"]["pbs_health"])

    def test_error_classification(self):
        cases = [(401, "AUTH_FAILED"), (403, "PERMISSION_DENIED"),
                 (404, "RESOURCE_NOT_FOUND"), (302, "UNAVAILABLE"),
                 (500, "UNAVAILABLE")]
        for status, expected in cases:
            with self.subTest(status=status):
                exc = urllib.error.HTTPError(
                    "https://example.invalid:8006", status, "failure", {}, None)
                with patch.object(self.client._opener, "open", side_effect=exc):
                    result = self.client.qemu("host-a")
                self.assertFalse(result["ok"])
                self.assertIsNone(result["data"])
                self.assertEqual(result["error_code"], expected)
                self.assertNotEqual(result["status"], "STOPPED")

    def test_timeout_and_network_unreachable(self):
        for exc in [socket.timeout("timeout"), ConnectionRefusedError(),
                    urllib.error.URLError(socket.timeout())]:
            with self.subTest(exc=type(exc).__name__):
                with patch.object(self.client._opener, "open", side_effect=exc):
                    result = self.client.node_status("host-a")
                self.assertEqual(result["error_code"], "API_UNREACHABLE")

    def test_tls_failure_and_wrapped_tls_failure(self):
        for exc in [ssl.SSLCertVerificationError("bad certificate"),
                    urllib.error.URLError(ssl.SSLError("bad certificate"))]:
            with patch.object(self.client._opener, "open", side_effect=exc):
                self.assertEqual(
                    self.client.version()["error_code"], "TLS_ERROR")

    def test_malformed_json_payloads_and_shapes(self):
        raw = [b"{bad", b"{}", b'{"data":null}', b'{"data":{}}',
               b'{"data":[{"vmid":"wrong"}]}']
        for body in raw:
            with self.subTest(body=body):
                with patch.object(self.client._opener, "open",
                                  return_value=Response(body)):
                    self.assertEqual(self.client.qemu("host-a")["error_code"],
                                     "MALFORMED_RESPONSE")

    def test_oversized_response_rejected(self):
        with patch.object(self.client._opener, "open",
                          return_value=Response(b"x" * (MAX_BODY + 2))):
            self.assertEqual(self.client.version()["error_code"],
                             "MALFORMED_RESPONSE")

    def test_partial_snapshot_never_fabricates_vm_status(self):
        responses = [
            Response({"version": "8.4"}),
            Response({"cpu": 0.5}),
            urllib.error.HTTPError(
                "https://example.invalid:8006", 403, "denied", {}, None),
            Response([{"vmid": 321, "status": "running"}]),
            Response([]),
            Response([]),
        ]
        with patch.object(self.client._opener, "open", side_effect=responses):
            result = self.client.snapshot("host-a")
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "DEGRADED")
        self.assertIsNone(result["data"]["resources"]["storage"])
        self.assertEqual(result["data"]["errors"]["storage"], "PERMISSION_DENIED")
        self.assertFalse(result["capabilities"]["storage"])
        self.assertFalse(result["capabilities"]["pbs_health"])
        self.assertEqual(result["data"]["resources"]["qemu"][0]["vmid"], 321)

    def test_all_unavailable_snapshot_is_not_down_claim(self):
        with patch.dict(os.environ, {"KSSH_PROXMOX_TOKEN_SECRET": ""}):
            with patch.object(self.client._opener, "open") as mocked:
                result = self.client.snapshot("host-a")
            mocked.assert_not_called()
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertEqual(result["error_code"], "UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
