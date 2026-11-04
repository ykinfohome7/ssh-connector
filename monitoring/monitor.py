"""Read-only switch and Proxmox reachability monitor for KSSH (MVP).

Requires: pip install pysnmp>=7.1,<8 for SNMP probes.
No host modifications, no credential logging, no public listeners.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import socket
import time
import urllib.request
from pathlib import Path


def load_config(path: Path) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(config.get("targets"), list) or not config["targets"]:
        raise ValueError("targets must be a nonempty list")
    names = set()
    for target in config["targets"]:
        name = target.get("name", "")
        if not name or name in names:
            raise ValueError("each target needs a distinct name")
        names.add(name)
        if not target.get("host"):
            raise ValueError("target requires host")
        port = int(target.get("tcp_port", 0))
        if not 1 <= port <= 65535:
            raise ValueError("tcp_port must be 1..65535")
        if target.get("snmp"):
            snmp = target["snmp"]
            if str(snmp.get("version")) not in {"1", "2c", "3"}:
                raise ValueError("unsupported SNMP version")
            if str(snmp["version"]) != "3" and not snmp.get("community_env"):
                raise ValueError("legacy SNMP requires community_env")
    config["interval_seconds"] = max(15, int(config.get("interval_seconds", 60)))
    config["failure_threshold"] = max(1, int(config.get("failure_threshold", 3)))
    config["recovery_threshold"] = max(1, int(config.get("recovery_threshold", 2)))
    return config


def tcp_probe(host: str, port: int, timeout: float = 3) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, TimeoutError):
        return False


async def snmp_probe(host: str, cfg: dict) -> dict:
    """Only SNMP GET sysUpTime.0 / sysName.0; never SNMP SET."""
    try:
        from pysnmp.hlapi.v3arch.asyncio import (
            CommunityData, ContextData, ObjectIdentity, ObjectType,
            SnmpEngine, UdpTransportTarget, UsmUserData, get_cmd,
            USM_AUTH_HMAC96_SHA, USM_PRIV_CBC56_DES, USM_PRIV_CFB128_AES,
        )
    except ImportError:
        return {"ok": False, "reason": "pysnmp-not-installed"}

    version = str(cfg["version"])
    try:
        if version == "3":
            auth_env, priv_env = cfg.get("auth_env", ""), cfg.get("priv_env", "")
            auth_key, priv_key = os.environ.get(auth_env), os.environ.get(priv_env)
            if not auth_key or not priv_key:
                return {"ok": False, "reason": "missing-snmp-secret-env"}
            auth_alg = cfg.get("auth_protocol", "SHA").upper()
            priv_alg = cfg.get("priv_protocol", "AES").upper()
            if auth_alg != "SHA" or priv_alg not in {"AES", "DES"}:
                return {"ok": False, "reason": "unsupported-snmpv3-parameters"}
            auth = UsmUserData(
                cfg["user"], authKey=auth_key, privKey=priv_key,
                authProtocol=USM_AUTH_HMAC96_SHA,
                privProtocol=USM_PRIV_CBC56_DES if priv_alg == "DES" else USM_PRIV_CFB128_AES,
            )
        else:
            community = os.environ.get(cfg["community_env"])
            if not community:
                return {"ok": False, "reason": "missing-snmp-community-env"}
            auth = CommunityData(community, mpModel=0 if version == "1" else 1)
        engine = SnmpEngine()
        try:
            target = await UdpTransportTarget.create(
                (host, int(cfg.get("port", 161))), timeout=2, retries=0
            )
            error, status, _, values = await get_cmd(
                engine, auth, target, ContextData(),
                ObjectType(ObjectIdentity("1.3.6.1.2.1.1.3.0")),
                ObjectType(ObjectIdentity("1.3.6.1.2.1.1.5.0")),
                lookupMib=False,
            )
            if error or status or not values:
                return {"ok": False, "reason": "snmp-no-response"}
            return {
                "ok": True,
                "uptime_ticks": str(values[0][1].prettyPrint()),
                "sys_name": str(values[1][1].prettyPrint()),
            }
        finally:
            engine.close_dispatcher()
    except Exception:
        # Avoid logging SNMP secrets or backend exception strings.
        return {"ok": False, "reason": "snmp-request-failed"}


def update_state(state: dict, key: str, ok: bool, bad_after: int, good_after: int) -> str | None:
    """Debounced state transition. Returns DOWN/RECOVERED or None."""
    entry = state.setdefault(key, {"healthy": True, "pending": 0, "seen": False})
    entry.setdefault("pending", 0)
    entry.setdefault("seen", False)
    entry.setdefault("healthy", True)
    if ok == entry["healthy"]:
        entry["pending"] = 0
        entry["seen"] = True
        return None
    entry["pending"] += 1
    threshold = good_after if ok else bad_after
    if entry["pending"] < threshold:
        return None
    entry["healthy"] = ok
    entry["pending"] = 0
    entry["seen"] = True
    return "RECOVERED" if ok else "DOWN"


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    fd = os.open(tmp, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as file:
        json.dump(state, file, sort_keys=True)
    os.replace(tmp, path)


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
        with urllib.request.urlopen(request, timeout=5) as response:
            response.read(256)
    except Exception:
        print("Webhook delivery failed (details hidden)", flush=True)


async def poll(config: dict, state: dict) -> list[dict]:
    output = []
    for target in config["targets"]:
        name, host = target["name"], target["host"]
        tcp_ok = await asyncio.to_thread(tcp_probe, host, int(target["tcp_port"]))
        results = [(f"{name}/tcp", tcp_ok)]
        record = {"name": name, "tcp_ok": tcp_ok}
        if "snmp" in target:
            snmp_result = await snmp_probe(host, target["snmp"])
            record["snmp_ok"] = snmp_result["ok"]
            record["snmp"] = snmp_result
            results.append((f"{name}/snmp", snmp_result["ok"]))
        for key, ok in results:
            event = update_state(state, key, ok, config["failure_threshold"], config["recovery_threshold"])
            if event:
                notify(f"{time.strftime('%Y-%m-%d %H:%M:%S %z')} KSSH monitor {event}: {key}")
        output.append(record)
    return output


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
        save_state(state_path, state)
        if args.once:
            break
        time.sleep(config["interval_seconds"])


if __name__ == "__main__":
    main()
