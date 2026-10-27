import asyncio, json, os, sys, time
os.environ["SSH_CONNECTOR_CONFIG"] = os.path.join(os.path.dirname(__file__), "servers.test.yaml")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
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
    print(json.dumps(out, indent=2, ensure_ascii=False))


asyncio.run(main())
