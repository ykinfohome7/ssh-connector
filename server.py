"""SSH connector - local MCP server (stdio) for Claude Code and ChatGPT Codex.

Connects directly to target servers over SSH. Features (Termius-style):
- multiple servers (Debian / Red Hat), primary + fallback addresses, automatic failover
- connect/login timeouts, keepalive, retries with backoff, transparent reconnect
- jump hosts (bastion / ProxyJump)
- tags / groups, run a command on a whole group in parallel
- snippets (saved commands)
- sudo support
- interactive shell sessions that keep state (cd, env vars, running programs)
- SFTP: list, read, write, upload, download, mkdir, remove, rename
- local port forwarding (tunnels)
- background jobs for long commands
- event watchers: service errors, crashes / OOM, logins
- command history
- HTTP mode (--http) for ChatGPT and remote clients, token-protected
"""
import asyncio
import json
import os
import shlex
import time
import uuid
from collections import deque
from pathlib import Path

import asyncssh
import yaml
from mcp.server.fastmcp import FastMCP

CONFIG_PATH = os.environ.get("SSH_CONNECTOR_CONFIG", str(Path(__file__).with_name("servers.yaml")))
mcp = FastMCP("ssh-connector")
try:  # allow access through a tunnel / reverse proxy (Host header is the public domain); auth is enforced below
    from mcp.server.transport_security import TransportSecuritySettings
    mcp.settings.transport_security = TransportSecuritySettings(enable_dns_rebinding_protection=False)
except Exception:
    pass


def load_config():
    with open(os.path.expanduser(CONFIG_PATH)) as f:
        raw = yaml.safe_load(f) or {}
    defaults = raw.get("defaults", {})
    servers = {}
    for name, cfg in (raw.get("servers") or {}).items():
        merged = {**defaults, **(cfg or {})}
        if not merged.get("hosts"):
            merged["hosts"] = [merged["host"]]
        merged.setdefault("tags", [])
        servers[name] = merged
    return servers, raw.get("snippets") or {}


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
        tunnel = None
        if c.get("jump"):  # name of another configured server used as bastion
            tunnel = await srv(c["jump"]).get_conn()
        ct = c.get("connect_timeout", 8)
        kwargs = dict(
            port=int(c.get("port", 22)),
            username=c.get("user"),
            password=c.get("password"),
            known_hosts=kh,
            connect_timeout=ct,
            login_timeout=ct * 2,
            keepalive_interval=c.get("keepalive_interval", 30),
            keepalive_count_max=c.get("keepalive_count_max", 3),
        )
        if key:
            kwargs["client_keys"] = [os.path.expanduser(key)]
        if tunnel:
            kwargs["tunnel"] = tunnel
        return await asyncio.wait_for(asyncssh.connect(host, **kwargs), timeout=ct * 3)

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
                    res = {"server": self.name, "host": self.active_host, "exit_code": r.exit_status,
                           "stdout": r.stdout, "stderr": r.stderr}
                    HISTORY.append({"ts": time.time(), "server": self.name, "command": command,
                                    "exit_code": r.exit_status})
                    return res
                except asyncio.TimeoutError:
                    return {"server": self.name, "host": self.active_host, "error": f"timeout after {timeout}s"}
                except (asyncssh.ConnectionLost, asyncssh.DisconnectError, BrokenPipeError, ConnectionResetError) as e:
                    if attempt:
                        raise
                    self.last_error = f"connection lost: {e}"
                except asyncssh.ChannelOpenError as e:
                    return {"server": self.name, "error": f"cannot open session (MaxSessions?): {e}"}


SERVERS = {}
SNIPPETS = {}
JOBS = {}
WATCHERS = {}
SHELLS = {}
FORWARDS = {}
EVENTS = deque(maxlen=2000)
HISTORY = deque(maxlen=500)


def init():
    if not SERVERS:
        servers, snippets = load_config()
        for n, c in servers.items():
            SERVERS[n] = Server(n, c)
        SNIPPETS.update(snippets)


def srv(name):
    init()
    if name not in SERVERS:
        raise ValueError(f"unknown server '{name}'. Known: {', '.join(SERVERS)}")
    return SERVERS[name]


def _err(e, **extra):
    return json.dumps({**extra, "error": f"{type(e).__name__}: {e}"})


# ---------------- servers & commands ----------------
@mcp.tool()
async def list_servers(tag: str = "") -> str:
    """List configured servers (optionally only one tag/group), addresses, tags and connection state."""
    init()
    out = []
    for s in SERVERS.values():
        if tag and tag not in s.cfg["tags"]:
            continue
        out.append({"name": s.name, "os": s.cfg.get("os"), "hosts": s.cfg["hosts"], "tags": s.cfg["tags"],
                    "jump": s.cfg.get("jump"), "connected": s._alive(), "active_host": s.active_host,
                    "last_error": s.last_error})
    return json.dumps(out, indent=2)


@mcp.tool()
async def run_command(server: str, command: str, timeout: int = 0, sudo: bool = False) -> str:
    """Run a shell command on a server. Reconnects / fails over automatically. sudo=True runs it with sudo -n."""
    try:
        s = srv(server)
        t = timeout or s.cfg.get("command_timeout", 120)
        if sudo:
            command = f"sudo -n sh -c {shlex.quote(command)}"
        return json.dumps(await s.run(command, t), indent=2)
    except Exception as e:
        return _err(e, server=server)


@mcp.tool()
async def run_on_many(servers: list[str], command: str, timeout: int = 0, sudo: bool = False) -> str:
    """Run the same command on several servers in parallel."""
    res = await asyncio.gather(*(run_command(n, command, timeout, sudo) for n in servers))
    return "[" + ",".join(res) + "]"


@mcp.tool()
async def run_on_group(tag: str, command: str, timeout: int = 0, sudo: bool = False) -> str:
    """Run a command on every server that has the given tag (group)."""
    init()
    names = [n for n, s in SERVERS.items() if tag in s.cfg["tags"]]
    if not names:
        return json.dumps({"error": f"no servers with tag '{tag}'"})
    return await run_on_many(names, command, timeout, sudo)


@mcp.tool()
async def list_snippets() -> str:
    """List saved command snippets from servers.yaml."""
    init()
    return json.dumps(SNIPPETS, indent=2)


@mcp.tool()
async def run_snippet(server: str, name: str, sudo: bool = False) -> str:
    """Run a saved snippet by name on a server."""
    init()
    if name not in SNIPPETS:
        return json.dumps({"error": f"unknown snippet '{name}'", "known": list(SNIPPETS)})
    return await run_command(server, SNIPPETS[name], 0, sudo)


@mcp.tool()
async def history(limit: int = 50, server: str = "") -> str:
    """Show recently executed commands."""
    h = [x for x in HISTORY if not server or x["server"] == server]
    return json.dumps(h[-limit:], indent=2)


# ---------------- background jobs ----------------
@mcp.tool()
async def start_job(server: str, command: str) -> str:
    """Start a long-running command in the background on the server (survives disconnects)."""
    try:
        jid = uuid.uuid4().hex[:8]
        log = f"/tmp/sshconn_{jid}.log"
        cmd = f"nohup sh -c {shlex.quote(command)} > {log} 2>&1 & echo $!"
        r = await srv(server).run(cmd, 30)
        JOBS[jid] = {"server": server, "pid": (r.get("stdout") or "").strip(), "log": log, "command": command}
        return json.dumps({"job_id": jid, **JOBS[jid]})
    except Exception as e:
        return _err(e, server=server)


@mcp.tool()
async def job_status(job_id: str, tail: int = 50) -> str:
    """Check a background job: running or finished, plus the last lines of output."""
    j = JOBS.get(job_id)
    if not j:
        return json.dumps({"error": "unknown job"})
    try:
        r = await srv(j["server"]).run(
            f"if kill -0 {j['pid']} 2>/dev/null; then echo RUNNING; else echo DONE; fi; tail -n {int(tail)} {j['log']}", 30)
        return json.dumps({"job_id": job_id, **r}, indent=2)
    except Exception as e:
        return _err(e, job_id=job_id)


# ---------------- interactive shell sessions ----------------
async def _read_until_idle(proc, wait, idle=0.6):
    buf = []
    deadline = time.time() + wait
    while time.time() < deadline:
        try:
            chunk = await asyncio.wait_for(proc.stdout.read(65536), timeout=idle)
        except asyncio.TimeoutError:
            if buf:
                break
            continue
        if not chunk:
            break
        buf.append(chunk)
    return "".join(buf)


@mcp.tool()
async def shell_open(server: str, cols: int = 200, rows: int = 50) -> str:
    """Open an interactive shell (with PTY) that keeps state between calls (cd, env, running programs)."""
    try:
        conn = await srv(server).get_conn()
        proc = await conn.create_process(term_type="xterm", term_size=(cols, rows), encoding="utf-8")
        sid = uuid.uuid4().hex[:8]
        SHELLS[sid] = {"server": server, "proc": proc, "opened": time.time()}
        banner = await _read_until_idle(proc, 3)
        return json.dumps({"shell_id": sid, "output": banner})
    except Exception as e:
        return _err(e, server=server)


@mcp.tool()
async def shell_send(shell_id: str, input: str, wait: float = 5, enter: bool = True) -> str:
    """Send input to an open shell and return the output. Use input='\\x03' with enter=False for Ctrl+C."""
    sh = SHELLS.get(shell_id)
    if not sh:
        return json.dumps({"error": "unknown shell_id"})
    proc = sh["proc"]
    try:
        proc.stdin.write(input + ("\n" if enter else ""))
        out = await _read_until_idle(proc, wait)
        HISTORY.append({"ts": time.time(), "server": sh["server"], "command": f"[shell] {input}", "exit_code": None})
        return json.dumps({"shell_id": shell_id, "output": out, "closed": proc.exit_status is not None})
    except Exception as e:
        SHELLS.pop(shell_id, None)
        return _err(e, shell_id=shell_id, note="shell closed; open a new one")


@mcp.tool()
async def shell_close(shell_id: str) -> str:
    """Close an interactive shell."""
    sh = SHELLS.pop(shell_id, None)
    if sh:
        sh["proc"].close()
    return json.dumps({"closed": bool(sh)})


@mcp.tool()
async def list_shells() -> str:
    """List open interactive shells."""
    return json.dumps([{"shell_id": k, "server": v["server"], "opened": v["opened"]} for k, v in SHELLS.items()])


# ---------------- SFTP ----------------
async def _sftp(server):
    conn = await srv(server).get_conn()
    return conn.start_sftp_client()


@mcp.tool()
async def sftp_list(server: str, path: str = ".") -> str:
    """List a remote directory (name, size, type, permissions, modified time)."""
    try:
        async with await _sftp(server) as sftp:
            items = []
            for e in await sftp.readdir(path):
                if e.filename in (".", ".."):
                    continue
                a = e.attrs
                items.append({"name": e.filename, "size": a.size,
                              "dir": bool(a.permissions and (a.permissions & 0o170000) == 0o040000),
                              "perm": oct(a.permissions & 0o777) if a.permissions else None, "mtime": a.mtime})
            return json.dumps(sorted(items, key=lambda x: (not x["dir"], x["name"])), indent=2)
    except Exception as e:
        return _err(e, server=server, path=path)


@mcp.tool()
async def sftp_read(server: str, path: str, max_bytes: int = 200000) -> str:
    """Read a remote text file (up to max_bytes)."""
    try:
        async with await _sftp(server) as sftp:
            async with sftp.open(path, "rb") as f:
                data = await f.read(max_bytes)
            return json.dumps({"path": path, "content": data.decode("utf-8", "replace"), "truncated": len(data) >= max_bytes})
    except Exception as e:
        return _err(e, server=server, path=path)


@mcp.tool()
async def sftp_write(server: str, path: str, content: str, append: bool = False) -> str:
    """Write (or append) text to a remote file."""
    try:
        async with await _sftp(server) as sftp:
            async with sftp.open(path, "ab" if append else "wb") as f:
                await f.write(content.encode("utf-8"))
            return json.dumps({"path": path, "bytes": len(content.encode("utf-8")), "append": append})
    except Exception as e:
        return _err(e, server=server, path=path)


@mcp.tool()
async def sftp_upload(server: str, local_path: str, remote_path: str) -> str:
    """Upload a local file or directory (recursive) to the server."""
    try:
        async with await _sftp(server) as sftp:
            await sftp.put(os.path.expanduser(local_path), remote_path, recurse=True, preserve=True)
            return json.dumps({"uploaded": local_path, "to": remote_path})
    except Exception as e:
        return _err(e, server=server)


@mcp.tool()
async def sftp_download(server: str, remote_path: str, local_path: str) -> str:
    """Download a remote file or directory (recursive) to this computer."""
    try:
        async with await _sftp(server) as sftp:
            await sftp.get(remote_path, os.path.expanduser(local_path), recurse=True, preserve=True)
            return json.dumps({"downloaded": remote_path, "to": local_path})
    except Exception as e:
        return _err(e, server=server)


@mcp.tool()
async def sftp_manage(server: str, action: str, path: str, new_path: str = "") -> str:
    """File management: action = mkdir | remove | rmdir | rename | stat."""
    try:
        async with await _sftp(server) as sftp:
            if action == "mkdir":
                await sftp.makedirs(path, exist_ok=True)
            elif action == "remove":
                await sftp.remove(path)
            elif action == "rmdir":
                await sftp.rmdir(path)
            elif action == "rename":
                await sftp.rename(path, new_path)
            elif action == "stat":
                a = await sftp.stat(path)
                return json.dumps({"path": path, "size": a.size, "perm": oct(a.permissions & 0o777) if a.permissions else None,
                                   "uid": a.uid, "gid": a.gid, "mtime": a.mtime})
            else:
                return json.dumps({"error": "action must be mkdir|remove|rmdir|rename|stat"})
            return json.dumps({"ok": True, "action": action, "path": path, "new_path": new_path or None})
    except Exception as e:
        return _err(e, server=server, path=path)


# ---------------- port forwarding ----------------
@mcp.tool()
async def port_forward(server: str, local_port: int, remote_host: str = "127.0.0.1", remote_port: int = 0) -> str:
    """Open a local tunnel: localhost:local_port -> remote_host:remote_port through the server."""
    try:
        conn = await srv(server).get_conn()
        listener = await conn.forward_local_port("127.0.0.1", local_port, remote_host, remote_port or local_port)
        fid = uuid.uuid4().hex[:8]
        FORWARDS[fid] = {"server": server, "listener": listener, "local": f"127.0.0.1:{listener.get_port()}",
                         "remote": f"{remote_host}:{remote_port or local_port}"}
        return json.dumps({"forward_id": fid, "local": FORWARDS[fid]["local"], "remote": FORWARDS[fid]["remote"]})
    except Exception as e:
        return _err(e, server=server)


@mcp.tool()
async def list_forwards() -> str:
    """List open tunnels."""
    return json.dumps([{"forward_id": k, "server": v["server"], "local": v["local"], "remote": v["remote"]}
                       for k, v in FORWARDS.items()])


@mcp.tool()
async def stop_forward(forward_id: str) -> str:
    """Close a tunnel."""
    f = FORWARDS.pop(forward_id, None)
    if f:
        f["listener"].close()
    return json.dumps({"closed": bool(f)})


# ---------------- events ----------------
WATCH_KINDS = {
    "service_errors": "journalctl -f -n0 -o json -p err",
    "crashes": "journalctl -f -n0 -o json --grep='Out of memory|Killed process|segfault|core dumped|Failed with result|entered failed state'",
    "logins": "journalctl -f -n0 -o json --grep='Accepted (password|publickey)|Failed password|session opened for user'",
}


async def _watch(server, kind):
    s = srv(server)
    cmd = WATCH_KINDS[kind]
    backoff = 1
    while True:
        try:
            conn = await s.get_conn()
            async with conn.create_process(cmd) as proc:
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
            EVENTS.append({"ts": time.time(), "server": server, "kind": "watcher",
                           "message": f"{kind} watcher lost: {e}; reconnecting"})
        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, 60)


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


# ---------------- HTTP mode (ChatGPT, remote Codex) ----------------
def http_app(token):
    """Streamable HTTP app guarded by a token: either 'Authorization: Bearer <token>'
    or a secret URL prefix https://host/<token>/mcp (for clients without header auth, e.g. ChatGPT)."""
    app = mcp.streamable_http_app()
    prefix = f"/{token}"

    async def guarded(scope, receive, send):
        if scope["type"] == "http":
            path = scope.get("path", "")
            headers = dict(scope.get("headers") or [])
            auth = headers.get(b"authorization", b"").decode()
            if path.startswith(prefix + "/"):
                new = path[len(prefix):]
                scope = dict(scope, path=new, raw_path=new.encode())
            elif auth != f"Bearer {token}":
                await send({"type": "http.response.start", "status": 401,
                            "headers": [(b"content-type", b"text/plain")]})
                await send({"type": "http.response.body", "body": b"unauthorized"})
                return
        await app(scope, receive, send)

    return guarded


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--http", action="store_true", help="serve over streamable HTTP instead of stdio")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    a = p.parse_args()
    if a.http:
        token = os.environ.get("SSH_CONNECTOR_TOKEN", "")
        if len(token) < 24:
            raise SystemExit("Set SSH_CONNECTOR_TOKEN to a random secret of at least 24 characters "
                             "(e.g. python3 -c 'import secrets;print(secrets.token_urlsafe(32))')")
        import uvicorn
        uvicorn.run(http_app(token), host=a.host, port=a.port)
    else:
        mcp.run()
