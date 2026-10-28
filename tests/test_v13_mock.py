"""Mock tests for v1.3 commands (no network): server_get, server_rename, server_set_primary,
server_failover, health_status, version_info, help.
Макетни тестове за командите на v1.3 — без реална мрежа, SSH връзката е подменена."""
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
            "defaults": {"connect_timeout": 1, "retries": 1},
            "servers": {
                "BGDB": {"hosts": ["100.65.111.82", "bgdb.example.com"], "user": "bgadmin",
                         "password_env": "BGDB_SSH_PASSWORD", "aliases": ["bg"]},
                "web1": {"hosts": ["10.0.0.5"], "user": "root"},
            },
        }))
        os.environ["SSH_CONNECTOR_CONFIG"] = str(path)
        import server

        async def no_network(*args, **kwargs):  # подменяме реалната SSH връзка (mock)
            raise OSError("mock: no network")
        server.asyncssh.connect = no_network

        g = json.loads(await server.server_get("bg"))
        assert g["name"] == "BGDB" and g["primary"] == "100.65.111.82", g
        assert "password" not in g and g["password_env"] == "BGDB_SSH_PASSWORD", g  # без тайни

        r = json.loads(await server.server_set_primary("BGDB", "bgdb.example.com"))
        assert r["primary"] == "bgdb.example.com", r
        assert yaml.safe_load(path.read_text())["servers"]["BGDB"]["hosts"][0] == "bgdb.example.com"
        assert "error" in json.loads(await server.server_set_primary("BGDB", "192.0.2.9"))

        r = json.loads(await server.server_rename("web1", "web-main"))
        assert r == {"renamed": "web1", "to": "web-main"}, r
        assert list(yaml.safe_load(path.read_text())["servers"]) == ["BGDB", "web-main"]
        assert "error" in json.loads(await server.server_rename("web-main", "bgdb"))   # дубликат
        assert "error" in json.loads(await server.server_rename("web-main", "1bad"))   # невалидно име

        f = json.loads(await server.server_failover("web-main"))
        assert "only one address" in f["error"], f
        f = json.loads(await server.server_failover("BGDB"))
        assert "failover failed" in f["error"], f

        h = json.loads(await server.health_status())
        assert h["config_ok"] and set(h["servers"]) == {"BGDB", "web-main"}, h

        v = json.loads(await server.version_info())
        assert v["version"] and v["commit"] and "help" in v["commands"], v

        assert len(json.loads(await server.help())) == len(server.HELP)
        assert json.loads(await server.help("server_get"))["example"] == {"name": "BGDB"}
        assert "error" in json.loads(await server.help("nope"))
    print("v1.3 mock tests PASSED")


if __name__ == "__main__":
    asyncio.run(main())
