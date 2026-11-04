# KSSH infrastructure monitor (NOT DEPLOYED)

Read-only monitoring for the Real HD 10GbE switch and the Proxmox hosts. Runs as a standalone Python process; it is **not** registered as KSSH MCP tools yet and **not** deployed anywhere. See [issue #11](https://github.com/ykinfohome7/ssh-connector/issues/11), [issue #10](https://github.com/ykinfohome7/ssh-connector/issues/10). The Proxmox VE API module is developed separately by CODEX in [issue #13](https://github.com/ykinfohome7/ssh-connector/issues/13).

> 🇧🇬 Резюме на български е в края на файла.

## Modules

| File | Purpose |
|---|---|
| `monitor.py` | Poll loop: TCP + SNMP checks, debounced DOWN/RECOVERED alerts, state file, optional HTTPS webhook |
| `snmp_client.py` | Bounded read-only SNMP client: GET / GETNEXT / GETBULK / WALK. **No SET.** Allowlist, OID validation, limits, concurrency, error classification |
| `snmp_interfaces.py` | IF-MIB / IF-X-MIB inventory, 64-bit counters, rate/utilisation maths, rollover/reboot/renumbering handling, flap tracking |
| `snmp_adapters.py` | Device adapters: generic (SNMPv2-MIB, ENTITY-MIB, ENTITY-SENSOR-MIB), `realhd`, placeholders `cisco`, `unifi` |
| `errors.py` | Error codes and UP / DOWN / UNKNOWN status |
| `logutil.py` | JSON logs (UTC) with key- and value-based secret redaction |

## Check status

| Status | Meaning | Alerts? |
|---|---|---|
| `UP` | check succeeded | RECOVERED after `recovery_threshold` |
| `DOWN` | device-side problem: `TIMEOUT`, `UNREACHABLE`, `AUTH_FAILED`, `PROTOCOL_ERROR` | DOWN after `failure_threshold` |
| `UNKNOWN` | our setup is broken: `DEPENDENCY_MISSING`, `SECRET_MISSING`, `CONFIG_ERROR`, `NOT_ALLOWED`, `INTERNAL` | never; logged as WARNING |

## Configuration (`targets.example.json`)

* `allowed_networks` — **required** allowlist (IPs/CIDRs, or exact hostnames). Every target must match.
* Per target: `tcp_port` and/or `snmp` (at least one).
* `snmp.version` — `"3"` (default). `"1"`/`"2c"` only with `"allow_legacy_snmp": true` and `community_env`.
* `snmp.security_level` — `noAuthNoPriv`, `authNoPriv`, `authPriv` (default).
* `snmp.auth_protocol` — `SHA` (=SHA-1), `SHA224`, `SHA256`, `SHA384`, `SHA512`. MD5 is not supported.
* `snmp.priv_protocol` — `AES` (default), `AES192`, `AES256`; `DES` only with `"allow_legacy_des": true`.
* `snmp.auth_env` / `priv_env` / `community_env` — **names** of environment variables; values are never in JSON.
* `snmp.timeout` (0.2–10 s, default 2), `snmp.retries` (0–5, default 1), `snmp.adapter` (`generic`, `realhd`, `cisco`, `unifi`).
* `max_concurrency` (1–16, default 4) — targets are checked in parallel.

The Real HD switch supports only SHA + DES, so the example sets `allow_legacy_des: true`. DES is weak; restrict UDP/161 to the management host.

## Safe local testing

```bash
python3 -m unittest -v tests/test_monitoring_mvp.py tests/test_monitoring_snmp.py   # offline, fake SNMP agent
python3 -m monitoring.monitor --once --config monitoring/targets.example.json        # only on an authorised host
```

For SNMP on a real host: `pip install -r monitoring/requirements-monitoring.txt`. **The PySNMP backend has not been executed yet** (PyPI was blocked in the development environment); validate it against a lab SNMP agent before any real device. Testing the Real HD switch or pve1/pve2 is `PENDING_EXPLICIT_APPROVAL`.

## Security limits

* No SNMP SET, no configuration changes, no service restarts, no auto-start, no listeners.
* No automatic SNMPv3 → v2c/v1 downgrade.
* Walks are bounded (results, seconds, hard ceilings) and stop on non-increasing OIDs.
* TCP reachability of :8006 does **not** prove Proxmox API or VM health.
* Temperature/fans/PSU only via ENTITY-SENSOR-MIB; otherwise `UNAVAILABLE`. No Real HD vendor OID is verified.

---

## 🇧🇬 На български

Мониторингът е **само за четене** и **не е внедрен**. Проверява TCP достъпност и SNMP (GET/GETNEXT/GETBULK/ограничен WALK — **никога SET**).

* `allowed_networks` е задължителен списък с разрешени адреси.
* SNMPv3 е по подразбиране (authPriv + AES). SNMPv1/v2c — само с `allow_legacy_snmp: true`. DES — само с `allow_legacy_des: true` (нужно за Real HD).
* Паролите се подават само чрез **имена** на променливи на средата, никога в JSON.
* Статус `UNKNOWN` (липсваща библиотека, парола или грешна настройка) **не** предизвиква тревога DOWN.
* Температура, вентилатори и захранване се показват само ако устройството ги дава през ENTITY-SENSOR-MIB; иначе `UNAVAILABLE` — стойности не се измислят.
* PySNMP частта **не е тествана реално** (PyPI е блокиран в средата за разработка). Тест с реален суич или pve1/pve2 изисква изрично одобрение (`PENDING_EXPLICIT_APPROVAL`).
