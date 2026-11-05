"""Offline regression / concurrency / timeout / security tests for the monitor engine.

Covers state_store, notifier, interface_monitor and their wiring in monitor.poll/main.
No real devices; network use is limited to 127.0.0.1 test servers.
"""
import asyncio
import http.server
import io
import json
import os
import sys
import tempfile
import threading
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from monitoring import logutil, monitor  # noqa: E402
from monitoring.errors import ErrorCode, MonitorError  # noqa: E402
from monitoring.interface_monitor import (  # noqa: E402
    evaluate, interface_config, sample_from_dict, sample_to_dict, selected)
from monitoring.notifier import Notifier, validate_webhook_url  # noqa: E402
from monitoring.snmp_client import END_OF_MIB, NO_SUCH, Allowlist, parse_oid  # noqa: E402
from monitoring.snmp_interfaces import DeviceSample, InterfaceSample, compute_rates  # noqa: E402
from monitoring.state_store import StateLocked, StateStore, empty_state, migrate  # noqa: E402

ENV = {"T_AUTH": "auth-secret-123", "T_PRIV": "priv-secret-456"}
SNMP = {"version": "3", "user": "mon", "security_level": "authPriv",
        "auth_env": "T_AUTH", "priv_env": "T_PRIV", "adapter": "realhd"}


class FakeAgent:
    """In-memory SNMP agent. ``mib`` may be replaced between polls."""

    def __init__(self, mib=None, delay=0.0, error=None):
        self.mib = dict(mib or {})
        self.delay = delay
        self.error = error
        self.active = 0
        self.max_active = 0

    async def _enter(self):
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
        for o in sorted(self.mib, key=parse_oid):
            if parse_oid(o) > parse_oid(oid):
                return o, self.mib[o]
        return oid, END_OF_MIB

    async def get(self, oids):
        await self._enter()
        return [(o, self.mib.get(o, NO_SUCH)) for o in oids]

    async def getnext(self, oids):
        await self._enter()
        return [self._next(o) for o in oids]

    async def getbulk(self, n, m, oids):
        await self._enter()
        out, cur = [], oids[0]
        for _ in range(m):
            nxt = self._next(cur)
            out.append(nxt)
            if nxt[1] is END_OF_MIB:
                break
            cur = nxt[0]
        return out


def switch_mib(uptime, ports):
    """ports: {idx: (name, admin, oper, hc_in, hc_out, in_err, last_change)}"""
    mib = {"1.3.6.1.2.1.1.3.0": uptime, "1.3.6.1.2.1.1.5.0": "sw"}
    for idx, (name, admin, oper, hc_in, hc_out, err, lc) in ports.items():
        mib.update({
            f"1.3.6.1.2.1.2.2.1.2.{idx}": name, f"1.3.6.1.2.1.2.2.1.7.{idx}": admin,
            f"1.3.6.1.2.1.2.2.1.8.{idx}": oper, f"1.3.6.1.2.1.2.2.1.9.{idx}": lc,
            f"1.3.6.1.2.1.2.2.1.14.{idx}": err, f"1.3.6.1.2.1.2.2.1.20.{idx}": 0,
            f"1.3.6.1.2.1.2.2.1.13.{idx}": 0, f"1.3.6.1.2.1.2.2.1.19.{idx}": 0,
            f"1.3.6.1.2.1.31.1.1.1.1.{idx}": name, f"1.3.6.1.2.1.31.1.1.1.6.{idx}": hc_in,
            f"1.3.6.1.2.1.31.1.1.1.10.{idx}": hc_out, f"1.3.6.1.2.1.31.1.1.1.15.{idx}": 10_000,
        })
    return mib


class RecordingNotifier:
    def __init__(self):
        self.events = []

    def send(self, event):
        self.events.append(event)
        return "printed"


def load(tmp, cfg):
    p = Path(tmp) / "cfg.json"
    p.write_text(json.dumps(cfg))
    return monitor.load_config(p)


def quiet():
    """Silence the JSON logger and prints during a test block."""
    return redirect_stderr(io.StringIO())


# --------------------------------------------------------------------------- state store


class StateStoreTests(unittest.TestCase):
    def test_v1_state_is_migrated(self):  # regression: first MVP format
        v1 = {"pve1/tcp": {"healthy": False, "pending": 0, "seen": True}, "junk": 5}
        st = migrate(v1)
        self.assertEqual(st["schema"], 2)
        self.assertEqual(st["checks"], {"pve1/tcp": {"healthy": False, "pending": 0}})

    def test_unknown_future_schema_rejected(self):
        with self.assertRaises(ValueError):
            migrate({"schema": 99})

    def test_corrupt_file_is_moved_aside_not_deleted(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "state.json"
            p.write_text("{not json")
            store = StateStore(p)
            self.assertEqual(store.load(), empty_state())
            self.assertIsNotNone(store.recovered_from)
            aside = list(Path(tmp).glob("state.json.corrupt-*"))
            self.assertEqual(len(aside), 1)
            self.assertEqual(aside[0].read_text(), "{not json")

    def test_oversized_file_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "state.json"
            with open(p, "wb") as fh:
                fh.truncate(9 * 1024 * 1024)
            store = StateStore(p)
            self.assertEqual(store.load(), empty_state())
            self.assertIn("ValueError", store.recovered_from)

    def test_round_trip_private(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "a" / "state.json"
            st = empty_state()
            st["checks"]["x/tcp"] = {"healthy": False, "pending": 1}
            StateStore(p).save(st)
            self.assertEqual(StateStore(p).load(), st)
            if os.name == "posix":
                self.assertEqual(p.stat().st_mode & 0o077, 0)

    @unittest.skipUnless(os.name == "posix", "flock is POSIX only")
    def test_second_process_cannot_take_lock(self):  # concurrency
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "state.json"
            with StateStore(p):
                with self.assertRaises(StateLocked):
                    StateStore(p).acquire()
            with StateStore(p):  # released again
                pass


# --------------------------------------------------------------------------- notifier


class NotifierTests(unittest.TestCase):
    def ev(self, check="sw/snmp", event="DOWN"):
        return {"ts_utc": "2026-11-04T00:00:00Z", "check": check, "event": event, "error_code": "TIMEOUT"}

    def test_url_validation(self):  # security
        self.assertIsNone(validate_webhook_url("https://hooks.example.com/x"))
        self.assertEqual(validate_webhook_url("http://hooks.example.com/x"), "HTTPS required")
        self.assertIn("credentials", validate_webhook_url("https://u:p@hooks.example.com/x"))
        self.assertIn("control", validate_webhook_url("https://hooks.example.com/x\r\nX: y"))
        self.assertIn("not in", validate_webhook_url("https://evil.example.net/x", {"hooks.example.com"}))
        self.assertIsNone(validate_webhook_url("https://HOOKS.example.com/x", {"hooks.example.com"}))
        self.assertEqual(validate_webhook_url("ftp://x"), "HTTPS required")

    def test_cooldown_and_hourly_cap(self):
        now = [0.0]
        out = []
        n = Notifier(cooldown_s=60, max_per_hour=3, clock=lambda: now[0], printer=out.append)
        self.assertEqual(n.send(self.ev()), "printed")
        self.assertEqual(n.send(self.ev()), "suppressed")           # same key within cooldown
        self.assertEqual(n.send(self.ev(event="RECOVERED")), "printed")  # different key
        now[0] = 61
        self.assertEqual(n.send(self.ev()), "printed")
        self.assertEqual(n.send(self.ev(check="b")), "suppressed")  # hourly cap 3 reached
        now[0] = 3700
        self.assertEqual(n.send(self.ev(check="b")), "printed")
        self.assertEqual(n.suppressed, 2)

    def test_webhook_failure_never_raises_or_leaks(self):
        logutil.clear_registered_secrets()
        out = []

        class Boom:
            def open(self, *a, **k):
                raise OSError("connect to https://hooks.example.com/SECRET-TOKEN failed")

        n = Notifier.from_env({"KSSH_MONITOR_WEBHOOK": "https://hooks.example.com/SECRET-TOKEN"},
                              printer=out.append, opener=Boom())
        self.assertEqual(n.send(self.ev()), "failed:OSError")
        self.assertNotIn("SECRET-TOKEN", "".join(out))
        self.assertEqual(logutil.scrub_text("x https://hooks.example.com/SECRET-TOKEN"), "x [REDACTED]")

    def test_disallowed_host_not_contacted(self):
        called = []

        class Spy:
            def open(self, *a, **k):
                called.append(1)

        n = Notifier.from_env({"KSSH_MONITOR_WEBHOOK": "https://evil.example.net/h",
                               "KSSH_MONITOR_WEBHOOK_HOSTS": "hooks.example.com"},
                              printer=lambda m: None, opener=Spy())
        self.assertTrue(n.send(self.ev()).startswith("failed:"))
        self.assertEqual(called, [])

    def test_payload_contains_only_whitelisted_fields(self):
        bodies = []

        class Resp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self, n):
                return b""

        class Capture:
            def open(self, req, timeout):
                bodies.append(json.loads(req.data))
                return Resp()

        n = Notifier(url="https://hooks.example.com/h", printer=lambda m: None, opener=Capture())
        ev = dict(self.ev(), secret_field="nope", status="DOWN")
        self.assertEqual(n.send(ev), "sent")
        self.assertNotIn("secret_field", json.dumps(bodies[0]))
        self.assertEqual(bodies[0]["event"]["check"], "sw/snmp")

    def test_real_https_redirect_refused(self):
        """Opener used by the notifier refuses a 302 from a real local server."""
        hits = []

        class Redirect(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                hits.append(self.path)
                self.send_response(302)
                self.send_header("Location", "/second")
                self.end_headers()

            def log_message(self, *a):
                pass

        srv = http.server.HTTPServer(("127.0.0.1", 0), Redirect)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            import urllib.error
            import urllib.request
            from monitoring.notifier import WEBHOOK_OPENER
            req = urllib.request.Request(f"http://127.0.0.1:{srv.server_port}/first", data=b"{}", method="POST")
            with self.assertRaises(urllib.error.HTTPError):
                WEBHOOK_OPENER.open(req, timeout=5)
            self.assertEqual(hits, ["/first"])
        finally:
            srv.shutdown()
            srv.server_close()


# --------------------------------------------------------------------------- interface monitor


def iface(idx, name, admin=1, oper=1, err=0, lc=0, hc=0):
    return InterfaceSample(idx, {"name": name, "descr": name, "admin_status": admin, "oper_status": oper,
                                 "in_errors": err, "out_errors": 0, "in_discards": 0, "out_discards": 0,
                                 "last_change": lc, "hc_in_octets": hc, "hc_out_octets": 0, "high_speed": 10_000})


class InterfaceMonitorTests(unittest.TestCase):
    def cfg(self, **kw):
        return interface_config(kw or True)

    def test_config_validation(self):
        self.assertIsNone(interface_config(None))
        self.assertIsNone(interface_config({"enabled": False}))
        self.assertEqual(interface_config(True)["include"], ["*"])
        for bad in ({"include": "Te*"}, {"util_warn_pct": 0}, {"flap_threshold": 1}, {"max_interfaces": 9999}, 5):
            with self.assertRaises(ValueError, msg=bad):
                interface_config(bad)

    def test_selection(self):
        c = interface_config({"include": ["Te*", "eth?"], "exclude": ["Te1/0/9"]})
        self.assertTrue(selected("Te1/0/1", c))
        self.assertFalse(selected("Te1/0/9", c))
        self.assertTrue(selected("eth1", c))
        self.assertFalse(selected("Gi1/0/1", c))
        self.assertFalse(selected(None, c))

    def test_link_down_only_when_admin_up(self):
        a = DeviceSample(0, 1, {1: iface(1, "p1"), 2: iface(2, "p2", admin=2, oper=2)})
        b = DeviceSample(10, 1001, {1: iface(1, "p1", oper=2, lc=500), 2: iface(2, "p2", admin=2, oper=2)})
        checks, _ = evaluate(compute_rates(a, b), self.cfg(), {}, "sw", 10)
        self.assertEqual(checks["if:p1/link"]["status"], "DOWN")
        self.assertEqual(checks["if:p1/link"]["error_code"], "LINK_DOWN")
        self.assertNotIn("if:p2/link", checks)

    def test_error_threshold_and_baseline_unknown(self):
        a = DeviceSample(0, 1, {1: iface(1, "p1", err=0)})
        b = DeviceSample(10, 1001, {1: iface(1, "p1", err=50)})
        base, _ = evaluate(compute_rates(None, a), self.cfg(), {}, "sw", 0)
        self.assertEqual(base["if:p1/errors"]["status"], "UNKNOWN")
        checks, _ = evaluate(compute_rates(a, b), self.cfg(error_rate_per_s=1.0), {}, "sw", 10)
        self.assertEqual((checks["if:p1/errors"]["status"], checks["if:p1/errors"]["errors_per_s"]), ("DOWN", 5.0))
        ok, _ = evaluate(compute_rates(a, b), self.cfg(error_rate_per_s=10), {}, "sw", 10)
        self.assertEqual(ok["if:p1/errors"]["status"], "UP")

    def test_utilisation_is_event_not_outage(self):
        a = DeviceSample(0, 1, {1: iface(1, "p1", hc=0)})
        b = DeviceSample(10, 1001, {1: iface(1, "p1", hc=12_000_000_000)})  # 9.6 Gbit/s on 10G
        checks, events = evaluate(compute_rates(a, b), self.cfg(util_warn_pct=90), {}, "sw", 10)
        self.assertTrue(any(e["event"] == "HIGH_UTILISATION" and e["util_pct"] == 96.0 for e in events))
        self.assertTrue(all(c["status"] != "DOWN" for c in checks.values()))

    def test_flapping_across_polls_and_cleanup(self):
        flaps = {}
        samples = [DeviceSample(t, 1 + t * 100, {1: iface(1, "p1", lc=t)}) for t in range(0, 50, 10)]
        statuses = []
        for prev, cur in zip(samples, samples[1:]):
            checks, _ = evaluate(compute_rates(prev, cur), self.cfg(flap_threshold=3, flap_window_s=60), flaps,
                                 "sw", cur.taken_at)
            statuses.append(checks["if:p1/flap"]["status"])
        self.assertEqual(statuses, ["UP", "UP", "DOWN", "DOWN"])
        gone = DeviceSample(60, 9000, {2: iface(2, "p2")})
        evaluate(compute_rates(samples[-1], gone), self.cfg(), flaps, "sw", 60)
        self.assertNotIn("sw/p1", flaps)

    def test_sample_persistence_round_trip_and_malformed(self):
        s = DeviceSample(5.0, 77, {1: iface(1, "p1"), 2: InterfaceSample(2, {"name": "x", "alias": NO_SUCH})})
        back = sample_from_dict(json.loads(json.dumps(sample_to_dict(s))))
        self.assertEqual(back.interfaces[1].data, s.interfaces[1].data)
        self.assertNotIn("alias", back.interfaces[2].data)
        for bad in (None, {}, {"taken_at": "x", "interfaces": {}}, {"taken_at": 1, "interfaces": {"a": {}}},
                    {"taken_at": 1, "interfaces": {"1": "str"}}):
            self.assertIsNone(sample_from_dict(bad), bad)

    def test_interface_limit(self):
        many = DeviceSample(0, 1, {i: iface(i, f"p{i}") for i in range(1, 11)})
        checks, events = evaluate(compute_rates(None, many), self.cfg(max_interfaces=3), {}, "sw", 0)
        self.assertEqual(len({k.split("/")[0] for k in checks}), 3)
        self.assertTrue(any(e["event"] == "INTERFACE_LIMIT" for e in events))


# --------------------------------------------------------------------------- engine end-to-end


class EngineTests(unittest.TestCase):
    def config(self, tmp, **extra):
        cfg = {"allowed_networks": ["127.0.0.1"], "failure_threshold": 2, "recovery_threshold": 1,
               "targets": [{"name": "sw", "host": "127.0.0.1", "snmp": SNMP,
                            "interfaces": {"include": ["Te*"], "error_rate_per_s": 1.0}}]}
        cfg.update(extra)
        return load(tmp, cfg)

    def test_interfaces_end_to_end_with_persisted_baseline(self):
        agent = FakeAgent(switch_mib(1000, {1: ("Te1", 1, 1, 0, 0, 0, 5), 2: ("Gi1", 1, 2, 0, 0, 0, 5)}))
        notifier = RecordingNotifier()
        t = [100.0]
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, ENV), quiet():
            config = self.config(tmp)
            store = StateStore(Path(tmp) / "state.json")
            state = store.load()
            r1 = asyncio.run(monitor.poll(config, state, backend_factory=lambda _: agent,
                                          notifier=notifier, clock=lambda: t[0]))
            self.assertEqual(r1[0]["checks"]["if:Te1/errors"]["status"], "UNKNOWN")  # baseline
            self.assertNotIn("if:Gi1/link", r1[0]["checks"])  # excluded by include pattern
            store.save(state)

            # restart: new state object loaded from disk, counters moved, link went down
            state = StateStore(Path(tmp) / "state.json").load()
            agent.mib = switch_mib(2000, {1: ("Te1", 1, 2, 125_000_000, 0, 30, 900),
                                          2: ("Gi1", 1, 2, 0, 0, 0, 5)})
            t[0] = 110.0
            r2 = asyncio.run(monitor.poll(config, state, backend_factory=lambda _: agent,
                                          notifier=notifier, clock=lambda: t[0]))
            iface2 = r2[0]["interfaces"][1]
            self.assertEqual(iface2["rates"]["in_bps"], 100_000_000.0)  # 125 MB in 10 s
            self.assertEqual(r2[0]["checks"]["if:Te1/errors"]["errors_per_s"], 3.0)
            t[0] = 120.0
            agent.mib = switch_mib(3000, {1: ("Te1", 1, 2, 125_000_000, 0, 60, 900)})
            asyncio.run(monitor.poll(config, state, backend_factory=lambda _: agent,
                                     notifier=notifier, clock=lambda: t[0]))
        downs = sorted(e["check"] for e in notifier.events if e["event"] == "DOWN")
        self.assertEqual(downs, ["sw/if:Te1/errors", "sw/if:Te1/link"])
        self.assertEqual(state["checks"]["sw/if:Te1/link"]["healthy"], False)
        self.assertIn("since_utc", state["checks"]["sw/if:Te1/link"])

    def test_interface_collection_failure_does_not_alert(self):
        class HealthOnly(FakeAgent):
            async def getbulk(self, *a):
                raise MonitorError(ErrorCode.LIMIT_EXCEEDED)

        agent = HealthOnly(switch_mib(1, {}))
        notifier = RecordingNotifier()
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, ENV), quiet():
            config = self.config(tmp, failure_threshold=1)
            state = {}
            r = asyncio.run(monitor.poll(config, state, backend_factory=lambda _: agent, notifier=notifier))
        self.assertEqual(r[0]["interfaces_error"], "LIMIT_EXCEEDED")
        self.assertEqual(notifier.events, [])

    def test_hanging_target_hits_deadline_without_blocking_others(self):  # timeout + concurrency
        slow = FakeAgent(switch_mib(1, {}), delay=30)
        fast = FakeAgent(switch_mib(1, {}))
        cfg = {"allowed_networks": ["127.0.0.1"], "failure_threshold": 1, "target_deadline_seconds": 5,
               "targets": [{"name": "slow", "host": "127.0.0.1", "snmp": SNMP},
                           {"name": "fast", "host": "127.0.0.1", "snmp": SNMP}]}
        notifier = RecordingNotifier()
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, ENV), quiet():
            config = load(tmp, cfg)
            config["target_deadline_seconds"] = 0.3  # shorten below the config minimum for the test

            async def go():
                loop = asyncio.get_running_loop()
                t0 = loop.time()
                res = await monitor.poll(config, {}, notifier=notifier,
                                         backend_factory=lambda t: slow if t["name"] == "slow" else fast)
                return res, loop.time() - t0

            res, elapsed = asyncio.run(go())
        by = {r["name"]: r for r in res}
        self.assertLess(elapsed, 2)
        self.assertEqual(by["slow"]["checks"]["snmp"]["error_code"], "DEADLINE_EXCEEDED")
        self.assertEqual(by["slow"]["checks"]["snmp"]["status"], "UNKNOWN")
        self.assertEqual(by["fast"]["checks"]["snmp"]["status"], "UP")
        self.assertEqual(notifier.events, [])  # our deadline is not a device outage
        self.assertEqual(slow.active, 0)       # cancelled cleanly

    def test_poll_respects_max_concurrency(self):  # concurrency
        agents = []

        class Shared:
            active = 0
            peak = 0

        class Counting(FakeAgent):
            async def _enter(self):
                Shared.active += 1
                Shared.peak = max(Shared.peak, Shared.active)
                try:
                    await asyncio.sleep(0.05)
                finally:
                    Shared.active -= 1

        cfg = {"allowed_networks": ["127.0.0.1"], "max_concurrency": 2,
               "targets": [{"name": f"t{i}", "host": "127.0.0.1", "snmp": SNMP} for i in range(6)]}
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, ENV), quiet():
            config = load(tmp, cfg)

            def factory(t):
                a = Counting(switch_mib(1, {}))
                agents.append(a)
                return a
            asyncio.run(monitor.poll(config, {}, backend_factory=factory, notifier=RecordingNotifier()))
        self.assertEqual(Shared.peak, 2)
        self.assertEqual(len(agents), 6)

    def test_removed_target_sample_forgotten(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, ENV), quiet():
            config = self.config(tmp)
            state = empty_state()
            state["samples"]["old-switch"] = {"taken_at": 1, "interfaces": {}}
            asyncio.run(monitor.poll(config, state, backend_factory=lambda _: FakeAgent(switch_mib(1, {})),
                                     notifier=RecordingNotifier()))
        self.assertNotIn("old-switch", state["samples"])
        self.assertIn("sw", state["samples"])

    def test_corrupt_persisted_sample_treated_as_baseline(self):  # regression / robustness
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, ENV), quiet():
            config = self.config(tmp)
            state = empty_state()
            state["samples"]["sw"] = {"taken_at": "garbage"}
            r = asyncio.run(monitor.poll(config, state, notifier=RecordingNotifier(),
                                         backend_factory=lambda _: FakeAgent(switch_mib(1, {1: ("Te1", 1, 1, 0, 0, 0, 0)}))))
        self.assertEqual(r[0]["interfaces"][1]["events"], ["BASELINE"])


# --------------------------------------------------------------------------- config security


class ConfigSecurityTests(unittest.TestCase):
    def test_rejects_unsafe_inventory(self):
        cases = [
            ({"allowed_networks": ["127.0.0.1"], "targets": [{"name": "a/b", "host": "127.0.0.1", "tcp_port": 1}]}, "name"),
            ({"allowed_networks": ["127.0.0.1"], "targets": [{"name": "x" * 65, "host": "127.0.0.1", "tcp_port": 1}]}, "name"),
            ({"allowed_networks": ["127.0.0.1"],
              "targets": [{"name": f"t{i}", "host": "127.0.0.1", "tcp_port": 1} for i in range(257)]}, "256"),
            ({"allowed_networks": ["127.0.0.1"],
              "targets": [{"name": "t", "host": "127.0.0.1", "tcp_port": 1, "interfaces": True}]}, "requires snmp"),
            ({"allowed_networks": ["0.0.0.0/0"], "targets": "x"}, "targets"),
            ([], "object"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            for cfg, msg in cases:
                with self.assertRaisesRegex(ValueError, msg):
                    load(tmp, cfg)

    def test_allowlist_not_bypassed_by_alternate_spellings(self):
        al = Allowlist(["192.168.30.10/32"])
        for host in ("::ffff:192.168.30.10", "192.168.030.010", "0xc0a81e0a", "3232243210",
                     "192.168.30.10.", "192.168.30.10 ", "192.168.30.10/32"):
            self.assertFalse(al.allows(host), host)
        self.assertTrue(al.allows("192.168.30.10"))


# --------------------------------------------------------------------------- main()


class MainTests(unittest.TestCase):
    def test_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp, quiet(), redirect_stdout(io.StringIO()):
            bad = Path(tmp) / "bad.json"
            bad.write_text("{}")
            self.assertEqual(monitor.main(["--config", str(bad), "--state", str(Path(tmp) / "s.json"), "--once"]), 2)
            good = Path(tmp) / "good.json"
            good.write_text(json.dumps({"allowed_networks": ["127.0.0.1"],
                                        "targets": [{"name": "local", "host": "127.0.0.1", "tcp_port": 9}]}))
            state = Path(tmp) / "s.json"
            if os.name == "posix":
                with StateStore(state):
                    self.assertEqual(monitor.main(["--config", str(good), "--state", str(state), "--once"]), 3)
            # v1 state from the first MVP still loads (regression)
            state.write_text(json.dumps({"local/tcp": {"healthy": True, "pending": 0, "seen": True}}))
            self.assertEqual(monitor.main(["--config", str(good), "--state", str(state), "--once"]), 0)
            saved = json.loads(state.read_text())
            self.assertEqual(saved["schema"], 2)
            self.assertEqual(saved["checks"]["local/tcp"]["pending"], 1)  # closed port 9: first failure


if __name__ == "__main__":
    unittest.main()
