"""Read-only switch and Proxmox reachability monitor for KSSH.

Run:   python3 -m monitoring.monitor --once --config monitoring/targets.example.json
(``python3 monitoring/monitor.py`` also works.)

Requires pysnmp>=7.1,<8 only for SNMP probes. No host modifications, no SNMP
SET, no credential logging, no public listeners.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import signal
import socket
import sys
import threading
import time
import urllib.request
from pathlib import Path

if __package__ in (None, ""):  # executed as a script: make the package importable
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "monitoring"

from .errors import CheckStatus, ErrorCode, MonitorError, status_for  # noqa: E402
from .interface_monitor import evaluate, interface_config, sample_from_dict, sample_to_dict  # noqa: E402
from .logutil import get_logger, log_event, new_correlation_id  # noqa: E402
from .notifier import WEBHOOK_OPENER, Notifier, _NoRedirect, validate_webhook_url  # noqa: E402,F401
from .snmp_adapters import make_adapter  # noqa: E402
from .snmp_client import Allowlist, SnmpClient, SnmpCredentials, SnmpLimits, SnmpTarget  # noqa: E402
from .snmp_interfaces import collect_sample, compute_rates  # noqa: E402
from .state_store import StateLocked, StateStore, empty_state, migrate, write_private_atomic  # noqa: E402

LOG = get_logger()
_WEBHOOK_OPENER = WEBHOOK_OPENER  # backwards-compatible name


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# --------------------------------------------------------------------------- config


def load_config(path: Path) -> dict:
    """Load and validate the inventory. Raises ValueError with a safe message."""
    config = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError("config must be a JSON object")
    try:
        allowlist = Allowlist(config.get("allowed_networks") or [])
    except MonitorError as exc:
        raise ValueError(f"allowed_networks: {exc.message}") from None
    targets = config.get("targets")
    if not isinstance(targets, list) or not targets:
        raise ValueError("targets must be a nonempty list")
    if len(targets) > 256:
        raise ValueError("at most 256 targets")
    names = set()
    for target in targets:
        if not isinstance(target, dict):
            raise ValueError("each target must be an object")
        name = target.get("name", "")
        if not isinstance(name, str) or not name or name in names or len(name) > 64 or "/" in name:
            raise ValueError("each target needs a distinct name (1..64 chars, no '/')")
        names.add(name)
        host = target.get("host")
        if not host:
            raise ValueError("target requires host")
        if not allowlist.allows(str(host)):
            raise ValueError(f"target {name}: host is not in allowed_networks")
        has_tcp = "tcp_port" in target
        if has_tcp:
            port = int(target["tcp_port"])
            if not 1 <= port <= 65535:
                raise ValueError("tcp_port must be 1..65535")
        if target.get("snmp"):
            try:
                SnmpCredentials.from_config(target["snmp"])
                snmp = target["snmp"]
                SnmpTarget(str(host), int(snmp.get("port", 161)),
                           float(snmp.get("timeout", 2.0)), int(snmp.get("retries", 1)))
            except MonitorError as exc:
                raise ValueError(f"target {name}: {exc.message}") from None
        elif not has_tcp:
            raise ValueError(f"target {name}: needs tcp_port and/or snmp")
        try:
            target["_interfaces"] = interface_config(target.get("interfaces"))
        except ValueError as exc:
            raise ValueError(f"target {name}: {exc}") from None
        if target["_interfaces"] and not target.get("snmp"):
            raise ValueError(f"target {name}: interfaces monitoring requires snmp")
    config["interval_seconds"] = max(15, int(config.get("interval_seconds", 60)))
    config["failure_threshold"] = max(1, int(config.get("failure_threshold", 3)))
    config["recovery_threshold"] = max(1, int(config.get("recovery_threshold", 2)))
    config["max_concurrency"] = max(1, min(16, int(config.get("max_concurrency", 4))))
    config["target_deadline_seconds"] = max(5, min(300, int(config.get("target_deadline_seconds", 60))))
    config["_allowlist"] = allowlist
    return config


# --------------------------------------------------------------------------- probes


def tcp_probe(host: str, port: int, timeout: float = 3) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, TimeoutError):
        return False


def _result(code: ErrorCode | None, detail: str = "", **data) -> dict:
    status = status_for(code)
    out = {"ok": status is CheckStatus.UP, "status": status.value,
           "error_code": code.value if code else None}
    if detail:
        out["detail"] = detail
    out.update(data)
    return out


def make_client(host: str, cfg: dict, allowlist: Allowlist | None, backend=None) -> SnmpClient:
    creds = SnmpCredentials.from_config(cfg)
    target = SnmpTarget(host, int(cfg.get("port", 161)),
                        float(cfg.get("timeout", 2.0)), int(cfg.get("retries", 1)))
    return SnmpClient(target, creds, allowlist or Allowlist([host]),
                      limits=SnmpLimits(max_concurrency=1), backend=backend)


async def snmp_probe(host: str, cfg: dict, allowlist: Allowlist | None = None, *, backend=None) -> dict:
    """Authenticated SNMP GET of sysUpTime.0 / sysName.0 - never SNMP SET.

    Returns {"ok", "status" (UP/DOWN/UNKNOWN), "error_code", ...}. Problems
    with our own setup (missing pysnmp, missing secret, bad config) yield
    UNKNOWN, which never raises a DOWN alert for the device.
    """
    try:
        client = make_client(host, cfg, allowlist, backend)
        health = await make_adapter(cfg.get("adapter", "generic"), client).health()
        return _result(None, uptime_ticks=health["sys_uptime_ticks"], sys_name=health["sys_name"])
    except MonitorError as exc:
        return _result(exc.code, exc.message)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        return _result(ErrorCode.INTERNAL, type(exc).__name__)


# --------------------------------------------------------------------------- state


def update_state(checks: dict, key: str, ok: bool | None, bad_after: int, good_after: int) -> str | None:
    """Debounced transition on one check. ``ok=None`` (UNKNOWN) changes nothing.

    Returns "DOWN", "RECOVERED" or None.
    """
    entry = checks.setdefault(key, {"healthy": True, "pending": 0})
    entry.pop("seen", None)  # legacy field from the first MVP
    entry.setdefault("pending", 0)
    entry.setdefault("healthy", True)
    if ok is None:
        return None
    if ok == entry["healthy"]:
        entry["pending"] = 0
        return None
    entry["pending"] += 1
    threshold = good_after if ok else bad_after
    if entry["pending"] < threshold:
        return None
    entry["healthy"] = ok
    entry["pending"] = 0
    entry["since_utc"] = utc_now()
    return "RECOVERED" if ok else "DOWN"


def save_state(path: Path, state: dict) -> None:
    """Atomic, private (0600), fsync'ed state write (kept for compatibility)."""
    write_private_atomic(Path(path), state)


def _ensure_v2(state: dict) -> dict:
    if state.get("schema") != 2:
        migrated = migrate(state) if state else empty_state()
        state.clear()
        state.update(migrated)
    return state


# --------------------------------------------------------------------------- notify (legacy helper)


def notify(message: str) -> None:
    """Print a message and POST it to KSSH_MONITOR_WEBHOOK (HTTPS, no redirects)."""
    print(message, flush=True)
    url = os.environ.get("KSSH_MONITOR_WEBHOOK")
    if not url:
        return
    reason = validate_webhook_url(url)
    if reason:
        print(f"Webhook skipped: {reason}", flush=True)
        return
    try:
        request = urllib.request.Request(
            url, data=json.dumps({"text": message}).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with _WEBHOOK_OPENER.open(request, timeout=5) as response:
            response.read(256)
    except Exception:
        print("Webhook delivery failed (details hidden)", flush=True)


# --------------------------------------------------------------------------- poll


async def _run_checks(target: dict, allowlist: Allowlist, backend_factory, prev_sample, clock) -> dict:
    name, host = target["name"], target["host"]
    record: dict = {"name": name, "checks": {}}
    if "tcp_port" in target:
        ok = await asyncio.to_thread(tcp_probe, host, int(target["tcp_port"]))
        record["tcp_ok"] = ok
        record["checks"]["tcp"] = _result(None if ok else ErrorCode.UNREACHABLE)
    if target.get("snmp"):
        backend = backend_factory(target) if backend_factory else None
        snmp = await snmp_probe(host, target["snmp"], allowlist, backend=backend)
        record["snmp_ok"] = snmp["ok"]
        record["snmp"] = snmp
        record["checks"]["snmp"] = snmp
        if target.get("_interfaces") and snmp["ok"]:
            try:
                client = make_client(host, target["snmp"], allowlist, backend)
                sample = await collect_sample(client, clock(), max_interfaces=target["_interfaces"]["max_interfaces"] * 4)
                record["_sample"] = sample
                record["_rates"] = compute_rates(prev_sample, sample)
            except MonitorError as exc:
                record["interfaces_error"] = exc.code.value
    return record


async def _check_target(target, allowlist, sem, backend_factory, prev_sample, deadline, clock) -> dict:
    async with sem:
        try:
            return await asyncio.wait_for(
                _run_checks(target, allowlist, backend_factory, prev_sample, clock), timeout=deadline)
        except asyncio.TimeoutError:
            planned = (["tcp"] if "tcp_port" in target else []) + (["snmp"] if target.get("snmp") else [])
            return {"name": target["name"], "deadline_exceeded": True,
                    "checks": {c: _result(ErrorCode.DEADLINE_EXCEEDED, f"no result within {deadline}s")
                               for c in planned}}


async def poll(config: dict, state: dict, *, backend_factory=None, notifier: Notifier | None = None,
               clock=time.time) -> list[dict]:
    """Check all targets concurrently (bounded), then apply state transitions in order.

    ``state`` is the v2 state dict (an empty dict is accepted and initialised).
    """
    _ensure_v2(state)
    allowlist = config.get("_allowlist") or Allowlist(config.get("allowed_networks") or [])
    sem = asyncio.Semaphore(config.get("max_concurrency", 4))
    deadline = config.get("target_deadline_seconds", 60)
    cid = new_correlation_id()
    prev = {t["name"]: sample_from_dict(state["samples"].get(t["name"])) if state["samples"].get(t["name"]) else None
            for t in config["targets"]}
    records = await asyncio.gather(*(
        _check_target(t, allowlist, sem, backend_factory, prev[t["name"]], deadline, clock)
        for t in config["targets"]
    ))
    if notifier is None:
        notifier = Notifier.from_env(printer=lambda m: notify_print(m))
    by_name = {t["name"]: t for t in config["targets"]}
    for record in records:
        name = record["name"]
        sample = record.pop("_sample", None)
        rates = record.pop("_rates", None)
        if sample is not None:
            state["samples"][name] = sample_to_dict(sample)
            if_checks, if_events = evaluate(rates, by_name[name]["_interfaces"], state["flaps"], name, clock())
            record["checks"].update(if_checks)
            record["interface_events"] = if_events
            record["interfaces"] = rates["interfaces"]
            for ev in if_events:
                log_event(LOG, logging.INFO, "interface event", target=name, correlation_id=cid, **ev)
        if record.get("deadline_exceeded"):
            log_event(LOG, logging.ERROR, "target deadline exceeded", target=name, correlation_id=cid)
        if record.get("interfaces_error"):
            log_event(LOG, logging.WARNING, "interface collection failed", target=name,
                      error_code=record["interfaces_error"], correlation_id=cid)
        for check, res in record["checks"].items():
            key = f"{name}/{check}"
            status = res["status"]
            ok = None if status == CheckStatus.UNKNOWN.value else status == CheckStatus.UP.value
            if ok is None and check in ("tcp", "snmp"):
                log_event(LOG, logging.WARNING, "check could not be evaluated",
                          check=key, error_code=res.get("error_code"), correlation_id=cid)
            event = update_state(state["checks"], key, ok, config["failure_threshold"], config["recovery_threshold"])
            if event:
                log_event(LOG, logging.ERROR if event == "DOWN" else logging.INFO, "state transition",
                          check=key, event=event, error_code=res.get("error_code"), correlation_id=cid)
                notifier.send({"ts_utc": utc_now(), "check": key, "event": event,
                               "error_code": res.get("error_code"), "status": status})
    # forget samples of targets removed from the config
    for stale in set(state["samples"]) - set(by_name):
        del state["samples"][stale]
    return list(records)


def notify_print(message: str) -> None:
    print(message, flush=True)


# --------------------------------------------------------------------------- main


def run(config: dict, store: StateStore, *, once: bool, stop: threading.Event) -> int:
    state = store.load()
    if store.recovered_from:
        log_event(LOG, logging.ERROR, "state file was unreadable; moved aside and started fresh",
                  moved_to=store.recovered_from)
    notifier = Notifier.from_env(printer=notify_print)
    while not stop.is_set():
        try:
            result = asyncio.run(poll(config, state, notifier=notifier))
        except KeyboardInterrupt:  # asyncio.run turns SIGINT into this; keep the last good state
            break
        print(json.dumps({"time_utc": utc_now(), "targets": result}, sort_keys=True, default=str), flush=True)
        try:
            store.save(state)
        except OSError as exc:
            log_event(LOG, logging.ERROR, "state save failed", exc_type=type(exc).__name__)
        if once:
            break
        stop.wait(config["interval_seconds"])
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only infrastructure monitor")
    parser.add_argument("--config", default=str(Path(__file__).with_name("targets.example.json")))
    parser.add_argument("--state", default=str(Path.home() / ".local/state/kssh-monitor.json"))
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args(argv)
    try:
        config = load_config(Path(args.config))
    except (OSError, ValueError) as exc:
        log_event(LOG, logging.ERROR, "invalid configuration", detail=str(exc))
        return 2
    stop = threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            signal.signal(sig, lambda *_: stop.set())
        except (ValueError, OSError):
            pass  # not in main thread / unsupported platform
    try:
        with StateStore(Path(args.state)) as store:
            return run(config, store, once=args.once, stop=stop)
    except StateLocked as exc:
        log_event(LOG, logging.ERROR, str(exc))
        return 3


if __name__ == "__main__":
    sys.exit(main())
