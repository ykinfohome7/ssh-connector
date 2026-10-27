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
    """Run install-server.sh like a user would on a fresh server, then use it locally and over the public tunnel."""
    import re
    import subprocess
    import httpx
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    def sh(*cmd, **kw):
        return subprocess.run(list(cmd), capture_output=True, text=True, **kw)

    inst = sh("sudo", "env", f"SRC={REPO}", "bash", os.path.join(REPO, "install-server.sh"), timeout=900)
    sh("sudo", "cp", os.path.join(REPO, "tests", "servers.test.yaml"), "/etc/ssh-connector/servers.yaml")
    sh("sudo", "chown", "root:sshconn", "/etc/ssh-connector/servers.yaml")
    sh("sudo", "chmod", "640", "/etc/ssh-connector/servers.yaml")
    sh("sudo", "systemctl", "restart", "ssh-connector")
    await asyncio.sleep(8)
    token = sh("sudo", "cat", "/etc/ssh-connector/env").stdout.strip().split("=", 1)[1]
    info = sh("sudo", "/usr/local/bin/ssh-connector-info").stdout
    m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", info)
    url = m.group(0) if m else None
    out = {"installer_exit": inst.returncode, "installer_tail": inst.stdout[-600:] + inst.stderr[-600:],
           "service": sh("systemctl", "is-active", "ssh-connector").stdout.strip(),
           "tunnel_service": sh("systemctl", "is-active", "ssh-connector-tunnel").stdout.strip(),
           "public_url_found": bool(url)}
    async with streamablehttp_client("http://127.0.0.1:8765/mcp", headers={"Authorization": "Bearer " + token}) as (r, w, _):
        async with ClientSession(r, w) as s:
            await s.initialize()
            res = await s.call_tool("run_command", {"server": "rebex", "command": "ls"})
    out["local_call"] = json.loads(res.content[0].text)
    if url:
        status = None
        for _ in range(20):  # quick tunnels need a few seconds to become reachable
            try:
                async with httpx.AsyncClient(timeout=10) as c:
                    status = (await c.post(url + "/mcp", json={})).status_code
                if status == 401:
                    break
            except Exception as e:
                status = f"{type(e).__name__}"
            await asyncio.sleep(3)
        out["public_without_token"] = status
        async with streamablehttp_client(f"{url}/{token}/mcp") as (r, w, _):
            async with ClientSession(r, w) as s:
                await s.initialize()
                res = await s.call_tool("run_command", {"server": "rebex", "command": "ls"})
        out["public_chatgpt_style_call"] = json.loads(res.content[0].text)
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
    out.append(await step("server installer + public tunnel", installer_check()))
    print(json.dumps(out, indent=2, ensure_ascii=False))


asyncio.run(main())
