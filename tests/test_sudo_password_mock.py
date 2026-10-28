"""Mock tests for v1.3.2 sudo_password (no network): generator, prompt page, profile, run_command(sudo), shell.
Макетни тестове за sudo паролата — без реална мрежа; сървърът е подменен и проверява паролата сам."""
import asyncio
import json
import os
import pathlib
import sys
import tempfile

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins" / "ssh-connector"))

REAL_PW = "Very-Secret-Pass-123"           # „истинската“ парола на макетния сървър


class FakeServerRun:
    """Подменя Server.run: приема sudo -S само с правилната парола; chpasswd сменя паролата."""
    def __init__(self):
        self.pw = REAL_PW
        self.seen = []                     # какви команди са минали (без stdin)

    async def __call__(self, srv_self, command, timeout, input=None):
        self.seen.append(command)
        if command.startswith("sudo -n"):
            return {"exit_code": 1, "stdout": "", "stderr": "sudo: a password is required\n"}
        first = (input or "").split("\n")[0]
        if first != self.pw:
            return {"exit_code": 1, "stdout": "", "stderr": "sudo: 1 incorrect password attempt\n"}
        if "chpasswd" in command:
            self.pw = input.split("\n")[1].split(":", 1)[1]
        return {"exit_code": 0, "stdout": "root\n", "stderr": ""}


async def call_page(server, path, method="GET", body=b""):
    """Пуска еднократната страница като ASGI заявка и връща (статус, html)."""
    out = {}
    msgs = [{"type": "http.request", "body": body, "more_body": False}]

    async def receive():
        return msgs.pop(0)

    async def send(m):
        if m["type"] == "http.response.start":
            out["status"] = m["status"]
            out["headers"] = dict(m["headers"])
        else:
            out["body"] = m["body"].decode()
    await server.sudo_page({"type": "http", "path": path, "method": method}, receive, send)
    return out["status"], out["body"], out["headers"]


async def main():
    with tempfile.TemporaryDirectory() as directory:
        path = pathlib.Path(directory) / "servers.yaml"
        path.write_text(yaml.safe_dump({"servers": {"BGDB": {"hosts": ["100.65.111.82"], "user": "bgadmin"}}}))
        os.environ["SSH_CONNECTOR_CONFIG"] = str(path)
        os.environ["SSH_CONNECTOR_PUBLIC_URL"] = "https://bgssh.example.ts.net"
        import server
        fake = FakeServerRun()
        server.Server.run = lambda self, c, t, input=None: fake(self, c, t, input)

        # 1) без избрана парола: sudo не виси, а казва „избери парола“ с трите варианта
        r = json.loads(await server.run_command("BGDB", "whoami", sudo=True))
        assert r["sudo_password_required"] and set(r["choose_one"]) == {"prompt", "profile", "generate"}, r

        # 2) генераторът: дължината и символите ги избира потребителят; без тях — отказ
        assert "error" in json.loads(await server.sudo_password("BGDB", "generate"))
        assert "error" in json.loads(await server.sudo_password("BGDB", "generate", length=8, charset="lower"))
        assert "error" in json.loads(await server.sudo_password("BGDB", "generate", length=40, charset="emoji"))
        for length, cs in [(17, "digits,upper"), (64, "lower,upper,digits,symbols"), (128, "symbols")]:
            pw = server._generate_password(length, cs)
            assert len(pw) == length
            for c in cs.split(","):
                assert any(ch in server.SUDO_CHARSETS[c] for ch in pw), (cs, pw)
            assert all(any(ch in server.SUDO_CHARSETS[c] for c in cs.split(",")) for ch in pw)

        # 3) prompt: еднократна връзка; паролата не е в отговора към чата
        r = json.loads(await server.sudo_password("BGDB", "prompt"))
        link = r["link"]
        assert link.startswith("https://bgssh.example.ts.net/sudo/") and REAL_PW not in json.dumps(r)
        page = link[len("https://bgssh.example.ts.net"):]
        st, html, hdr = await call_page(server, page)
        assert st == 200 and "type=password" in html and hdr[b"cache-control"] == b"no-store"
        st, html, _ = await call_page(server, page, "POST", b"pw=wrong")
        assert st == 403 and "BGDB" not in server.SUDO_SECRETS             # грешна — не се пази
        st, html, _ = await call_page(server, page, "POST", ("pw=" + REAL_PW).encode())
        assert st == 200 and server.SUDO_SECRETS["BGDB"] == REAL_PW
        st, _, _ = await call_page(server, page)
        assert st == 410                                                    # еднократна: вече не работи
        r = json.loads(await server.run_command("BGDB", "whoami", sudo=True))
        assert r["exit_code"] == 0 and r["stdout"] == "root\n", r
        assert all(REAL_PW not in c for c in fake.seen)                      # паролата никога не е в командата
        assert all(REAL_PW not in json.dumps(h) for h in server.HISTORY)     # нито в историята
        s = json.loads(await server.sudo_password("BGDB", "status"))
        assert s["source"] == "memory" and REAL_PW not in json.dumps(s), s

        # 4) generate + apply: нищо не се сменя, преди потребителят да натисне „Записах я“
        r = json.loads(await server.sudo_password("BGDB", "generate", length=37, charset="lower,digits,symbols",
                                                  apply_on_server=True))
        page = r["link"][len("https://bgssh.example.ts.net"):]
        assert fake.pw == REAL_PW and "value" not in r
        st, html, _ = await call_page(server, page)
        assert st == 200 and "<code>" in html and fake.pw == REAL_PW
        st, html, _ = await call_page(server, page, "POST")
        assert st == 200 and fake.pw != REAL_PW and len(fake.pw) == 37 and server.SUDO_SECRETS["BGDB"] == fake.pw
        r = json.loads(await server.run_command("BGDB", "whoami", sudo=True))
        assert r["exit_code"] == 0, r

        # 5) profile: само ИМЕТО на променливата отива в профила, никога стойността
        os.environ["BGDB_SUDO_PW"] = fake.pw
        r = json.loads(await server.sudo_password("BGDB", "profile", password_env="BGDB_SUDO_PW"))
        assert r["source"] == "profile" and r["verified"], r
        assert "BGDB" not in server.SUDO_SECRETS
        saved = path.read_text()
        assert "BGDB_SUDO_PW" in saved and fake.pw not in saved
        assert "error" in json.loads(await server.sudo_password("BGDB", "profile", password_env="not a name"))

        # 6) грешна парола в профила -> ясен отговор, а не висене
        os.environ["BGDB_SUDO_PW"] = "nope"
        r = json.loads(await server.run_command("BGDB", "whoami", sudo=True))
        assert r.get("sudo_password_wrong") and r["sudo_password_required"], r

        # 7) clear
        assert json.loads(await server.sudo_password("BGDB", "clear"))["server"] == "BGDB"
        assert "error" in json.loads(await server.sudo_password("BGDB", "bogus"))

        # 8) терминалът разпознава въпроса за парола
        assert server._SUDO_PROMPT.search("...\r\n[sudo] password for bgadmin: ")
        assert not server._SUDO_PROMPT.search("bgadmin@host:~$ ")
        print("sudo_password mock tests: OK")


if __name__ == "__main__":
    asyncio.run(main())
