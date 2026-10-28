"""Offline safety tests for the ClouDNS boot updater. No DNS requests are sent."""
import os
import pathlib
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "cloudns-ddns.sh"
FAKE_URL = "https://ipv4.cloudns.net/api/dynamicURL/?q=FAKE_TEST_TOKEN_012345"

with tempfile.TemporaryDirectory() as work:
    root = pathlib.Path(work)
    fake_curl = root / "curl"
    marker = root / "called"
    fake_curl.write_text(
        "#!/usr/bin/env python3\n"
        "import os, sys, pathlib\n"
        "pathlib.Path(os.environ['FAKE_CURL_CALLED']).write_text('yes')\n"
        "args=sys.argv[1:]\n"
        "assert '--config' in args and args[args.index('--config')+1]=='-'\n"
        "config=sys.stdin.read()\n"
        "assert 'FAKE_TEST_TOKEN_012345' in config\n"
        "out=args[args.index('--output')+1]\n"
        "pathlib.Path(out).write_text(os.environ.get('FAKE_CURL_REPLY','OK'))\n"
        "sys.exit(int(os.environ.get('FAKE_CURL_EXIT','0')))\n"
    )
    fake_curl.chmod(0o755)

    def run(**updates):
        marker.unlink(missing_ok=True)
        env = dict(os.environ)
        env.pop("GITHUB_ACTIONS", None)
        env.update({
            "PATH": str(root) + os.pathsep + env["PATH"],
            "FAKE_CURL_CALLED": str(marker),
            "BGSSH_DDNS_ENABLED": "0",
            "BGSSH_DDNS_PUBLIC_HTTPS_READY": "0",
            "CLOUDNS_DDNS_URL": FAKE_URL,
        })
        env.update(updates)
        p = subprocess.run(["bash", str(SCRIPT)], capture_output=True, text=True, env=env, timeout=5)
        assert "FAKE_TEST_TOKEN" not in p.stdout + p.stderr
        return p, marker.exists()

    p, called = run(GITHUB_ACTIONS="true", BGSSH_DDNS_ENABLED="1",
                    BGSSH_DDNS_PUBLIC_HTTPS_READY="1")
    assert p.returncode == 0 and not called and "GitHub Actions" in p.stdout

    p, called = run()
    assert p.returncode == 0 and not called and "not enabled" in p.stdout

    p, called = run(BGSSH_DDNS_ENABLED="1")
    assert p.returncode != 0 and not called and "not been confirmed" in p.stdout

    p, called = run(BGSSH_DDNS_ENABLED="1", BGSSH_DDNS_PUBLIC_HTTPS_READY="1",
                    CLOUDNS_DDNS_URL="http://example.invalid/")
    assert p.returncode != 0 and not called

    p, called = run(BGSSH_DDNS_ENABLED="1", BGSSH_DDNS_PUBLIC_HTTPS_READY="1")
    assert p.returncode == 0 and called and "OK:" in p.stdout

    p, called = run(BGSSH_DDNS_ENABLED="1", BGSSH_DDNS_PUBLIC_HTTPS_READY="1",
                    FAKE_CURL_REPLY="ERROR")
    assert p.returncode != 0 and called and "did not confirm OK" in p.stdout

    p, called = run(BGSSH_DDNS_ENABLED="1", BGSSH_DDNS_PUBLIC_HTTPS_READY="1",
                    FAKE_CURL_EXIT="22")
    assert p.returncode != 0 and called and "request failed" in p.stdout

print("ClouDNS DDNS boot safety tests PASSED")
