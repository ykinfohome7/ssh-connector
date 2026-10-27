"""Local tests for SSH backend host CRUD, aliases and validation (no network)."""
import asyncio
import json
import os
import pathlib
import sys
import tempfile
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins" / "ssh-connector"))


async def main():
    with tempfile.TemporaryDirectory() as directory:
        path = pathlib.Path(directory) / "servers.yaml"
        path.write_text(yaml.safe_dump({
            "defaults": {"connect_timeout": 2, "retries": 1},
            "servers": {"rebex": {"hosts": ["test.rebex.net"], "user": "demo", "tags": ["demo"]}},
        }))
        os.environ["SSH_CONNECTOR_CONFIG"] = str(path)
        import server

        out = json.loads(await server.server_add(
            "BGDB-Codespaces", ["100.65.111.82"], "bgadmin", 2222,
            ["github", "tailscale"], ["github_bgdb"], "BGDB_SSH_PASSWORD",
        ))
        assert out.get("added") == "BGDB-Codespaces", out
        assert server.srv("github_bgdb").cfg["port"] == 2222
        assert server.srv("github_bgdb").cfg["hosts"] == ["100.65.111.82"]
        assert server.srv("rebex").cfg["user"] == "demo"
        assert yaml.safe_load(path.read_text())["servers"]["BGDB-Codespaces"]["password_env"] == "BGDB_SSH_PASSWORD"

        duplicate = json.loads(await server.server_add("github_bgdb", ["127.0.0.1"]))
        assert "error" in duplicate, duplicate

        changed = json.loads(await server.server_update(
            "github_bgdb", hosts=["bgdb.example.com", "100.65.111.82"], port=2202,
        ))
        assert changed.get("updated") == "BGDB-Codespaces", changed
        assert server.srv("BGDB-Codespaces").cfg["port"] == 2202
        assert server.srv("BGDB-Codespaces").cfg["hosts"][0] == "bgdb.example.com"

        refused = json.loads(await server.server_remove("github_bgdb"))
        assert refused.get("confirmation_required"), refused
        removed = json.loads(await server.server_remove("github_bgdb", True))
        assert removed.get("removed") == "BGDB-Codespaces", removed
        assert "BGDB-Codespaces" not in yaml.safe_load(path.read_text())["servers"]
        assert "rebex" in server.SERVERS
    print("SSH profile CRUD / alias / validation tests PASSED")


if __name__ == "__main__":
    asyncio.run(main())
