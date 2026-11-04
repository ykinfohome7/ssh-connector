"""Copy the read-only SNMP library from monitoring/ into the installable plugin.

Why: Claude Code / Codex install only the folder plugins/ssh-connector, so the
plugin cannot import the repository-level monitoring/ package. The canonical
code stays in monitoring/; this script copies it to plugins/ssh-connector/kssh_snmp/.

Run:         python3 scripts/sync_plugin_snmp.py
Check only:  python3 scripts/sync_plugin_snmp.py --check   (exit 1 if copies differ)

Защо: инсталира се само папката на плъгина, затова SNMP кодът се копира в нея.
Оригиналът остава в monitoring/; тестът проверява, че копията са еднакви.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "monitoring"
DST = ROOT / "plugins" / "ssh-connector" / "kssh_snmp"
FILES = ["errors.py", "logutil.py", "snmp_client.py", "snmp_interfaces.py", "snmp_adapters.py"]
HEADER = "# GENERATED COPY of monitoring/{name} - edit the original, then run scripts/sync_plugin_snmp.py\n"
INIT = ('"""Read-only SNMP library vendored from monitoring/ (see scripts/sync_plugin_snmp.py).\n\n'
        'No SNMP SET exists in this package."""\n')


def expected() -> dict[str, str]:
    out = {"__init__.py": INIT}
    for name in FILES:
        out[name] = HEADER.format(name=name) + (SRC / name).read_text(encoding="utf-8")
    return out


def main(argv: list[str]) -> int:
    want = expected()
    if "--check" in argv:
        stale = [n for n, text in want.items()
                 if not (DST / n).is_file() or (DST / n).read_text(encoding="utf-8") != text]
        extra = sorted(p.name for p in DST.glob("*.py") if p.name not in want) if DST.is_dir() else []
        if stale or extra:
            print(f"kssh_snmp out of sync: stale={stale} extra={extra}. Run scripts/sync_plugin_snmp.py")
            return 1
        print("kssh_snmp in sync")
        return 0
    DST.mkdir(parents=True, exist_ok=True)
    for name, text in want.items():
        (DST / name).write_text(text, encoding="utf-8")
    print(f"synced {len(want)} files into {DST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
