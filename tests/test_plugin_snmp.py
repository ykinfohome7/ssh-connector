"""Offline tests for the read-only SNMP MCP tools in the installable plugin.

The tools are exercised with an in-memory fake SNMP agent; no network traffic.
Registration in server.py is checked only when its runtime deps (mcp<2, asyncssh)
are importable (they are in CI; tests/test_plugins.py also checks the count of 56).
"""
import asyncio
import importlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "ssh-connector"
sys.path.insert(0, str(PLUGIN))

import snmp_tools  # noqa: E402
from kssh_snmp.snmp_client import END_OF_MIB, NO_SUCH, parse_oid  # noqa: E402

ENV = {"T_AUTH": "auth-secret-123", "T_PRIV": "priv-secret-456"}
DEVICE = {"host": "192.0.2.10", "adapter": "realhd", "version": "3", "user": "mon",
          "security_level": "authPriv", "auth_env": "T_AUTH", "priv_env": "T_PRIV"}


class FakeAgent:
    def __init__(self, mib):
        self.mib = mib

    def _next(self, oid):
        for o in sorted(self.mib, key=parse_oid):
            if parse_oid(o) > parse_oid(oid):
                return o, self.mib[o]
        return oid, END_OF_MIB

    async def get(self, oids):
        return [(o, self.mib.get(o, NO_SUCH)) for o in oids]

    async def getnext(self, oids):
        return [self._next(o) for o in oids]

    async def getbulk(self, n, m, oids):
        out, cur = [], oids[0]
        for _ in range(m):
            nxt = self._next(cur)
            out.append(nxt)
            if nxt[1] is END_OF_MIB:
                break
            cur = nxt[0]
        return out


def mib(uptime=100, hc_in=0, errors=0):
    m = {"1.3.6.1.2.1.1.1.0": "Real HD SW5-10G-RJ45", "1.3.6.1.2.1.1.3.0": uptime,
         "1.3.6.1.2.1.1.5.0": "sw-core", "1.3.6.1.2.1.1.6.0": "x" * 5000}
    for idx, name in ((1, "Te1"), (2, "Te2"), (3, "mgmt0")):
        m.update({f"1.3.6.1.2.1.2.2.1.2.{idx}": name, f"1.3.6.1.2.1.2.2.1.7.{idx}": 1,
                  f"1.3.6.1.2.1.2.2.1.8.{idx}": 1 if idx != 2 else 2, f"1.3.6.1.2.1.2.2.1.14.{idx}": errors,
                  f"1.3.6.1.2.1.31.1.1.1.1.{idx}": name, f"1.3.6.1.2.1.31.1.1.1.6.{idx}": hc_in,
                  f"1.3.6.1.2.1.31.1.1.1.10.{idx}": 0, f"1.3.6.1.2.1.31.1.1.1.15.{idx}": 10_000})
    return m


class Env:
    """Temporary servers.yaml + env + fake backend for one test."""

    def __init__(self, snmp_section, agent=None):
        self.snmp = snmp_section
        self.agent = agent or FakeAgent(mib())

    def __enter__(self):
        import yaml
        self.tmp = tempfile.TemporaryDirectory()
        path = Path(self.tmp.name) / "servers.yaml"
        path.write_text(yaml.safe_dump({"servers": {}, "snmp": self.snmp}))
        self.patches = [patch.dict(os.environ, {**ENV, "SSH_CONNECTOR_CONFIG": str(path)}),
                        patch.object(snmp_tools, "BACKEND_FACTORY", lambda name, cfg: self.agent),
                        patch.object(snmp_tools, "AUDIT", [])]
        for p in self.patches:
            p.start()
        return self

    def __exit__(self, *exc):
        for p in reversed(self.patches):
            p.stop()
        self.tmp.cleanup()

    @property
    def audit(self):
        return snmp_tools.AUDIT


GOOD = {"allowed_networks": ["192.0.2.10/32"], "devices": {"realhd-switch": DEVICE}}


def call(coro):
    return json.loads(asyncio.run(coro))


class ConfigTests(unittest.TestCase):
    def test_config_errors_are_unknown_not_down(self):
        cases = [
            ({}, "no 'snmp' section"),
            ({"devices": {"a": DEVICE}}, "allowed_networks"),
            ({"allowed_networks": ["10.0.0.0/8"], "devices": {"a": DEVICE}}, "not in snmp.allowed_networks"),
            ({"allowed_networks": ["192.0.2.0/24"], "devices": {"a": dict(DEVICE, priv_protocol="DES")}},
             "allow_legacy_des"),
            ({"allowed_networks": ["192.0.2.0/24"], "devices": {"a": dict(DEVICE, adapter="hp")}}, "unknown adapter"),
            ({"allowed_networks": ["192.0.2.0/24"], "devices": {"a": {"version": "2c", "host": "192.0.2.10",
                                                                         "community_env": "C"}}}, "allow_legacy_snmp"),
        ]
        for section, msg in cases:
            with Env(section):
                r = call(snmp_tools.snmp_health("a"))
            self.assertEqual((r["status"], r["error_code"]), ("UNKNOWN", "CONFIG_ERROR"), section)
            self.assertIn(msg, r["detail"])

    def test_only_configured_device_names(self):
        with Env(GOOD):
            r = call(snmp_tools.snmp_health("192.0.2.10"))  # a raw host is not accepted
        self.assertEqual(r["error_code"], "CONFIG_ERROR")
        self.assertIn("unknown snmp device", r["detail"])

    def test_missing_secret(self):
        with Env(GOOD), patch.dict(os.environ, {"T_AUTH": ""}):
            r = call(snmp_tools.snmp_health("realhd-switch"))
        self.assertEqual((r["status"], r["error_code"]), ("UNKNOWN", "SECRET_MISSING"))


class ToolTests(unittest.TestCase):
    def test_health_and_case_insensitive_name(self):
        with Env(GOOD) as env:
            r = call(snmp_tools.snmp_health("REALHD-switch"))
            self.assertEqual(env.audit[-1]["command"], "snmp:snmp_health")
            self.assertEqual(env.audit[-1]["exit_code"], 0)
        self.assertEqual((r["status"], r["sys_uptime_ticks"], r["read_only"]), ("UP", 100, True))

    def test_device_info_truncates_and_marks_unavailable(self):
        with Env(GOOD):
            r = call(snmp_tools.snmp_device_info("realhd-switch"))
        self.assertEqual(r["sys_descr"], "Real HD SW5-10G-RJ45")
        self.assertEqual(r["model"], "UNAVAILABLE")
        self.assertEqual(r["environment"]["temperature_c"], "UNAVAILABLE")
        self.assertFalse(r["capabilities"]["write_operations"])
        self.assertTrue(r["sys_location"].endswith("...[truncated]"))  # every value is length-capped
        self.assertLess(len(r["sys_location"]), 1100)

    def test_get_getnext_getbulk(self):
        with Env(GOOD):
            g = call(snmp_tools.snmp_get("realhd-switch", ["1.3.6.1.2.1.1.5.0", "1.3.6.1.2.1.1.99.0",
                                                            "1.3.6.1.2.1.1.6.0"]))
            n = call(snmp_tools.snmp_getnext("realhd-switch", ["1.3.6.1.2.1.1.1.0"]))
            b = call(snmp_tools.snmp_getbulk("realhd-switch", ["1.3.6.1.2.1.2.2.1.2"], 999))
        self.assertEqual(g["values"]["1.3.6.1.2.1.1.5.0"], "sw-core")
        self.assertEqual(g["values"]["1.3.6.1.2.1.1.99.0"], "NO_SUCH_OBJECT")
        self.assertTrue(g["values"]["1.3.6.1.2.1.1.6.0"].endswith("...[truncated]"))
        self.assertEqual(n["values"][0]["oid"], "1.3.6.1.2.1.1.3.0")
        self.assertEqual(len(b["values"]), 25)  # max_repetitions capped

    def test_walk_bounded(self):
        with Env(GOOD):
            r = call(snmp_tools.snmp_walk("realhd-switch", "1.3.6.1.2.1.2.2.1.2", 2))
            full = call(snmp_tools.snmp_walk("realhd-switch", "1.3.6.1.2.1.2.2.1.2", 10_000_000))
        self.assertEqual((r["count"], r["truncated"]), (2, True))
        self.assertEqual((full["count"], full["truncated"]), (3, False))

    def test_invalid_inputs(self):
        with Env(GOOD):
            for coro in (snmp_tools.snmp_get("realhd-switch", ["sysName.0"]),
                         snmp_tools.snmp_get("realhd-switch", []),
                         snmp_tools.snmp_walk("realhd-switch", "1.3.6.1; rm -rf /"),
                         snmp_tools.snmp_get("realhd-switch", [f"1.3.6.1.{i}" for i in range(40)])):
                r = call(coro)
                self.assertEqual(r["status"], "UNKNOWN", r)

    def test_interfaces_filter(self):
        with Env(GOOD):
            r = call(snmp_tools.snmp_interfaces("realhd-switch", "Te*"))
        self.assertEqual([i["name"] for i in r["interfaces"]], ["Te1", "Te2"])
        self.assertEqual(r["interfaces"][1]["oper_status"], "down")
        self.assertNotIn("rates", r["interfaces"][0])

    def test_interface_stats_two_samples(self):
        agent = FakeAgent(mib(uptime=100, hc_in=0, errors=0))
        clock = iter([1000.0, 1005.0])

        async def fake_sleep(_s):
            agent.mib = mib(uptime=600, hc_in=625_000_000, errors=10)  # 1 Gbit/s over 5 s

        with Env(GOOD, agent), patch.object(snmp_tools, "SLEEP", fake_sleep), \
                patch.object(snmp_tools, "CLOCK", lambda: next(clock)):
            r = call(snmp_tools.snmp_interface_stats("realhd-switch", "Te1", 5))
        te1 = r["interfaces"][0]
        self.assertEqual(r["interval_s"], 5.0)
        self.assertEqual(te1["rates"]["in_bps"], 1_000_000_000.0)
        self.assertEqual(te1["rates"]["in_util_pct"], 10.0)
        self.assertEqual(te1["rates"]["in_errors_per_s"], 2.0)

    def test_device_errors_are_down_and_never_leak_secrets(self):
        from kssh_snmp.errors import ErrorCode, MonitorError

        class Failing(FakeAgent):
            async def get(self, oids):
                raise MonitorError(ErrorCode.AUTH_FAILED, "snmp auth_failed")

        class Crashing(FakeAgent):
            async def get(self, oids):
                raise RuntimeError(f"backend said key={ENV['T_AUTH']}")

        with Env(GOOD, Failing({})) as env:
            r = call(snmp_tools.snmp_health("realhd-switch"))
            self.assertEqual(env.audit[-1]["exit_code"], 1)
        self.assertEqual((r["status"], r["error_code"]), ("DOWN", "AUTH_FAILED"))
        with Env(GOOD, Crashing({})):
            raw = asyncio.run(snmp_tools.snmp_health("realhd-switch"))
        self.assertNotIn(ENV["T_AUTH"], raw)
        self.assertEqual(json.loads(raw)["detail"], "RuntimeError")


class ReadOnlyAndPackagingTests(unittest.TestCase):
    def test_no_write_operation_anywhere(self):
        for path in [PLUGIN / "snmp_tools.py", *(PLUGIN / "kssh_snmp").glob("*.py")]:
            text = path.read_text()
            for bad in ("set_cmd", "setCmd", "def snmp_set", "def set("):
                self.assertNotIn(bad, text, f"{path.name}: {bad}")
        self.assertEqual(sorted(snmp_tools.TOOLS), sorted(n for n in dir(snmp_tools) if n.startswith("snmp_")))

    def test_vendored_library_in_sync_with_monitoring(self):
        out = subprocess.run([sys.executable, str(ROOT / "scripts" / "sync_plugin_snmp.py"), "--check"],
                             capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)

    def test_example_configs_valid_and_secret_free(self):
        for path in (ROOT / "servers.example.yaml", PLUGIN / "servers.example.yaml"):
            cfg = snmp_tools.load_snmp_config(str(path))
            self.assertIn("realhd-switch", cfg["devices"])
            text = path.read_text()
            self.assertNotIn("authKey", text)
            self.assertNotIn("password:", text.split("snmp:")[1])

    def test_server_registers_all_snmp_tools_with_help(self):
        try:
            os.environ.setdefault("SSH_CONNECTOR_CONFIG", str(PLUGIN / "servers.example.yaml"))
            server = importlib.import_module("server")
        except Exception as exc:  # mcp<2 / asyncssh absent outside CI
            self.skipTest(f"server.py not importable here: {type(exc).__name__}")
        for name in snmp_tools.TOOLS:
            self.assertIn(name, server.HELP)
            bg, en, example = server.HELP[name]
            self.assertTrue(bg and en and "device" in example)
            self.assertTrue(callable(getattr(server, name)))
        self.assertEqual(len(server.HELP), 56)


if __name__ == "__main__":
    unittest.main()
