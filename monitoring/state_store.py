"""Persistent monitor state: versioned, private, atomic, single-writer.

Schema v2::

    {"schema": 2,
     "checks":  {"<target>/<check>": {"healthy": bool, "pending": int, "since_utc": str}},
     "samples": {"<target>": <serialised DeviceSample>},
     "flaps":   {"<target>/<ifname>": [epoch, ...]}}

* v1 files (the flat dict written by the first MVP) are migrated on load.
* A corrupt or unreadable file is moved aside to ``<name>.corrupt-<UTC>``
  (never silently deleted) and the monitor starts from an empty state.
* ``fcntl.flock`` on ``<name>.lock`` prevents two monitor processes from
  writing the same file. If the lock is held, ``StateLocked`` is raised.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

SCHEMA = 2
MAX_STATE_BYTES = 8 * 1024 * 1024  # refuse to load absurdly large files


class StateLocked(RuntimeError):
    """Another process holds the state lock."""


def empty_state() -> dict:
    return {"schema": SCHEMA, "checks": {}, "samples": {}, "flaps": {}}


def migrate(raw: Any) -> dict:
    """Return a v2 state from any previously written format."""
    if not isinstance(raw, dict):
        raise ValueError("state root must be an object")
    if raw.get("schema") == SCHEMA:
        out = empty_state()
        for key in ("checks", "samples", "flaps"):
            if isinstance(raw.get(key), dict):
                out[key] = raw[key]
        return out
    if "schema" in raw:
        raise ValueError(f"unsupported state schema {raw.get('schema')!r}")
    # v1: {"name/check": {"healthy": .., "pending": .., "seen": ..}}
    out = empty_state()
    for key, entry in raw.items():
        if isinstance(entry, dict) and "healthy" in entry:
            out["checks"][str(key)] = {
                "healthy": bool(entry.get("healthy", True)),
                "pending": int(entry.get("pending", 0) or 0),
            }
    return out


def write_private_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    fd = os.open(tmp, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as file:
        json.dump(data, file, sort_keys=True)
        file.flush()
        os.fsync(file.fileno())
    os.replace(tmp, path)
    try:
        dir_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except OSError:
        pass


class StateStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock_fd: int | None = None
        self.recovered_from: str | None = None  # set when a corrupt file was moved aside

    # ------------------------------------------------------------------ lock
    def acquire(self) -> "StateStore":
        try:
            import fcntl
        except ImportError:  # non-POSIX: no lock available, document and continue
            return self
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path.with_name(self.path.name + ".lock"), os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(fd)
            raise StateLocked("another monitor process is using this state file") from None
        self._lock_fd = fd
        return self

    def release(self) -> None:
        if self._lock_fd is not None:
            try:
                import fcntl
                fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
            finally:
                os.close(self._lock_fd)
                self._lock_fd = None

    def __enter__(self):
        return self.acquire()

    def __exit__(self, *exc):
        self.release()

    # ------------------------------------------------------------------ io
    def load(self) -> dict:
        try:
            if self.path.stat().st_size > MAX_STATE_BYTES:
                raise ValueError("state file too large")
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            return migrate(raw)
        except FileNotFoundError:
            return empty_state()
        except (OSError, ValueError, TypeError) as exc:
            stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
            aside = self.path.with_name(f"{self.path.name}.corrupt-{stamp}")
            try:
                os.replace(self.path, aside)
                self.recovered_from = f"{aside.name} ({type(exc).__name__})"
            except OSError:
                self.recovered_from = f"unreadable ({type(exc).__name__})"
            return empty_state()

    def save(self, state: dict) -> None:
        write_private_atomic(self.path, state)
