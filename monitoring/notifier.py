"""Alert delivery: stdout always, optional HTTPS webhook, with rate limiting.

Safety rules:
* HTTPS only, redirects refused (no downgrade, no hop to another host).
* Optional host allowlist ``KSSH_MONITOR_WEBHOOK_HOSTS`` (comma separated).
  When set, the webhook host must match exactly.
* URLs with embedded credentials (``user:pass@``) are refused.
* The URL is registered as a secret, so it never appears in logs.
* Per-key cooldown and a global hourly cap stop alert storms.
* Delivery failures are reported by type only; the monitor never crashes
  because a webhook is down.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Callable

from .logutil import register_secret


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse all redirects so an HTTPS webhook can never be downgraded."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


WEBHOOK_OPENER = urllib.request.build_opener(_NoRedirect)


def validate_webhook_url(url: str, allowed_hosts: set[str] | None = None) -> str | None:
    """Return None when the URL is acceptable, else a short reason."""
    try:
        parts = urllib.parse.urlsplit(url)
    except ValueError:
        return "invalid URL"
    if parts.scheme != "https":
        return "HTTPS required"
    if not parts.hostname:
        return "missing host"
    if parts.username or parts.password:
        return "credentials in URL are not allowed"
    if any(c in url for c in "\r\n\t "):
        return "control characters in URL"
    if allowed_hosts is not None and parts.hostname.lower() not in allowed_hosts:
        return "webhook host not in KSSH_MONITOR_WEBHOOK_HOSTS"
    return None


@dataclass
class Notifier:
    url: str | None = None
    allowed_hosts: set[str] | None = None
    cooldown_s: float = 300.0          # same key at most once per cooldown (DOWN and RECOVERED are separate keys)
    max_per_hour: int = 30
    timeout_s: float = 5.0
    clock: Callable[[], float] = time.monotonic
    printer: Callable[[str], None] = field(default=lambda m: print(m, flush=True))
    opener: object = None
    _last: dict = field(default_factory=dict, init=False, repr=False)
    _sent: list = field(default_factory=list, init=False, repr=False)
    suppressed: int = field(default=0, init=False)

    @classmethod
    def from_env(cls, environ: dict | None = None, **kwargs) -> "Notifier":
        env = os.environ if environ is None else environ
        url = env.get("KSSH_MONITOR_WEBHOOK") or None
        hosts = env.get("KSSH_MONITOR_WEBHOOK_HOSTS")
        allowed = {h.strip().lower() for h in hosts.split(",") if h.strip()} if hosts else None
        if url:
            register_secret(url)
        return cls(url=url, allowed_hosts=allowed, **kwargs)

    def _allowed_now(self, key: str) -> bool:
        now = self.clock()
        self._sent = [t for t in self._sent if now - t < 3600]
        last = self._last.get(key)
        if last is not None and now - last < self.cooldown_s:
            return False
        if len(self._sent) >= self.max_per_hour:
            return False
        self._last[key] = now
        self._sent.append(now)
        return True

    def send(self, event: dict) -> str:
        """Deliver one event. Returns 'sent', 'printed', 'suppressed' or 'failed:<reason>'."""
        key = f"{event.get('check')}|{event.get('event')}"
        if not self._allowed_now(key):
            self.suppressed += 1
            return "suppressed"
        text = (f"{event.get('ts_utc', '')} KSSH monitor {event.get('event')}: {event.get('check')}"
                + (f" ({event['error_code']})" if event.get("error_code") else ""))
        self.printer(text)
        if not self.url:
            return "printed"
        reason = validate_webhook_url(self.url, self.allowed_hosts)
        if reason:
            self.printer(f"Webhook skipped: {reason}")
            return f"failed:{reason}"
        body = json.dumps({"text": text, "event": {k: event.get(k) for k in
                           ("ts_utc", "check", "event", "error_code", "status")}}).encode("utf-8")
        request = urllib.request.Request(self.url, data=body, method="POST",
                                         headers={"Content-Type": "application/json"})
        try:
            with (self.opener or WEBHOOK_OPENER).open(request, timeout=self.timeout_s) as response:
                response.read(256)
            return "sent"
        except urllib.error.HTTPError as exc:
            self.printer("Webhook delivery failed (details hidden)")
            return f"failed:http_{exc.code}"
        except Exception as exc:
            self.printer("Webhook delivery failed (details hidden)")
            return f"failed:{type(exc).__name__}"
