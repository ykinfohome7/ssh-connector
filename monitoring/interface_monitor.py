"""Turn interface samples into monitor checks (10GbE ports and others).

Checks produced per selected interface (key ``<target>/if:<name>/<check>``):

* ``link``   - DOWN when the port is administratively up but operationally
  not up. Admin-down ports are skipped (an intentionally disabled port is
  not an outage).
* ``errors`` - DOWN when in/out errors+discards per second exceed the
  configured threshold. UNKNOWN when no rate is available this cycle
  (baseline, reboot, counter discontinuity).
* ``flap``   - DOWN while the link changed state at least ``flap_threshold``
  times inside ``flap_window_s``.

Utilisation above ``util_warn_pct`` is reported as an event in the poll
output, not as a DOWN state: high load is not an outage.
"""
from __future__ import annotations

import fnmatch
from typing import Any

from .errors import ErrorCode
from .snmp_client import END_OF_MIB, NO_SUCH
from .snmp_interfaces import DeviceSample, InterfaceSample

DEFAULTS = {
    "include": ["*"],
    "exclude": [],
    "error_rate_per_s": 1.0,
    "util_warn_pct": 90.0,
    "flap_threshold": 3,
    "flap_window_s": 600,
    "max_interfaces": 128,
}


def interface_config(raw: Any) -> dict | None:
    """Validate the per-target ``interfaces`` section. None = disabled."""
    if raw in (None, False):
        return None
    if raw is True:
        raw = {}
    if not isinstance(raw, dict):
        raise ValueError("interfaces must be true or an object")
    if raw.get("enabled") is False:
        return None
    cfg = dict(DEFAULTS)
    for key in ("include", "exclude"):
        if key in raw:
            value = raw[key]
            if not isinstance(value, list) or not all(isinstance(p, str) and 0 < len(p) <= 64 for p in value):
                raise ValueError(f"interfaces.{key} must be a list of short patterns")
            cfg[key] = value
    for key, lo, hi in (("error_rate_per_s", 0.0, 1e6), ("util_warn_pct", 1.0, 100.0),
                        ("flap_threshold", 2, 100), ("flap_window_s", 30, 86400),
                        ("max_interfaces", 1, 512)):
        if key in raw:
            value = float(raw[key])
            if not lo <= value <= hi:
                raise ValueError(f"interfaces.{key} must be {lo}..{hi}")
            cfg[key] = int(value) if isinstance(DEFAULTS[key], int) else value
    return cfg


def selected(name: str | None, cfg: dict) -> bool:
    if not name:
        return False
    if not any(fnmatch.fnmatchcase(name, p) for p in cfg["include"]):
        return False
    return not any(fnmatch.fnmatchcase(name, p) for p in cfg["exclude"])


# --------------------------------------------------------------------------- persistence

def _jsonable(value):
    if value is NO_SUCH or value is END_OF_MIB:
        return None
    return value


def sample_to_dict(sample: DeviceSample) -> dict:
    return {
        "taken_at": sample.taken_at,
        "sys_uptime_ticks": sample.sys_uptime_ticks,
        "interfaces": {str(i): {k: _jsonable(v) for k, v in s.data.items()}
                       for i, s in sample.interfaces.items()},
    }


def sample_from_dict(raw: Any) -> DeviceSample | None:
    """Rebuild a sample from state; return None for anything malformed."""
    try:
        interfaces = {}
        for idx, data in raw["interfaces"].items():
            if not isinstance(data, dict):
                return None
            clean = {str(k): v for k, v in data.items() if v is None or isinstance(v, (int, float, str))}
            interfaces[int(idx)] = InterfaceSample(int(idx), {k: v for k, v in clean.items() if v is not None})
        up = raw.get("sys_uptime_ticks")
        return DeviceSample(float(raw["taken_at"]), up if isinstance(up, int) else None, interfaces)
    except (KeyError, TypeError, ValueError, AttributeError):
        return None


# --------------------------------------------------------------------------- evaluation

def _check(ok: bool | None, code: ErrorCode | None = None, **data) -> dict:
    if ok is None:
        status = "UNKNOWN"
    else:
        status = "UP" if ok else "DOWN"
    out = {"ok": bool(ok), "status": status, "error_code": code.value if code else None}
    out.update(data)
    return out


def evaluate(rates: dict, cfg: dict, flaps: dict, target: str, now: float) -> tuple[dict, list[dict]]:
    """Return (checks, events). ``flaps`` is the persisted flap history (mutated)."""
    checks: dict[str, dict] = {}
    events: list[dict] = []
    count = 0
    for idx, entry in sorted(rates["interfaces"].items()):
        name = entry.get("name")
        if not selected(name, cfg):
            continue
        count += 1
        if count > cfg["max_interfaces"]:
            events.append({"event": "INTERFACE_LIMIT", "detail": f"more than {cfg['max_interfaces']} selected"})
            break
        prefix = f"if:{name}"
        admin, oper = entry.get("admin_status"), entry.get("oper_status")

        if admin == "up":
            if oper is None:
                checks[f"{prefix}/link"] = _check(None, ErrorCode.UNAVAILABLE, if_index=idx)
            else:
                checks[f"{prefix}/link"] = _check(oper == "up", None if oper == "up" else ErrorCode.LINK_DOWN,
                                                  if_index=idx, oper_status=oper)

        r = entry.get("rates")
        if r is None:
            checks[f"{prefix}/errors"] = _check(None, ErrorCode.UNAVAILABLE, reason=",".join(entry["events"]) or None)
        else:
            parts = [r.get(k) for k in ("in_errors_per_s", "out_errors_per_s", "in_discards_per_s", "out_discards_per_s")]
            known = [p for p in parts if p is not None]
            if not known:
                checks[f"{prefix}/errors"] = _check(None, ErrorCode.UNAVAILABLE)
            else:
                rate = round(sum(known), 4)
                bad = rate > cfg["error_rate_per_s"]
                checks[f"{prefix}/errors"] = _check(not bad, ErrorCode.THRESHOLD_EXCEEDED if bad else None,
                                                    errors_per_s=rate)
            for direction in ("in", "out"):
                util = r.get(f"{direction}_util_pct")
                if util is not None and util >= cfg["util_warn_pct"]:
                    events.append({"event": "HIGH_UTILISATION", "interface": name,
                                   "direction": direction, "util_pct": util})

        # flapping, history persisted across restarts
        fkey = f"{target}/{name}"
        history = [t for t in flaps.get(fkey, []) if isinstance(t, (int, float)) and now - t <= cfg["flap_window_s"]]
        if "LINK_STATE_CHANGED" in entry["events"]:
            history.append(now)
        flaps[fkey] = history[-100:]
        flapping = len(history) >= cfg["flap_threshold"]
        checks[f"{prefix}/flap"] = _check(not flapping, ErrorCode.THRESHOLD_EXCEEDED if flapping else None,
                                          changes_in_window=len(history))
        for ev in entry["events"]:
            if ev in {"REBOOT_OR_UPTIME_WRAP", "COUNTER_DISCONTINUITY", "IFINDEX_REASSIGNED", "SPEED_CHANGED"}:
                events.append({"event": ev, "interface": name, "if_index": idx})
    for ev in rates.get("device_events", []):
        events.append({"event": ev})
    # drop flap history of interfaces that no longer exist for this target
    present = {f"{target}/{e.get('name')}" for e in rates["interfaces"].values()}
    for fkey in [k for k in flaps if k.startswith(f"{target}/") and k not in present]:
        del flaps[fkey]
    return checks, events
