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
import socket
import sys
import time
import urllib.request
from pathlib import Path

if __package__ in (None, ""):  # executed as a script: make the package importable
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "monitoring"

from .errors import CheckStatus, ErrorCode, MonitorError, status_for  # noqa: E402
from .logutil import get_logger, log_event, new_correlation_id  # noqa: E402
from .snmp_adapters import make_adapter  # noqa: E402
from .snmp_client import Allowlist, SnmpClient, SnmpCredentials, SnmpLimits, SnmpTarget  # noqa: E402

LOG = get_logger()


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
    names = set()
    for target in targets:
        if not isinstance(target, dict):
            raise ValueError("each target must be an object")
        name = target.get("name", "")
        if not name or name in names:
            raise ValueError("each target needs a distinct name")
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
    config["interval_seconds"] = max(15, int(config.get("interval_seconds", 60)))
    config["failure_threshold"] = max(1, int(config.get("failure_threshold", 3)))
    config["recovery_threshold"] = max(1, int(config.get("recovery_threshold", 2)))
    config["max_concurrency"] = max(1, min(16, int(config.get("max_concurrency", 4))))
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


async def snmp_probe(host: str, cfg: dict, allowlist: Allowlist | None = None, *, backend=None) -> dict:
    """Authenticated SNMP GET of sysUpTime.0 / sysName.0 - never SNMP SET.

    Returns {"ok", "status" (UP/DOWN/UNKNOWN), "error_code", ...}. Problems
    with our own setup (missing pysnmp, missing secret, bad config) yield
    UNKNOWN, which never raises a DOWN alert for the device.
    """
    try:
        creds = SnmpCredentials.from_config(cfg)
        target = SnmpTarget(host, int(cfg.get("port", 161)),
                            float(cfg.get("timeout", 2.0)), int(cfg.get("retries", 1)))
        client = SnmpClient(target, creds, allowlist or Allowlist([host]),
                            limits=SnmpLimits(max_concurrency=1), backend=backend)
        health = await make_adapter(cfg.get("adapter", "generic"), client).health()
        return _result(None, uptime_ticks=health["sys_uptime_ticks"], sys_name=health["sys_name"])
    except MonitorError as exc:
        return _result(exc.code, exc.message)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        return _result(ErrorCode.INTERNAL, type(exc).__name__)


# --------------------------------------------------------------------------- state


def update_state(state: dict, key: str, ok: bool | None, bad_after: int, good_after: int) -> str | None:
    """Debounced transition. ``ok=None`` (UNKNOWN) leaves the state untouched.

    Returns "DOWN", "RECOVERED" or None.
    """
    entry = state.setdefault(key, {"healthy": True, "pending": 0})
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
    return "RECOVERED" if ok else "DOWN"


def save_state(path: Path, state: dict) -> None:
    """Atomic, private (0600), fsync'ed state write."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    fd = os.open(tmp, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as file:
        json.dump(state, file, sort_keys=True)
        file.flush()
        os.fsync(file.fileno())
    os.replace(tmp, path)
    try:
        dir_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except OSError:
        pass  # not supported on every platform/filesystem


# --------------------------------------------------------------------------- notify


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse all redirects so an HTTPS webhook can never be downgraded."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_WEBHOOK_OPENER = urllib.request.build_opener(_NoRedirect)


def notify(message: str) -> None:
    """Optional HTTPS webhook; no public listener, never print URL/token."""
    print(message, flush=True)
    url = os.environ.get("KSSH_MONITOR_WEBHOOK")
    if not url:
        return
    if not url.startswith("https://"):
        print("Webhook skipped: HTTPS required", flush=True)
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


async def _check_target(target: dict, allowlist: Allowlist, sem: asyncio.Semaphore, backend_factory) -> dict:
    async with sem:
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
        return record


async def poll(config: dict, state: dict, *, backend_factory=None) -> list[dict]:
    """Check all targets concurrently (bounded), then apply state transitions in order."""
    allowlist = config.get("_allowlist") or Allowlist(config.get("allowed_networks") or [])
    sem = asyncio.Semaphore(config.get("max_concurrency", 4))
    cid = new_correlation_id()
    records = await asyncio.gather(*(
        _check_target(t, allowlist, sem, backend_factory) for t in config["targets"]
    ))
    for record in records:
        for check, res in record["checks"].items():
            key = f"{record['name']}/{check}"
            status = res["status"]
            ok = None if status == CheckStatus.UNKNOWN.value else status == CheckStatus.UP.value
            if ok is None:
                log_event(LOG, logging.WARNING, "check could not be evaluated",
                          check=key, error_code=res.get("error_code"), correlation_id=cid)
            event = update_state(state, key, ok, config["failure_threshold"], config["recovery_threshold"])
            if event:
                log_event(LOG, logging.ERROR if event == "DOWN" else logging.INFO, "state transition",
                          check=key, event=event, error_code=res.get("error_code"), correlation_id=cid)
                notify(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} KSSH monitor {event}: {key}"
                       + (f" ({res['error_code']})" if res.get("error_code") else ""))
    return list(records)


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only infrastructure monitor")
    parser.add_argument("--config", default=str(Path(__file__).with_name("targets.example.json")))
    parser.add_argument("--state", default=str(Path.home() / ".local/state/kssh-monitor.json"))
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    config = load_config(Path(args.config))
    state_path = Path(args.state)
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        state = {}
    while True:
        result = asyncio.run(poll(config, state))
        print(json.dumps({"time": int(time.time()), "targets": result}, sort_keys=True), flush=True)
        try:
            save_state(state_path, state)
        except OSError as exc:
            log_event(LOG, logging.ERROR, "state save failed", exc_type=type(exc).__name__)
        if args.once:
            break
        time.sleep(config["interval_seconds"])


if __name__ == "__main__":
    main()
