import asyncio, json, os, sys, time
os.environ["SSH_CONNECTOR_CONFIG"] = os.path.join(os.path.dirname(__file__), "servers.test.yaml")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN = os.path.join(REPO, "plugins", "ssh-connector")
sys.path.insert(0, PLUGIN)
import server


async def step(name, coro):
    t = time.time()
    try:
        r = await coro
        try:
            r = json.loads(r)
        except Exception:
            pass
    except Exception as e:
        r = {"error": f"{type(e).__name__}: {e}"}
    return {"test": name, "seconds": round(time.time() - t, 1), "result": r}


async def http_check():
    import subprocess
    import httpx
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    token = "T" * 32
    base = "http://127.0.0.1:8799"
    env = dict(os.environ, SSH_CONNECTOR_TOKEN=token)
    proc = subprocess.Popen([sys.executable, server.__file__, "--http", "--port", "8799"], env=env)
    try:
        await asyncio.sleep(5)
        async with httpx.AsyncClient() as c:
            no_token = (await c.post(base + "/mcp", json={})).status_code
            wrong_token = (await c.post(base + "/mcp", json={}, headers={"Authorization": "Bearer nope"})).status_code
        async with streamablehttp_client(base + "/mcp", headers={"Authorization": "Bearer " + token}) as (r, w, _):
            async with ClientSession(r, w) as s:
                await s.initialize()
                tools = await s.list_tools()
                res = await s.call_tool("run_command", {"server": "rebex", "command": "ls"})
        async with streamablehttp_client(f"{base}/{token}/mcp") as (r, w, _):
            async with ClientSession(r, w) as s:
                await s.initialize()
                tools2 = await s.list_tools()
        return json.dumps({"no_token_status": no_token, "wrong_token_status": wrong_token,
                           "bearer_tools": len(tools.tools), "bearer_call": json.loads(res.content[0].text),
                           "secret_path_tools": len(tools2.tools)})
    finally:
        proc.terminate()


async def plugin_check():
    """Validate plugin manifests and start the server exactly as Claude Code / Codex would (sh bin/run.sh)."""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    manifests = {}
    for p in [".claude-plugin/marketplace.json", ".agents/plugins/marketplace.json",
              "plugins/ssh-connector/.claude-plugin/plugin.json", "plugins/ssh-connector/.codex-plugin/plugin.json",
              "plugins/ssh-connector/codex-mcp.json"]:
        with open(os.path.join(REPO, p)) as f:
            json.load(f)
        manifests[p] = "valid json"
    params = StdioServerParameters(
        command="sh", args=[os.path.join(PLUGIN, "bin", "run.sh")],
        env=dict(os.environ, CLAUDE_PLUGIN_DATA="/tmp/sshconn-plugin-data"))
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await asyncio.wait_for(s.initialize(), 300)
            tools = await s.list_tools()
            res = await s.call_tool("run_command", {"server": "rebex", "command": "ls"})
    return json.dumps({"manifests": manifests, "launcher_tools": len(tools.tools),
                       "launcher_call": json.loads(res.content[0].text)})


async def installer_check():
    """Install the loopback-only systemd backend; no public tunnel or root auto-login."""
    import subprocess
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    def sh(*cmd, **kw):
        return subprocess.run(list(cmd), capture_output=True, text=True, **kw)

    inst = sh("sudo", "env", f"SRC={REPO}", "bash",
              os.path.join(REPO, "install-server.sh"), timeout=900)
    sh("sudo", "cp", os.path.join(REPO, "tests", "servers.test.yaml"),
       "/etc/ssh-connector/servers.yaml")
    sh("sudo", "chown", "root:sshconn", "/etc/ssh-connector/servers.yaml")
    sh("sudo", "chmod", "640", "/etc/ssh-connector/servers.yaml")
    sh("sudo", "systemctl", "restart", "ssh-connector")
    await asyncio.sleep(8)
    token = sh("sudo", "cat", "/etc/ssh-connector/env").stdout.strip().split("=", 1)[1]
    out = {"installer_exit": inst.returncode,
           "service": sh("systemctl", "is-active", "ssh-connector").stdout.strip(),
           "tunnel_service": sh("systemctl", "is-active",
                                "ssh-connector-tunnel").stdout.strip()}
    async with streamablehttp_client(
            "http://127.0.0.1:8765/mcp",
            headers={"Authorization": "Bearer " + token}) as (r, w, _):
        async with ClientSession(r, w) as session:
            await session.initialize()
            res = await session.call_tool("run_command", {"server": "rebex",
                                                        "command": "ls"})
    out["local_call"] = json.loads(res.content[0].text)
    return json.dumps(out)


async def main():
    out = [
        await step("run_command rebex", server.run_command("rebex", "ls")),
        await step("failover", server.run_command("failover", "ls")),
        await step("run_on_group demo", server.run_on_group("demo", "pwd")),
        await step("run_snippet", server.run_snippet("rebex", "list")),
        await step("sftp_list /", server.sftp_list("rebex", "/")),
        await step("sftp_read readme", server.sftp_read("rebex", "/readme.txt", 300)),
        await step("sftp_manage stat", server.sftp_manage("rebex", "stat", "/readme.txt")),
    ]
    sh = await step("shell_open", server.shell_open("rebex"))
    out.append(sh)
    sid = sh["result"].get("shell_id") if isinstance(sh["result"], dict) else None
    if sid:
        out.append(await step("shell_send pwd", server.shell_send(sid, "pwd", 4)))
        out.append(await step("shell_close", server.shell_close(sid)))
    out.append(await step("history", server.history(10)))
    out.append(await step("list_servers", server.list_servers()))
    out.append(await step("http mode", http_check()))
    out.append(await step("plugin launcher", plugin_check()))
    out.append(await step("server installer (local-only)", installer_check()))
    # Fail CI on returned errors as well as raised exceptions. Do not print raw
    # results: install logs / HTTP clients may contain credential-bearing URLs.
    problems = []

    def require(condition, message):
        if not condition:
            problems.append(message)

    results = {item["test"]: item["result"] for item in out}
    commands = ("run_command rebex", "failover", "run_snippet")
    for name in commands:
        r = results.get(name)
        require(isinstance(r, dict) and r.get("exit_code") == 0, name)

    group = results.get("run_on_group demo")
    require(isinstance(group, list) and len(group) >= 2
            and all(isinstance(r, dict) and r.get("exit_code") == 0 for r in group),
            "run_on_group demo")

    for item in out:
        if isinstance(item["result"], dict) and "error" in item["result"]:
            problems.append(item["test"])
    require(isinstance(results.get("shell_open"), dict)
            and bool(results["shell_open"].get("shell_id")), "shell_open")
    require("shell_send pwd" in results and "shell_close" in results,
            "shell lifecycle")
    require(isinstance(results.get("sftp_list /"), list), "sftp_list")
    require(isinstance(results.get("sftp_read readme"), dict)
            and "content" in results["sftp_read readme"], "sftp_read")
    require(isinstance(results.get("sftp_manage stat"), dict)
            and "size" in results["sftp_manage stat"], "sftp_manage")

    http = results.get("http mode", {})
    require(isinstance(http, dict) and http.get("no_token_status") == 401
            and http.get("wrong_token_status") == 401
            and http.get("bearer_tools", 0) >= 48
            and http.get("secret_path_tools", 0) >= 48
            and http.get("bearer_call", {}).get("exit_code") == 0,
            "HTTP auth/MCP (48 tools)")

    plugin = results.get("plugin launcher", {})
    require(isinstance(plugin, dict) and plugin.get("launcher_tools", 0) >= 48
            and plugin.get("launcher_call", {}).get("exit_code") == 0,
            "Claude/Codex plugin launcher")

    install = results.get("server installer (local-only)", {})
    require(isinstance(install, dict) and install.get("installer_exit") == 0
            and install.get("service") == "active"
            and install.get("tunnel_service") != "active"
            and install.get("local_call", {}).get("exit_code") == 0,
            "installer local-only")

    # Only safe metadata is printed; no tokens, host credentials, URLs, or logs.
    failed = set(problems)
    # Match aggregate assertion names back to the individual safe test names.
    aliases = {
        "shell lifecycle": ("shell_send pwd", "shell_close"),
        "sftp_list": ("sftp_list /",),
        "sftp_read": ("sftp_read readme",),
        "sftp_manage": ("sftp_manage stat",),
        "HTTP auth/MCP (48 tools)": ("http mode",),
        "Claude/Codex plugin launcher": ("plugin launcher",),
        "installer local-only": ("server installer (local-only)",),
    }
    failed_tests = set(failed)
    for name in failed:
        failed_tests.update(aliases.get(name, ()))
    safe_checks = [
        {"test": item["test"], "seconds": item["seconds"],
         "passed": item["test"] not in failed_tests}
        for item in out
    ]
    # Optional separate report: only static test labels, durations, PASS/FAIL.
    # This file can safely become a GitHub Actions artifact in a PUBLIC repo.
    report_path = os.environ.get("SSH_CONNECTOR_CI_REPORT", "")
    if report_path:
        from pathlib import Path
        report_file = Path(report_path)
        report_file.parent.mkdir(parents=True, exist_ok=True)
        report_file.write_text(json.dumps({"schema_version": 1, "checks": safe_checks},
                                          indent=2, ensure_ascii=False) + "\n",
                               encoding="utf-8")
    print(json.dumps(safe_checks, indent=2, ensure_ascii=False))
    if failed:
        print("Integration checks failed: " + ", ".join(sorted(failed)), file=sys.stderr)
        raise SystemExit(1)


asyncio.run(main())
