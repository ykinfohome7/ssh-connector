# KSSH infrastructure monitor — MVP (NOT DEPLOYED)

Initial **read-only** monitoring prototype for the user's Real HD switch and Proxmox hosts. It runs as a standalone Python process; integration into KSSH and deployment are **not** implemented yet. See [issue #11](https://github.com/ykinfohome7/ssh-connector/issues/11) and [SNMP/RDP issue #10](https://github.com/ykinfohome7/ssh-connector/issues/10).

## Inventory

| Device | IP | Check |
|---|---|---|
| Real HD SW5-10G-RJ45 | 192.168.30.10 | HTTP/TCP 80 and read-only SNMPv3 sysUpTime.0, sysName.0 |
| Proxmox pve1 | 192.168.0.100 | TCP 8006 reachability only |
| Proxmox pve2 | 192.168.0.127 | TCP 8006 reachability only |

**Not yet included:** Proxmox API CPU/RAM/storage/VM status, backups, switch interface counters or temperature vendor OIDs, native push notifications, persistent systemd service, RDP. These are next iterations described in issue #11.

## Safe local testing

Use a Linux host **already permitted** to reach the switch's management network and both Proxmox hosts. Do not put the switch's WAN port into a LAN switch.

1. Create a venv and install `pysnmp>=7.1,<8` for SNMP. Basic TCP polling does not need third-party packages.
2. Use `monitoring/targets.example.json` as a starting point.
3. Supply SNMPv3 passwords as **environment variables** named `KSSH_REALHD_AUTH_PASS` and `KSSH_REALHD_PRIV_PASS` via a private, chmod-600 protected service configuration or credentials manager. Never commit values or paste them into an issue/chat. The Real HD supports SHA authentication and only DES privacy; this is legacy cryptography, so restrict SNMP UDP/161 to an authorized management source.
4. Run one local poll: `python3 monitoring/monitor.py --once --config monitoring/targets.example.json`.
5. Run continuously only after checking results, access controls and notification destination: `python3 monitoring/monitor.py --config monitoring/targets.example.json`.

The program reports to stdout on each poll. On a confirmed transition, it logs `DOWN` or `RECOVERED`; only if `KSSH_MONITOR_WEBHOOK` is explicitly set to an **HTTPS** endpoint will it POST a `{"text":"..."}` notification. This is suitable for some webhook receivers, not all; test your actual provider first. No unsolicited ChatGPT notifications are generated.

A target is declared down after **3** failing polls, and recovered after **2** good polls (60s poll interval by default). State is stored under `~/.local/state/kssh-monitor.json`. Initial state assumes healthy; consequently a newly unavailable host must fail the configured number of times before it alerts. This avoids one-packet false alarms but means short outages can be missed.

## Security limits / Важни ограничения

- A successful TCP connection does **not** prove Proxmox API health or VM health.
- SNMP data for temperature is not yet implemented. Verify Real HD's vendor MIB/OID first.
- For SNMPv1/v2c legacy Cisco devices, only configure `community_env` with the name of a private environment variable; never put the community itself into JSON. Prefer v3 where possible.
- No SNMP SET, configuration changes, firewall changes, auto-starts, or service restarts.
- Current prototype is untested against real hardware. Review/test locally before installing.
- No code in this branch is automatically deployed to the installed KSSH service.
