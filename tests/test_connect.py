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
    print(json.dumps(out, indent=2, ensure_ascii=False))


asyncio.run(main())
