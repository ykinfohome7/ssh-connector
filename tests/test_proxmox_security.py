"""Offline negative/security tests for the Proxmox API collector."""
import io
import json
import logging
import os
import ssl
import unittest
import urllib.error
from unittest.mock import patch

from monitoring.proxmox_api import (
    NoRedirect, ProxmoxReadOnlyClient, canonical_host, validate_origin
)


class SecurityTests(unittest.TestCase):
    def client(self, **kwargs):
        return ProxmoxReadOnlyClient(
            "https://proxmox.example:8006",
            allowed_hosts=["proxmox.example"], **kwargs)

    def test_https_only_explicit_origin_validation(self):
        invalid = [
            "http://proxmox.example:8006", "https://proxmox.example",
            "https://proxmox.example:443", "https://other.example:8006",
            "https://proxmox.example:8006/api2/json",
            "https://proxmox.example:8006?q=1",
            "https://proxmox.example:8006/#fragment",
            "https://user:pass@proxmox.example:8006",
            "https://proxmox.example:8006@attacker.invalid:8006",
            "https://proxmox.example:8006\\@attacker.invalid",
        ]
        for url in invalid:
            with self.subTest(url=url), self.assertRaises(ValueError):
                ProxmoxReadOnlyClient(
                    url, allowed_hosts=["proxmox.example"])

    def test_origin_can_be_valid_but_target_is_blocked(self):
        for allowed in ([], ["other.invalid"], "proxmox.example"):
            with self.subTest(allowed=allowed), self.assertRaises(ValueError):
                ProxmoxReadOnlyClient(
                    "https://proxmox.example:8006", allowed_hosts=allowed)
        self.assertEqual(
            validate_origin("https://PROXMOX.EXAMPLE:8006/")[1],
            "proxmox.example")

    def test_hostname_validation_rejects_injection(self):
        for value in ("", "bad host", "a..b", "-bad.example", "bad-.example",
                      "bad/evil", "example.com@", "example.com%0d", "host:8006",
                      "example.com.", "ü.example", "example.com\\evil"):
            with self.subTest(host=value), self.assertRaises(ValueError):
                canonical_host(value)
        self.assertEqual(canonical_host("192.0.2.25"), "192.0.2.25")

    def test_invalid_nodes_rejected_before_request(self):
        with patch.dict(os.environ, {
            "KSSH_PROXMOX_TOKEN_ID": "monitor@pve!read",
            "KSSH_PROXMOX_TOKEN_SECRET": "fixture"
        }):
            client = self.client()
            with patch.object(client._opener, "open") as mocked:
                for name in ("/", "../pve", "pve?x", "pve%2fvm", "space node",
                             "pve/name", "", "pve#fragment"):
                    with self.subTest(name=name), self.assertRaises(ValueError):
                        client.qemu(name)
                mocked.assert_not_called()

    def test_credential_variables_only_and_missing_token_prevents_io(self):
        for env_ref in ("SECRET=abc", "abc", "BAD-NAME", "ROOT PASSWORD"):
            with self.subTest(env_ref=env_ref), self.assertRaises(ValueError):
                self.client(token_secret_env=env_ref)
        with patch.dict(os.environ, {
            "KSSH_PROXMOX_TOKEN_ID": "",
            "KSSH_PROXMOX_TOKEN_SECRET": "",
        }):
            client = self.client()
            with patch.object(client._opener, "open") as mocked:
                result = client.version()
            mocked.assert_not_called()
            self.assertEqual(result["error_code"], "UNAVAILABLE")

    def test_invalid_token_identifier_rejected(self):
        with patch.dict(os.environ, {
            "KSSH_PROXMOX_TOKEN_ID": "bad\nAuthorization: hacked",
            "KSSH_PROXMOX_TOKEN_SECRET": "fixture",
        }):
            client = self.client()
            with patch.object(client._opener, "open") as mocked:
                self.assertEqual(client.version()["error_code"], "UNAVAILABLE")
                mocked.assert_not_called()

    def test_ssl_verification_and_hostname_checks_stay_on(self):
        client = self.client()
        self.assertEqual(client.tls_context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(client.tls_context.check_hostname)

    def test_no_redirect_to_different_target_or_downgrade(self):
        handler = NoRedirect()
        for destination in (
            "http://evil.example/api",
            "https://evil.example:8006/api2/json/nodes",
            "https://proxmox.example:8006/other",
        ):
            self.assertIsNone(handler.redirect_request(
                None, None, 302, "redirect", {}, destination))
        client = self.client()
        self.assertTrue(any(isinstance(h, NoRedirect)
                            for h in client._opener.handlers))
        self.assertFalse(any(
            type(h).__name__ == "HTTPRedirectHandler"
            for h in client._opener.handlers))

    def test_proxy_environment_does_not_affect_opener(self):
        client = self.client()
        proxies = [h for h in client._opener.handlers
                   if type(h).__name__ == "ProxyHandler"]
        self.assertTrue(all(h.proxies == {} for h in proxies))

    def test_mutating_http_methods_have_no_api_surface(self):
        client = self.client()
        for name in ("post", "put", "patch", "delete", "request", "raw_get",
                     "start_vm", "stop_vm", "shutdown", "execute"):
            self.assertFalse(hasattr(client, name), name)
        # A positive call still uses GET, not POST.
        with patch.dict(os.environ, {
            "KSSH_PROXMOX_TOKEN_ID": "monitor@pve!read",
            "KSSH_PROXMOX_TOKEN_SECRET": "fixture",
        }):
            class Fake:
                status = 200
                def __enter__(self): return self
                def __exit__(self, *args): return False
                def read(self, limit): return b'{"data":{"version":"8.4"}}'
            with patch.object(client._opener, "open", return_value=Fake()) as mocked:
                self.assertTrue(client.version()["ok"])
            self.assertEqual(mocked.call_args.args[0].get_method(), "GET")

    def test_json_log_is_utc_and_does_not_expose_credentials(self):
        with patch.dict(os.environ, {
            "KSSH_PROXMOX_TOKEN_ID": "monitor@pve!read",
            "KSSH_PROXMOX_TOKEN_SECRET": "KEEP_ME_SECRET",
        }):
            logger = logging.getLogger("monitoring.proxmox_api")
            stream = io.StringIO()
            handler = logging.StreamHandler(stream)
            logger.addHandler(handler)
            old_level = logger.level
            logger.setLevel(logging.INFO)
            try:
                client = self.client()
                failure = urllib.error.HTTPError(
                    "https://proxmox.example:8006", 403, "KEEP_ME_SECRET", {}, None)
                with patch.object(client._opener, "open", side_effect=failure):
                    self.assertEqual(
                        client.version()["error_code"], "PERMISSION_DENIED")
            finally:
                logger.removeHandler(handler)
                logger.setLevel(old_level)
            output = stream.getvalue()
            self.assertNotIn("KEEP_ME_SECRET", output)
            self.assertNotIn("PVEAPIToken", output)
            self.assertNotIn("proxmox.example", output)
            record = json.loads(output.strip())
            self.assertEqual(record["error_code"], "PERMISSION_DENIED")
            self.assertTrue(record["timestamp_utc"].endswith("Z"))
            self.assertEqual(len(record["correlation_id"]), 32)

    def test_timeout_validation(self):
        for timeout in (0, -1, 61, float("nan"), True):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                self.client(timeout=timeout)


if __name__ == "__main__":
    unittest.main()
