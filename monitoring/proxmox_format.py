"""Pure Proxmox response normalizers (no I/O, no implicit zeroes)."""
from __future__ import annotations

import math


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def normalize(resource: str, value):
    """Return (data, capability flags); ValueError means a malformed API shape."""
    flags = {}
    if resource == "api_version":
        if not isinstance(value, dict) or not isinstance(value.get("version"), str):
            raise ValueError("Invalid Proxmox version response")
        return {key: value[key] for key in ("version", "release", "repoid")
                if key in value}, {"api_version": True}

    if resource == "nodes":
        if not isinstance(value, list) or any(
            not isinstance(x, dict) or not isinstance(x.get("node"), str)
            for x in value
        ):
            raise ValueError("Invalid nodes response")
        return [{"node": x["node"], **({"status": x["status"]}
                  if "status" in x else {})} for x in value], {"node_inventory": True}

    if resource == "node_status":
        if not isinstance(value, dict):
            raise ValueError("Invalid node status response")
        data = {key: value[key] for key in (
            "status", "uptime", "cpu", "loadavg", "memory", "swap",
            "wait", "kversion", "pveversion", "netin", "netout"
        ) if key in value}
        for key in ("cpu", "uptime", "wait", "netin", "netout"):
            if key in data and not number(data[key]):
                del data[key]
        for key in ("memory", "swap"):
            if key in data:
                if not isinstance(data[key], dict):
                    del data[key]
                else:
                    data[key] = {k: v for k, v in data[key].items()
                                 if k in ("used", "total", "free") and number(v)}
        return data, {
            "cpu": "cpu" in data,
            "memory": bool(data.get("memory")),
            "swap": bool(data.get("swap")),
            "network_metrics": "netin" in data or "netout" in data,
        }

    if resource == "storage":
        if not isinstance(value, list):
            raise ValueError("Invalid storage response")
        result, capacity = [], False
        for item in value:
            if not isinstance(item, dict) or not isinstance(item.get("storage"), str):
                raise ValueError("Invalid storage item")
            row = {k: item[k] for k in ("storage", "type", "active", "enabled")
                   if k in item}
            used, total = item.get("used"), item.get("total")
            if number(used) and number(total) and 0 <= used and total > 0:
                capacity = True
                row.update(used=used, total=total, usage_ratio=used / total)
                row["warning"] = used / total >= 0.90
            else:
                row["warning"] = None
            if item.get("active") == 0:
                row["warning"] = True
            result.append(row)
        return result, {"capacity": capacity}

    if resource in ("qemu", "lxc"):
        if not isinstance(value, list):
            raise ValueError("Invalid inventory response")
        records, network = [], False
        for entry in value:
            if (not isinstance(entry, dict) or type(entry.get("vmid")) is not int
                    or entry["vmid"] <= 0):
                raise ValueError("Invalid VM inventory entry")
            row = {key: entry[key] for key in (
                "vmid", "name", "status", "uptime", "cpu", "mem", "maxmem"
            ) if key in entry}
            for metric in ("netin", "netout"):
                if metric in entry and number(entry[metric]):
                    row[metric] = entry[metric]
                    network = True
            records.append(row)
        return records, {"inventory": True, "network_metrics": network}

    if resource == "backup_tasks":
        if not isinstance(value, list):
            raise ValueError("Invalid task response")
        tasks, failures = [], []
        for item in value:
            if not isinstance(item, dict):
                raise ValueError("Invalid task item")
            if item.get("type", "vzdump") != "vzdump":
                continue
            row = {key: item[key] for key in (
                "upid", "id", "type", "status", "starttime", "endtime"
            ) if key in item}
            # In-progress tasks without endtime are NOT failed.
            if item.get("endtime") is not None and item.get("status") != "OK":
                failures.append(row)
            tasks.append(row)
        return {
            "tasks": tasks, "failures": failures, "total_returned": len(tasks)
        }, {
            "pve_backup_task_history": True,
            "history_may_be_truncated": len(value) >= 100,
            "pbs_health": False,
        }
    raise ValueError("Unknown resource")
