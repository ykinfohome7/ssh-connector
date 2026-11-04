"""Offline tests for the read-only SNMP module, interface maths and adapters.

All tests use an in-memory fake SNMP agent; no network traffic, no real devices.
"""
import asyncio
import importlib.util
import json
import logging
import os
import sys
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from monitoring import logutil  # noqa: E402
from monitoring.errors import ErrorCode, MonitorError, status_for  # noqa: E402
from monitoring.snmp_adapters import (  # noqa: E402
    UNAVAILABLE, GenericAdapter, RealHDAdapter, make_adapter, sensor_reading)
from monitoring.snmp_client import (  # noqa: E402
    END_OF_MIB, NO_SUCH, Allowlist, PysnmpBackend, SnmpClient, SnmpCredentials,
    SnmpLimits, SnmpTarget, classify_error_indication, parse_oid)
from monitoring.snmp_interfaces import (  # noqa: E402
    WRAP32, DeviceSample, FlapTracker, InterfaceSample, collect_sample, compute_rates)

ENV = {"T_AUTH": "auth-secret-123", "T_PRIV": "priv-secret-456", "T_COMM": "community-xyz"}
V3 = SnmpCredentials(version="3", user="mon", security_level="authPriv",
                     auth_env="T_AUTH", priv_env="T_PRIV")


def key(oid):
    return parse_oid(oid)


class FakeAgent:
    """Minimal in-memory SNMP agent implementing GET/GETNEXT/GETBULK semantics."""

    def __init__(self, mib=None, *, delay=0.0, error=None, broken_order=False):
        self.mib = dict(mib or {})
        self.delay = delay
        self.error = error
        self.broken_order = broken_order
        self.calls = []
        self.active = 0
        self.max_active = 0

    async def _enter(self, kind):
        self.calls.append(kind)
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            if self.delay:
                await asyncio.sleep(self.delay)
            if self.error:
                raise self.error
        finally:
            self.active -= 1

    def _next(self, oid):
        if self.broken_order and getattr(self, "_stuck", None):
            return self._stuck  # buggy agent: repeats an OID -> must be detected
        for o in sorted(self.mib, key=key):
            if key(o) > key(oid):
                self._stuck = (o, self.mib[o])
                return o, self.mib[o]
        return oid, END_OF_MIB

    async def get(self, oids):
        await self._enter("get")
        return [(o, self.mib.get(o, NO_SUCH)) for o in oids]

    async def getnext(self, oids):
        await self._enter("next")
        return [self._next(o) for o in oids]

    async def getbulk(self, non_rep, max_rep, oids):
        await self._enter("bulk")
        out, cursor = [], oids[0]
        for _ in range(max_rep):
            nxt = self._next(cursor)
            out.append(nxt)
            if nxt[1] is END_OF_MIB:
                break
            cursor = nxt[0]
        return out


def client(agent, creds=V3, limits=None, host="127.0.0.1"):
    return SnmpClient(SnmpTarget(host), creds, Allowlist(["127.0.0.0/8"]), limits=limits, backend=agent)


def run(coro):
    with patch.dict(os.environ, ENV):
        return asyncio.run(coro)


class OidAndAllowlistTests(unittest.TestCase):
    def test_oid_validation(self):
        self.assertEqual(parse_oid(".1.3.6.1"), (1, 3, 6, 1))
        for bad in ("", "1", "1.3.x", "sysName.0", "1.3.6." , "5.1", "1." + ".".join(["1"] * 200), "1.4294967296"):
            with self.assertRaises(MonitorError, msg=bad):
                parse_oid(bad)

    def test_allowlist(self):
        al = Allowlist(["192.168.30.10/32", "192.168.0.0/24", "switch.lan"])
        self.assertTrue(al.allows("192.168.30.10"))
        self.assertTrue(al.allows("192.168.0.127"))
        self.assertTrue(al.allows("SWITCH.lan."))
        self.assertFalse(al.allows("192.168.30.11"))
        self.assertFalse(al.allows("8.8.8.8"))
        self.assertFalse(al.allows("evil.switch.lan"))
        with self.assertRaises(MonitorError):
            Allowlist([])
        with self.assertRaises(MonitorError):
            Allowlist(["bad host!"])

    def test_client_refuses_target_outside_allowlist(self):
        with self.assertRaises(MonitorError) as ctx:
            SnmpClient(SnmpTarget("10.0.0.1"), V3, Allowlist(["192.168.0.0/24"]), backend=FakeAgent())
        self.assertEqual(ctx.exception.code, ErrorCode.NOT_ALLOWED)


class CredentialTests(unittest.TestCase):
    def test_security_levels(self):
        SnmpCredentials(version="3", user="u", security_level="noAuthNoPriv").validate()
        SnmpCredentials(version="3", user="u", security_level="authNoPriv", auth_env="A",
                        auth_protocol="SHA256").validate()
        V3.validate()
        with self.assertRaises(MonitorError):
            SnmpCredentials(version="3", user="u", security_level="authOnly").validate()

    def test_md5_and_unknown_protocols_rejected(self):
        for kw in ({"auth_protocol": "MD5"}, {"priv_protocol": "3DES"}, {"priv_protocol": "DES"}):
            with self.assertRaises(MonitorError, msg=kw):
                SnmpCredentials(version="3", user="u", auth_env="A", priv_env="P", **kw).validate()

    def test_des_needs_opt_in(self):
        SnmpCredentials(version="3", user="u", auth_env="A", priv_env="P",
                        priv_protocol="DES", allow_legacy_des=True).validate()

    def test_default_is_v3_aes_authpriv(self):
        c = SnmpCredentials(user="u", auth_env="A", priv_env="P")
        self.assertEqual((c.version, c.security_level, c.priv_protocol), ("3", "authPriv", "AES"))

    def test_env_names_not_values_in_config(self):
        with self.assertRaises(MonitorError):
            SnmpCredentials(version="3", user="u", auth_env="my secret pw", priv_env="P").validate()

    def test_secrets_resolved_only_from_env_and_scrubbed(self):
        with patch.dict(os.environ, ENV):
            secrets = V3.resolve_secrets()
        self.assertEqual(secrets, {"auth_key": ENV["T_AUTH"], "priv_key": ENV["T_PRIV"]})
        self.assertNotIn(ENV["T_AUTH"], repr(V3) + json.dumps(V3.describe()))
        self.assertEqual(logutil.scrub_text(f"x {ENV['T_PRIV']} y"), "x [REDACTED] y")

    def test_short_v3_key_rejected(self):
        with patch.dict(os.environ, {"T_AUTH": "short", "T_PRIV": "long-enough"}):
            with self.assertRaises(MonitorError) as ctx:
                V3.resolve_secrets()
        self.assertEqual(ctx.exception.code, ErrorCode.CONFIG_ERROR)

    def test_no_silent_downgrade(self):
        """A v3 auth failure stays a v3 failure; no v2c/v1 request is attempted."""
        agent = FakeAgent(error=MonitorError(ErrorCode.AUTH_FAILED))
        with self.assertRaises(MonitorError) as ctx:
            run(client(agent).get(["1.3.6.1.2.1.1.3.0"]))
        self.assertEqual(ctx.exception.code, ErrorCode.AUTH_FAILED)
        self.assertEqual(agent.calls, ["get"])


class ClientTests(unittest.TestCase):
    MIB = {f"1.3.6.1.2.1.2.2.1.2.{i}": f"port{i}" for i in range(1, 51)}
    MIB.update({"1.3.6.1.2.1.1.3.0": 100, "1.3.6.1.2.1.2.2.1.3.1": 6})

    def test_no_write_operations_exist(self):
        for name in ("set", "set_cmd", "snmp_set", "setcmd"):
            self.assertFalse(hasattr(SnmpClient, name), name)
            self.assertFalse(hasattr(PysnmpBackend, name), name)
        src = (Path(__file__).resolve().parents[1] / "monitoring" / "snmp_client.py").read_text()
        self.assertNotIn("set_cmd", src)

    def test_get_and_missing(self):
        res = run(client(FakeAgent(self.MIB)).get(["1.3.6.1.2.1.1.3.0", "1.3.6.1.2.1.1.99.0"]))
        self.assertEqual(res["1.3.6.1.2.1.1.3.0"], 100)
        self.assertIs(res["1.3.6.1.2.1.1.99.0"], NO_SUCH)

    def test_request_oid_limit(self):
        c = client(FakeAgent(), limits=SnmpLimits(max_oids_per_request=2))
        with self.assertRaises(MonitorError) as ctx:
            run(c.get(["1.3.6.1.1", "1.3.6.1.2", "1.3.6.1.3"]))
        self.assertEqual(ctx.exception.code, ErrorCode.LIMIT_EXCEEDED)

    def test_walk_stays_in_subtree(self):
        res = run(client(FakeAgent(self.MIB)).walk("1.3.6.1.2.1.2.2.1.2"))
        self.assertEqual(len(res.items), 50)
        self.assertFalse(res.truncated)
        self.assertTrue(all(o.startswith("1.3.6.1.2.1.2.2.1.2.") for o, _ in res.items))

    def test_walk_with_getnext_and_v1(self):
        v1 = SnmpCredentials(version="1", community_env="T_COMM", allow_legacy_snmp=True)
        agent = FakeAgent(self.MIB)
        res = run(client(agent, creds=v1).walk("1.3.6.1.2.1.2.2.1.2"))
        self.assertEqual(len(res.items), 50)
        self.assertEqual(set(agent.calls), {"next"})
        with self.assertRaises(MonitorError):
            run(client(agent, creds=v1).getbulk(["1.3.6.1"]))

    def test_walk_result_limit(self):
        res = run(client(FakeAgent(self.MIB), limits=SnmpLimits(max_walk_results=10)).walk("1.3.6.1.2.1.2.2.1.2"))
        self.assertEqual(len(res.items), 10)
        self.assertTrue(res.truncated)
        self.assertIn("max_walk_results", res.reason)

    def test_walk_cannot_exceed_configured_or_hard_caps(self):
        lim = SnmpLimits(max_walk_results=5)
        res = run(client(FakeAgent(self.MIB), limits=lim).walk("1.3.6.1.2.1.2.2.1.2", max_results=10_000_000))
        self.assertEqual(len(res.items), 5)

    def test_walk_duration_limit(self):
        agent = FakeAgent(self.MIB, delay=0.05)
        lim = SnmpLimits(max_walk_seconds=0.12, max_repetitions=1)
        res = run(client(agent, limits=lim).walk("1.3.6.1.2.1.2.2.1.2"))
        self.assertTrue(res.truncated)
        self.assertIn("max_walk_seconds", res.reason)
        self.assertLess(len(res.items), 50)

    def test_walk_detects_non_increasing_oid(self):
        with self.assertRaises(MonitorError) as ctx:
            run(client(FakeAgent(self.MIB, broken_order=True)).walk("1.3.6.1.2.1.2.2.1.2"))
        self.assertEqual(ctx.exception.code, ErrorCode.PROTOCOL_ERROR)

    def test_getbulk_repetitions_capped(self):
        res = run(client(FakeAgent(self.MIB), limits=SnmpLimits(max_repetitions=7)).getbulk(
            ["1.3.6.1.2.1.2.2.1.2"], max_repetitions=1000))
        self.assertEqual(len(res), 7)

    def test_concurrency_limit(self):
        agent = FakeAgent(self.MIB, delay=0.05)
        c = client(agent, limits=SnmpLimits(max_concurrency=2))

        async def many():
            await asyncio.gather(*(c.get(["1.3.6.1.2.1.1.3.0"]) for _ in range(6)))
        run(many())
        self.assertEqual(agent.max_active, 2)

    def test_cancellation_propagates(self):
        agent = FakeAgent(self.MIB, delay=5)

        async def go():
            task = asyncio.create_task(client(agent).get(["1.3.6.1.2.1.1.3.0"]))
            await asyncio.sleep(0.05)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            self.assertEqual(agent.active, 0)
        run(go())

    def test_missing_secret_fails_before_network(self):
        agent = FakeAgent(self.MIB)
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(MonitorError) as ctx:
                asyncio.run(client(agent).get(["1.3.6.1.2.1.1.3.0"]))
        self.assertEqual(ctx.exception.code, ErrorCode.SECRET_MISSING)
        self.assertEqual(agent.calls, [])


class ErrorClassificationTests(unittest.TestCase):
    def test_indications(self):
        cases = {
            "No SNMP response received before timeout": ErrorCode.TIMEOUT,
            "Unknown USM user": ErrorCode.AUTH_FAILED,
            "unknownUserName": ErrorCode.AUTH_FAILED,
            "Wrong SNMP PDU digest": ErrorCode.AUTH_FAILED,
            "decryptionError": ErrorCode.AUTH_FAILED,
            "Unsupported security level": ErrorCode.AUTH_FAILED,
            "Connection refused": ErrorCode.UNREACHABLE,
            "something odd": ErrorCode.PROTOCOL_ERROR,
        }
        for text, code in cases.items():
            self.assertEqual(classify_error_indication(text), code, text)

    def test_status_mapping(self):
        self.assertEqual(status_for(None).value, "UP")
        for c in (ErrorCode.TIMEOUT, ErrorCode.AUTH_FAILED, ErrorCode.UNREACHABLE, ErrorCode.PROTOCOL_ERROR):
            self.assertEqual(status_for(c).value, "DOWN")
        for c in (ErrorCode.DEPENDENCY_MISSING, ErrorCode.SECRET_MISSING, ErrorCode.CONFIG_ERROR,
                  ErrorCode.NOT_ALLOWED, ErrorCode.INTERNAL, ErrorCode.UNAVAILABLE):
            self.assertEqual(status_for(c).value, "UNKNOWN")

    @unittest.skipIf(importlib.util.find_spec("pysnmp") is not None, "pysnmp installed")
    def test_pysnmp_missing_is_dependency_missing(self):
        backend = PysnmpBackend(SnmpTarget("127.0.0.1"), V3)
        with patch.dict(os.environ, ENV):
            with self.assertRaises(MonitorError) as ctx:
                asyncio.run(backend.get(["1.3.6.1.2.1.1.3.0"]))
        self.assertEqual(ctx.exception.code, ErrorCode.DEPENDENCY_MISSING)


def ifc(idx, name="p1", hc_in=None, hc_out=None, lo_in=None, lo_out=None, speed=None,
        high_speed=None, last_change=0, errors=0, disc=None, oper=1):
    data = {"name": name, "descr": name, "admin_status": 1, "oper_status": oper, "last_change": last_change,
            "in_errors": errors, "out_errors": 0, "in_discards": 0, "out_discards": 0}
    for k, v in (("hc_in_octets", hc_in), ("hc_out_octets", hc_out), ("in_octets", lo_in),
                 ("out_octets", lo_out), ("speed", speed), ("high_speed", high_speed),
                 ("counter_discontinuity", disc)):
        if v is not None:
            data[k] = v
    return InterfaceSample(idx, data)


class InterfaceMathTests(unittest.TestCase):
    def sample(self, t, up, *ifs):
        return DeviceSample(t, up, {i.if_index: i for i in ifs})

    def test_baseline_then_rate_with_hc_counters(self):
        a = self.sample(0, 1000, ifc(1, hc_in=0, hc_out=0, lo_in=0, lo_out=0, high_speed=10_000))
        b = self.sample(10, 2000, ifc(1, hc_in=12_500_000_000, hc_out=0, lo_in=5, lo_out=0, high_speed=10_000))
        self.assertIn("BASELINE", compute_rates(None, a)["interfaces"][1]["events"])
        r = compute_rates(a, b)["interfaces"][1]
        self.assertEqual(r["counter_bits"], 64)
        self.assertEqual(r["rates"]["in_bps"], 10_000_000_000.0)   # 12.5 GB in 10 s = 10 Gbit/s
        self.assertEqual(r["rates"]["in_util_pct"], 100.0)
        self.assertEqual(r["speed_bps"], 10_000_000_000)

    def test_32bit_single_wrap(self):
        a = self.sample(0, 100, ifc(1, lo_in=WRAP32 - 1000, lo_out=0, speed=100_000_000))
        b = self.sample(10, 1100, ifc(1, lo_in=24_000, lo_out=0, speed=100_000_000))
        r = compute_rates(a, b)["interfaces"][1]["rates"]
        self.assertEqual(r["in_bps"], (25_000 * 8) / 10)

    def test_32bit_wrap_ambiguous_on_fast_link(self):
        # 10 Gbit/s for 60 s moves 75 GB: a 32-bit counter may wrap many times.
        a = self.sample(0, 100, ifc(1, lo_in=WRAP32 - 1000, lo_out=0, high_speed=10_000))
        b = self.sample(60, 6100, ifc(1, lo_in=500, lo_out=0, high_speed=10_000))
        r = compute_rates(a, b)["interfaces"][1]
        self.assertIsNone(r["rates"]["in_bps"])
        self.assertIn("COUNTER_UNUSABLE", r["events"])

    def test_64bit_decrease_is_discontinuity_not_wrap(self):
        a = self.sample(0, 100, ifc(1, hc_in=10**12, hc_out=0, high_speed=10_000))
        b = self.sample(10, 1100, ifc(1, hc_in=5, hc_out=0, high_speed=10_000))
        self.assertIsNone(compute_rates(a, b)["interfaces"][1]["rates"]["in_bps"])

    def test_reboot_resets_baseline(self):
        a = self.sample(0, 900_000, ifc(1, hc_in=10**9, hc_out=0))
        b = self.sample(60, 300, ifc(1, hc_in=10, hc_out=0))
        res = compute_rates(a, b)
        self.assertIn("REBOOT_OR_UPTIME_WRAP", res["device_events"])
        self.assertIn("COUNTER_DISCONTINUITY", res["interfaces"][1]["events"])
        self.assertIsNone(res["interfaces"][1]["rates"])

    def test_discontinuity_time_change(self):
        a = self.sample(0, 100, ifc(1, hc_in=100, hc_out=0, disc=0))
        b = self.sample(10, 1100, ifc(1, hc_in=200, hc_out=0, disc=500))
        self.assertIn("COUNTER_DISCONTINUITY", compute_rates(a, b)["interfaces"][1]["events"])

    def test_ifindex_reassigned(self):
        a = self.sample(0, 100, ifc(3, name="Te1/0/1", hc_in=100, hc_out=0))
        b = self.sample(10, 1100, ifc(3, name="Te1/0/7", hc_in=200, hc_out=0))
        r = compute_rates(a, b)["interfaces"][3]
        self.assertIn("IFINDEX_REASSIGNED", r["events"])
        self.assertIsNone(r["rates"])

    def test_removed_interface_and_speed_and_link_change(self):
        a = self.sample(0, 100, ifc(1, hc_in=0, hc_out=0, high_speed=1000, last_change=5), ifc(2, name="p2"))
        b = self.sample(10, 1100, ifc(1, hc_in=0, hc_out=0, high_speed=10_000, last_change=900))
        res = compute_rates(a, b)
        self.assertEqual(res["removed_if_indexes"], [2])
        self.assertIn("SPEED_CHANGED", res["interfaces"][1]["events"])
        self.assertIn("LINK_STATE_CHANGED", res["interfaces"][1]["events"])

    def test_error_rates_and_unknown_speed(self):
        a = self.sample(0, 100, ifc(1, hc_in=0, hc_out=0, errors=10))
        b = self.sample(10, 1100, ifc(1, hc_in=1000, hc_out=0, errors=30))
        r = compute_rates(a, b)["interfaces"][1]
        self.assertEqual(r["rates"]["in_errors_per_s"], 2.0)
        self.assertIsNone(r["speed_bps"])
        self.assertIsNone(r["rates"]["in_util_pct"])  # never guessed

    def test_ifspeed_max_value_means_unknown(self):
        self.assertIsNone(ifc(1, speed=4_294_967_295).speed_bps)
        self.assertEqual(ifc(1, speed=4_294_967_295, high_speed=10_000).speed_bps, 10**10)

    def test_flap_tracker(self):
        ft = FlapTracker(window_s=60, threshold=3)
        self.assertFalse(ft.update("p1", True, 0))
        self.assertFalse(ft.update("p1", True, 10))
        self.assertTrue(ft.update("p1", True, 20))
        self.assertFalse(ft.update("p1", False, 200))  # old events expired

    def test_collect_sample_from_fake_agent(self):
        mib = {"1.3.6.1.2.1.1.3.0": 777,
               "1.3.6.1.2.1.2.2.1.2.1": "eth1", "1.3.6.1.2.1.2.2.1.2.2": "eth2",
               "1.3.6.1.2.1.2.2.1.8.1": 1, "1.3.6.1.2.1.2.2.1.8.2": 2,
               "1.3.6.1.2.1.31.1.1.1.6.1": 123, "1.3.6.1.2.1.31.1.1.1.15.1": 10_000}
        s = run(collect_sample(client(FakeAgent(mib)), now=5.0))
        self.assertEqual(s.sys_uptime_ticks, 777)
        self.assertEqual(sorted(s.interfaces), [1, 2])
        self.assertEqual(s.interfaces[1].octets("in"), (123, 64))
        self.assertEqual(s.interfaces[2].octets("in"), (None, 32))
        r = compute_rates(None, s)["interfaces"]
        self.assertEqual((r[1]["oper_status"], r[2]["oper_status"]), ("up", "down"))


class AdapterTests(unittest.TestCase):
    SYS = {"1.3.6.1.2.1.1.1.0": "Real HD SW5-10G-RJ45", "1.3.6.1.2.1.1.2.0": "1.3.6.1.4.1.99999",
           "1.3.6.1.2.1.1.3.0": 4242, "1.3.6.1.2.1.1.5.0": "sw-core"}

    def test_device_info_without_entity_mib(self):
        info = run(RealHDAdapter(client(FakeAgent(self.SYS))).device_info())
        self.assertEqual(info["sys_descr"], "Real HD SW5-10G-RJ45")
        self.assertEqual(info["sys_location"], UNAVAILABLE)
        self.assertEqual((info["model"], info["firmware"]), (UNAVAILABLE, UNAVAILABLE))
        self.assertEqual(info["adapter"], "realhd")

    def test_device_info_with_entity_mib(self):
        mib = dict(self.SYS)
        mib.update({"1.3.6.1.2.1.47.1.1.1.1.5.1": 3, "1.3.6.1.2.1.47.1.1.1.1.13.1": "SW5-10G",
                    "1.3.6.1.2.1.47.1.1.1.1.10.1": "2.1.4", "1.3.6.1.2.1.47.1.1.1.1.5.2": 10})
        info = run(GenericAdapter(client(FakeAgent(mib))).device_info())
        self.assertEqual((info["model"], info["firmware"]), ("SW5-10G", "2.1.4"))

    def test_environment_unavailable_is_never_invented(self):
        env = run(RealHDAdapter(client(FakeAgent(self.SYS))).environment())
        self.assertEqual((env["temperature_c"], env["fans"], env["power"]), (UNAVAILABLE,) * 3)

    def test_environment_from_entity_sensor_mib(self):
        base = "1.3.6.1.2.1.99.1.1.1"
        mib = dict(self.SYS)
        mib.update({f"{base}.1.5": 8, f"{base}.2.5": 9, f"{base}.3.5": 1, f"{base}.4.5": 455, f"{base}.5.5": 1,
                    f"{base}.1.6": 10, f"{base}.2.6": 9, f"{base}.3.6": 0, f"{base}.4.6": 4200, f"{base}.5.6": 1,
                    f"{base}.1.7": 8, f"{base}.2.7": 9, f"{base}.3.7": 0, f"{base}.4.7": 0, f"{base}.5.7": 2})
        env = run(GenericAdapter(client(FakeAgent(mib))).environment())
        self.assertEqual(env["temperature_c"][0]["value"], 45.5)
        self.assertEqual(env["temperature_c"][1]["value"], UNAVAILABLE)  # sensor reports unavailable
        self.assertEqual(env["fans"][0]["value"], 4200.0)
        self.assertEqual(env["power"], UNAVAILABLE)

    def test_sensor_scaling(self):
        self.assertEqual(sensor_reading(12000, 8, 0), 12.0)   # milli
        self.assertEqual(sensor_reading(455, 9, 1), 45.5)
        self.assertIsNone(sensor_reading(NO_SUCH, 9, 0))

    def test_health_and_auth_failure_propagates(self):
        self.assertEqual(run(GenericAdapter(client(FakeAgent(self.SYS))).health())["sys_uptime_ticks"], 4242)
        with self.assertRaises(MonitorError) as ctx:
            run(GenericAdapter(client(FakeAgent(error=MonitorError(ErrorCode.AUTH_FAILED)))).environment())
        self.assertEqual(ctx.exception.code, ErrorCode.AUTH_FAILED)

    def test_adapter_registry_and_capabilities(self):
        c = client(FakeAgent())
        self.assertIsInstance(make_adapter("realhd", c), RealHDAdapter)
        for name in ("generic", "cisco", "unifi"):
            caps = make_adapter(name, c).capabilities()
            self.assertFalse(caps["write_operations"])
            self.assertFalse(caps["vendor_oids_verified"])
        with self.assertRaises(MonitorError):
            make_adapter("nope", c)


class LoggingTests(unittest.TestCase):
    def test_json_log_redacts_keys_and_values(self):
        logutil.register_secret("hunter2-secret")
        stream = StringIO()
        logger = logging.getLogger("kssh.test")
        handler = logging.StreamHandler(stream)
        handler.setFormatter(logutil.JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        try:
            logutil.log_event(logger, logging.INFO, "auth failed with hunter2-secret",
                              password="p", auth_key="k", community="c", auth_protocol="SHA",
                              auth_env="T_AUTH", nested={"api_token": "t", "ok": "hunter2-secret"})
        finally:
            logger.removeHandler(handler)
        line = json.loads(stream.getvalue())
        self.assertNotIn("hunter2-secret", stream.getvalue())
        self.assertEqual(line["password"], "[REDACTED]")
        self.assertEqual(line["auth_key"], "[REDACTED]")
        self.assertEqual(line["community"], "[REDACTED]")
        self.assertEqual(line["nested"]["api_token"], "[REDACTED]")
        self.assertEqual(line["auth_protocol"], "SHA")
        self.assertEqual(line["auth_env"], "T_AUTH")
        self.assertTrue(line["ts_utc"].endswith("Z"))

    def test_exception_text_not_logged(self):
        stream = StringIO()
        logger = logging.getLogger("kssh.test2")
        handler = logging.StreamHandler(stream)
        handler.setFormatter(logutil.JsonFormatter())
        logger.addHandler(handler)
        try:
            try:
                raise RuntimeError("backend said key=supersecretvalue")
            except RuntimeError:
                logger.exception("boom")
        finally:
            logger.removeHandler(handler)
        self.assertNotIn("supersecretvalue", stream.getvalue())
        self.assertIn("RuntimeError", stream.getvalue())


if __name__ == "__main__":
    unittest.main()
