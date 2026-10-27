import asyncio, json, os, sys, time
os.environ["SSH_CONNECTOR_CONFIG"] = os.path.join(os.path.dirname(__file__), "servers.test.yaml")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import server

async def main():
    out = []
    for name in ["rebex", "failover"]:
        t = time.time()
        r = json.loads(await server.run_command(name, "ls"))
        r["seconds"] = round(time.time() - t, 1)
        out.append(r)
    out.append(json.loads(await server.list_servers()))
    print(json.dumps(out, indent=2))

asyncio.run(main())
