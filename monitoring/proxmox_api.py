"""Opt-in Proxmox VE read-only HTTPS API client for KSSH Issue #13.

Standalone module; does not import or modify Claude Code's polling engine.
Every network call uses a fixed GET endpoint, a verified TLS context, an
explicit target allowlist, no ambient HTTP proxies, and no redirects.
"""
from __future__ import annotations

from datetime import datetime, timezone
import ipaddress
import json
import logging
import math
import os
import re
import socket
import ssl
import urllib.error
import urllib.parse
import urllib.request
from uuid import uuid4

from monitoring.proxmox_format import normalize

LOG = logging.getLogger(__name__)
LOG.addHandler(logging.NullHandler())
DNS_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
NODE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]{0,62}$")
ENV = re.compile(r"^[A-Z_][A-Z0-9_]*$")
TOKEN_ID = re.compile(r"^[^\s!@=]+@[^\s!@=]+![^\s!@=]+$")
MAX_BODY = 2 * 1024 * 1024


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def canonical_host(value):
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError("Invalid hostname")
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    if any(ch in value for ch in "/?#@%\\"):
        raise ValueError("Invalid hostname")
    try:
        return ipaddress.ip_address(value).compressed.lower()
    except ValueError:
        pass
    hostname = value.lower()
    labels = hostname.split(".")
    if len(hostname) > 253 or not all(DNS_LABEL.fullmatch(x) for x in labels):
        raise ValueError("Invalid hostname")
    return hostname


def validate_origin(url):
    if not isinstance(url, str):
        raise ValueError("API origin must be HTTPS")
    try:
        p = urllib.parse.urlsplit(url)
        port, host = p.port, p.hostname
    except ValueError:
        raise ValueError("Invalid URL") from None
    if (p.scheme != "https" or not host or port != 8006 or
            p.username is not None or p.password is not None or
            p.path not in ("", "/") or p.query or p.fragment):
        raise ValueError("Require HTTPS origin on port 8006, no path or credentials")
    host = canonical_host(host)
    return ("https://[" + host + "]:8006" if ":" in host else
            "https://" + host + ":8006"), host


def validated_node(value):
    if not isinstance(value, str) or not NODE.fullmatch(value):
        raise ValueError("Invalid node name")
    # No arbitrary URL paths; encoded name is a single path component.
    return urllib.parse.quote(value, safe="")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


class ProxmoxReadOnlyClient:
    """Authenticated GET-only API collector.

    Credentials are *names* of environment variables, not literals.
    Constructing a client makes no network connection. A CA bundle can be
    supplied for private PKI; verify_mode and hostname checks stay enabled.
    """

    def __init__(self, base_url, *, allowed_hosts,
                 token_id_env="KSSH_PROXMOX_TOKEN_ID",
                 token_secret_env="KSSH_PROXMOX_TOKEN_SECRET",
                 timeout=5.0, ca_bundle=None):
        self.base_url, hostname = validate_origin(base_url)
        if not allowed_hosts or isinstance(allowed_hosts, str):
            raise ValueError("An explicit list of allowed_hosts is required")
        if hostname not in {canonical_host(x) for x in allowed_hosts}:
            raise ValueError("Target is not allowlisted")
        if not ENV.fullmatch(token_id_env) or not ENV.fullmatch(token_secret_env):
            raise ValueError("Credentials must be referenced by environment name")
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 60:
            raise ValueError("Timeout must be > 0 and <= 60 seconds")
        self.timeout = float(timeout)
        self.token_id_env = token_id_env
        self.token_secret_env = token_secret_env
        self.tls_context = ssl.create_default_context(cafile=ca_bundle)
        # No proxies or HTTPRedirectHandler default; only our rejecting handler.
        self._opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            urllib.request.HTTPSHandler(context=self.tls_context),
            NoRedirect(),
        )

    def _result(self, node, resource, data=None, error_code=None,
                status=None, capabilities=None):
        state = status or ("OK" if error_code is None else "UNAVAILABLE")
        result = {
            "ok": error_code is None,
            "status": state,
            "node": node,
            "resource": resource,
            "timestamp_utc": utc_now(),
            "data": data if error_code is None else None,
            "error_code": error_code,
            "source": "proxmox-ve-api",
            "capabilities": capabilities or {},
        }
        # Log only safe categories, never raw exceptions, token or request URL.
        LOG.info(json.dumps({
            "event": "proxmox_api_read",
            "timestamp_utc": result["timestamp_utc"],
            "correlation_id": uuid4().hex,
            "node": node, "resource": resource,
            "status": state, "error_code": error_code,
        }, separators=(",", ":")))
        return result

    def _authorization(self):
        token_id = os.environ.get(self.token_id_env, "")
        secret = os.environ.get(self.token_secret_env, "")
        if (not TOKEN_ID.fullmatch(token_id) or not secret or
                "\r" in secret or "\n" in secret):
            return None
        return "PVEAPIToken=" + token_id + "=" + secret

    @staticmethod
    def _http_error(code):
        return {401: "AUTH_FAILED", 403: "PERMISSION_DENIED",
                404: "RESOURCE_NOT_FOUND"}.get(code, "UNAVAILABLE")

    def _get(self, node, resource, fixed_path, expected_type):
        auth = self._authorization()
        if auth is None:
            return self._result(node, resource, error_code="UNAVAILABLE")
        request = urllib.request.Request(
            self.base_url + "/api2/json/" + fixed_path,
            headers={"Accept": "application/json", "Authorization": auth},
            method="GET",
        )
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                if response.status != 200:
                    return self._result(
                        node, resource, error_code=self._http_error(response.status))
                raw = response.read(MAX_BODY + 1)
                if len(raw) > MAX_BODY:
                    return self._result(
                        node, resource, error_code="MALFORMED_RESPONSE")
            payload = json.loads(raw.decode("utf-8"))
            if (not isinstance(payload, dict) or "data" not in payload or
                    type(payload["data"]) is not expected_type):
                raise ValueError("Malformed JSON API envelope")
            data, caps = normalize(resource, payload["data"])
            return self._result(node, resource, data=data, capabilities=caps)
        except urllib.error.HTTPError as exc:
            return self._result(node, resource, error_code=self._http_error(exc.code))
        except (ssl.SSLError, ssl.CertificateError):
            return self._result(node, resource, error_code="TLS_ERROR")
        except urllib.error.URLError as exc:
            code = ("TLS_ERROR" if isinstance(
                exc.reason, (ssl.SSLError, ssl.CertificateError)
            ) else "API_UNREACHABLE")
            return self._result(node, resource, error_code=code)
        except (TimeoutError, socket.timeout, ConnectionError, OSError):
            return self._result(node, resource, error_code="API_UNREACHABLE")
        except (ValueError, TypeError, UnicodeError):
            return self._result(node, resource, error_code="MALFORMED_RESPONSE")

    def version(self):
        return self._get(None, "api_version", "version", dict)

    def discover_nodes(self):
        return self._get(None, "nodes", "nodes", list)

    def node_status(self, node):
        name = validated_node(node)
        return self._get(node, "node_status", f"nodes/{name}/status", dict)

    def storage(self, node):
        name = validated_node(node)
        return self._get(node, "storage", f"nodes/{name}/storage", list)

    def qemu(self, node):
        name = validated_node(node)
        return self._get(node, "qemu", f"nodes/{name}/qemu", list)

    def lxc(self, node):
        name = validated_node(node)
        return self._get(node, "lxc", f"nodes/{name}/lxc", list)

    def backup_tasks(self, node):
        name = validated_node(node)
        # Proxmox VE task history, NOT the separate PBS product/API.
        return self._get(
            node, "backup_tasks",
            f"nodes/{name}/tasks?typefilter=vzdump&limit=100", list)

    def snapshot(self, node):
        """Polling adapter contract. Do not confuse partial errors with STOPPED."""
        validated_node(node)
        parts = {
            "api_version": self.version(),
            "node_status": self.node_status(node),
            "storage": self.storage(node),
            "qemu": self.qemu(node),
            "lxc": self.lxc(node),
            "backup_tasks": self.backup_tasks(node),
        }
        passed = sum(x["ok"] for x in parts.values())
        data = {
            "resources": {name: x["data"] if x["ok"] else None
                          for name, x in parts.items()},
            "errors": {name: x["error_code"] for name, x in parts.items()
                       if not x["ok"]},
        }
        caps = {name: x["ok"] for name, x in parts.items()}
        caps["network_metrics"] = any(
            x["capabilities"].get("network_metrics", False)
            for x in parts.values())
        caps["pbs_health"] = False
        status = ("OK" if passed == len(parts) else
                  "DEGRADED" if passed else "UNAVAILABLE")
        return self._result(
            node, "snapshot", data=data if passed else None,
            error_code="UNAVAILABLE" if not passed else None,
            status=status, capabilities=caps)
