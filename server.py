"""SSH connector - local MCP server (stdio) for Claude Code and ChatGPT Codex.

Connects directly to target servers over SSH. Features:
- multiple servers (Debian / Red Hat), primary + fallback addresses
- connect/banner/login timeouts, keepalive, retry with backoff, automatic failover
- automatic reconnect when a connection silently dies
- up to max_sessions (default 10) parallel sessions per server
- background jobs for long commands
- event watchers: service errors, crashed processes / OOM, logins
"""
import asyncio
import json
import os
import time
import uuid
from collections import deque
from pathlib import Path

import asyncssh
import yaml
from mcp.server.fastmcp import FastMCP

CONFIG_PATH = os.environ.get("SSH_CONNECTOR_CONFIG", str(Path(__file__).with_name("servers.yaml")))
mcp = FastMCP("ssh-connector")


def load_config():
    with open(os.path.expanduser(CONFIG_PATH)) as f:
        raw = yaml.safe_load(f) or {}
    defaults = raw.get("defaults", {})
    servers = {}
    for name, cfg in (raw.get("servers") or {}).items():
        merged = {**defaults, **cfg}
        if not merged.get("hosts"):
            merged["hosts"] = [merged["host"]]
        servers[name] = merged
    return servers


class Server:
    def __init__(self, name, cfg):
        self.name = name
        self.cfg = cfg
        self.conn = None
        self.active_host = None
        self.lock = asyncio.Lock()
        self.sem = asyncio.Semaphore(int(cfg.get("max_sessions", 10)))
        self.last_error = None

    def _alive(self):
        return self.conn is not None and not self.conn.is_closed()

    async def _connect_host(self, host):
        c = self.cfg
        kh = c.get("known_hosts", "~/.ssh/known_hosts")
        kh = os.path.expanduser(kh) if kh else None
        key = c.get("key")
        return await asyncio.wait_for(
            asyncssh.connect(
                host,
                port=int(c.get("port", 22)),
                username=c.get("user"),
                client_keys=[os.path.expanduser(key)] if key else None,
                password=c.get("password"),
                known_hosts=kh,
                connect_timeout=c.get("connect_timeout", 8),
                login_timeout=c.get("connect_timeout", 8) * 2,
                keepalive_interval=c.get("keepalive_interval", 30),
                keepalive_count_max=c.get("keepalive_count_max", 3),
            ),
            timeout=c.get("connect_timeout", 8) * 3,
        )

    async def get_conn(self, force=False):
        async with self.lock:
            if self._alive() and not force:
                return self.conn
            if self.conn:
                self.conn.close()
            self.conn = None
            errors = []
            for host in self.cfg["hosts"]:  # primary first, then fallbacks
                for attempt in range(int(self.cfg.get("retries", 3))):
                    try:
                        self.conn = await self._connect_host(host)
                        self.active_host = host
                        self.last_error = None
                        return self.conn
                    except (OSError, asyncssh.Error, asyncio.TimeoutError) as e:
                        errors.append(f"{host} try {attempt + 1}: {type(e).__name__}: {e}")
                        await asyncio.sleep(min(2 ** attempt, 10))
            self.last_error = "; ".join(errors)
            raise ConnectionError(f"{self.name}: all addresses failed -> {self.last_error}")

    async def run(self, command, timeout):
        async with self.sem:
            for attempt in range(2):  # one transparent reconnect if the connection died
                conn = await self.get_conn(force=attempt > 0)
                try:
                    r = await asyncio.wait_for(conn.run(command, check=False), timeout=timeout)
                    return {"server": self.name, "host": self.active_host, "exit_code": r.exit_status,
                            "stdout": r.stdout, "stderr": r.stderr}
                except asyncio.TimeoutError:
                    return {"server": self.name, "host": self.active_host, "error": f"timeout after {timeout}s"}
                except (asyncssh.ConnectionLost, asyncssh.DisconnectError, BrokenPipeError, ConnectionResetError) as e:
                    if attempt:
                        raise
                    self.last_error = f"connection lost: {e}"
                except asyncssh.ChannelOpenError as e:
                    return {"server": self.name, "error": f"cannot open session (MaxSessions?): {e}"}


SERVERS = {}
JOBS = {}
WATCHERS = {}
EVENTS = deque(maxlen=2000)


def srv(name):
    if not SERVERS:
        for n, c in load_config().items():
            SERVERS[n] = Server(n, c)
    if name not in SERVERS:
        raise ValueError(f"unknown server '{name}'. Known: {', '.join(SERVERS)}")
    return SERVERS[name]


@mcp.tool()
async def list_servers() -> str:
    """List configured servers, their addresses and connection state."""
    srv(next(iter(load_config()), "")) if not SERVERS else None
    out = []
    for s in SERVERS.values():
        out.append({"name": s.name, "os": s.cfg.get("os"), "hosts": s.cfg["hosts"],
                    "connected": s._alive(), "active_host": s.active_host, "last_error": s.last_error})
    return json.dumps(out, indent=2)


@mcp.tool()
async def run_command(server: str, command: str, timeout: int = 0) -> str:
    """Run a shell command on a server. Reconnects / fails over automatically."""
    s = srv(server)
    t = timeout or s.cfg.get("command_timeout", 120)
    try:
        return json.dumps(await s.run(command, t), indent=2)
    except Exception as e:
        return json.dumps({"server": server, "error": str(e)})


@mcp.tool()
async def run_on_many(servers: list[str], command: str, timeout: int = 0) -> str:
    """Run the same command on several servers in parallel."""
    res = await asyncio.gather(*(run_command(n, command, timeout) for n in servers))
    return "[" + ",".join(res) + "]"


@mcp.tool()
async def start_job(server: str, command: str) -> str:
    """Start a long-running command in the background on the server (survives disconnects)."""
    jid = uuid.uuid4().hex[:8]
    log = f"/tmp/sshconn_{jid}.log"
    cmd = f"nohup sh -c {json.dumps(command)} > {log} 2>&1 & echo $!"
    r = await srv(server).run(cmd, 30)
    JOBS[jid] = {"server": server, "pid": (r.get("stdout") or "").strip(), "log": log, "command": command}
    return json.dumps({"job_id": jid, **JOBS[jid]})


@mcp.tool()
async def job_status(job_id: str, tail: int = 50) -> str:
    """Check a background job: running or finished, plus the last lines of output."""
    j = JOBS.get(job_id)
    if not j:
        return json.dumps({"error": "unknown job"})
    r = await srv(j["server"]).run(
        f"if kill -0 {j['pid']} 2>/dev/null; then echo RUNNING; else echo DONE; fi; tail -n {int(tail)} {j['log']}", 30)
    return json.dumps({"job_id": job_id, **r}, indent=2)


# ---------------- events ----------------
WATCH_KINDS = {
    "service_errors": "journalctl -f -n0 -o json -p err",
    "crashes": "journalctl -f -n0 -o json -k --grep='Out of memory|Killed process|segfault' ; "
               "journalctl -f -n0 -o json --grep='core dumped|Failed with result|entered failed state'",
    "logins": "journalctl -f -n0 -o json _COMM=sshd --grep='Accepted|Failed password|session opened'",
}


async def _watch(server, kind):
    s = srv(server)
    cmd = WATCH_KINDS[kind]
    backoff = 1
    while True:
        try:
            conn = await s.get_conn()
            async with conn.create_process(f"sh -c {json.dumps(cmd)}") as proc:
                backoff = 1
                async for line in proc.stdout:
                    try:
                        j = json.loads(line)
                        msg = j.get("MESSAGE")
                        unit = j.get("_SYSTEMD_UNIT") or j.get("SYSLOG_IDENTIFIER")
                    except ValueError:
                        msg, unit = line.strip(), None
                    EVENTS.append({"ts": time.time(), "server": server, "kind": kind, "unit": unit, "message": msg})
        except asyncio.CancelledError:
            raise
        except Exception as e:
            EVENTS.append({"ts": time.time(), "server": server, "kind": "watcher", "message": f"{kind} watcher lost: {e}; reconnecting"})
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)
            await s.get_conn(force=True) if not s._alive() else None


@mcp.tool()
async def start_watch(server: str, kinds: list[str] = ["service_errors", "crashes", "logins"]) -> str:
    """Start listening for events on a server. Kinds: service_errors, crashes, logins."""
    started = []
    for k in kinds:
        if k not in WATCH_KINDS:
            continue
        key = f"{server}:{k}"
        if key not in WATCHERS or WATCHERS[key].done():
            WATCHERS[key] = asyncio.create_task(_watch(server, k))
        started.append(key)
    return json.dumps({"watching": started})


@mcp.tool()
async def stop_watch(server: str) -> str:
    """Stop all event watchers for a server."""
    stopped = [k for k in list(WATCHERS) if k.startswith(server + ":")]
    for k in stopped:
        WATCHERS.pop(k).cancel()
    return json.dumps({"stopped": stopped})


@mcp.tool()
async def get_events(since: float = 0, server: str = "", limit: int = 100) -> str:
    """Read captured events (newest last). Pass the last 'ts' as 'since' to get only new ones."""
    ev = [e for e in EVENTS if e["ts"] > since and (not server or e["server"] == server)]
    return json.dumps(ev[-limit:], indent=2)


if __name__ == "__main__":
    mcp.run()
