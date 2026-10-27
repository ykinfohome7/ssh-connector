"""MCP SSH connector for Claude.

Exposes tools to list configured servers and run commands on them over SSH.
Works with Debian/Ubuntu and Red Hat/CentOS/Rocky/Alma hosts.
"""
import os
import shlex
import yaml
import paramiko
from mcp.server.fastmcp import FastMCP

CONFIG_PATH = os.environ.get("SSH_CONNECTOR_CONFIG", os.path.join(os.path.dirname(__file__), "servers.yaml"))
mcp = FastMCP("ssh-connector")


def load_servers() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("servers", {})


def connect(name: str) -> paramiko.SSHClient:
    servers = load_servers()
    if name not in servers:
        raise ValueError(f"Unknown server '{name}'. Known: {', '.join(servers)}")
    s = servers[name]
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    if s.get("auto_add_host_key", False):
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    else:
        client.set_missing_host_key_policy(paramiko.RejectPolicy())
    client.connect(
        hostname=s["host"],
        port=int(s.get("port", 22)),
        username=s["user"],
        key_filename=os.path.expanduser(s["key"]) if s.get("key") else None,
        password=os.environ.get(s["password_env"]) if s.get("password_env") else None,
        timeout=15,
    )
    return client


@mcp.tool()
def list_servers() -> list[dict]:
    """List configured servers (name, host, user, os)."""
    return [
        {"name": n, "host": s["host"], "user": s["user"], "os": s.get("os", "unknown")}
        for n, s in load_servers().items()
    ]


@mcp.tool()
def run_command(server: str, command: str, timeout: int = 60) -> dict:
    """Run a shell command on a configured server and return stdout, stderr and exit code."""
    client = connect(server)
    try:
        _, stdout, stderr = client.exec_command(command, timeout=timeout)
        code = stdout.channel.recv_exit_status()
        return {
            "server": server,
            "exit_code": code,
            "stdout": stdout.read().decode(errors="replace")[-20000:],
            "stderr": stderr.read().decode(errors="replace")[-20000:],
        }
    finally:
        client.close()


@mcp.tool()
def detect_os(server: str) -> dict:
    """Detect the Linux distribution (Debian family or Red Hat family)."""
    r = run_command(server, "cat /etc/os-release")
    info = dict(line.split("=", 1) for line in r["stdout"].splitlines() if "=" in line)
    ids = (info.get("ID", "") + " " + info.get("ID_LIKE", "")).replace('"', "")
    family = "debian" if "debian" in ids else "redhat" if ("rhel" in ids or "fedora" in ids) else "other"
    return {"server": server, "name": info.get("PRETTY_NAME", "").strip('"'), "family": family}


@mcp.tool()
def install_package(server: str, package: str) -> dict:
    """Install a package using apt (Debian) or dnf/yum (Red Hat)."""
    pkg = shlex.quote(package)
    family = detect_os(server)["family"]
    if family == "debian":
        cmd = f"sudo DEBIAN_FRONTEND=noninteractive apt-get install -y {pkg}"
    elif family == "redhat":
        cmd = f"sudo $(command -v dnf || command -v yum) install -y {pkg}"
    else:
        raise ValueError("Unsupported OS family")
    return run_command(server, cmd, timeout=600)


if __name__ == "__main__":
    mcp.run()
