# BGSSH: ClouDNS DDNS boot hook (bgssh.abrdns.com)

## Certificate
ClouDNS has already issued a Let's Encrypt certificate for `bgssh.abrdns.com`
and `*.bgssh.abrdns.com` (2026-10-28 to 2027-01-25).
The certificate/private key are NOT in this public repository. ClouDNS free SSL
on DNS redirect/parking pages does **not** automatically make BGSSH publicly
reachable or install the certificate on our reverse proxy.

## Why the GitHub Actions runner must not update the A record
The ClouDNS DynamicURL for an A record sets the IP to the public IPv4 of the
machine making the request. The current GitHub Actions runner is temporary
and does not expose a stable inbound HTTPS listener; its IP must NOT be
published as `bgssh.abrdns.com`. `scripts/cloudns-ddns.sh` always skips
on GitHub Actions even if enabled. The running CI session and tunnel do not
change. No Tailscale 100.x address or trycloudflare IP should go into the A record.

## Prerequisites on the actual always-on HTTPS ingress server
1. Deploy an always-on Debian HTTPS ingress/reverse proxy with reachable public
   TCP 443, and install the valid certificate and private key securely there.
   Confirm inbound routing, NAT/CGNAT considerations, and firewall policy.
2. In the ClouDNS zone `bgssh.abrdns.com`, create an IPv4 A record for the
   apex host (blank/`@` in the UI) pointing to that ingress's **public IPv4**.
   Enable the A record's **Dynamic URL** in ClouDNS.
3. Place the resulting URL ONLY in a protected server-side environment variable
   `CLOUDNS_DDNS_URL`; do not commit it or paste into an issue or logs.
   Example URL shape (not a real credential):
   `https://ipv4.cloudns.net/api/dynamicURL/?q=REDACTED`
4. Confirm that the calling host's observed outbound public IPv4 is the same
   public address that can reach the ingress through port 443. Verify from an
   external network before marking the ingress ready.
5. Set `BGSSH_DDNS_ENABLED=1` and `BGSSH_DDNS_PUBLIC_HTTPS_READY=1` on
   that persistent machine only. Use `scripts/cloudns-ddns.sh` during its
   network-online startup, and optionally every 5 minutes via systemd timer.

## Run on the persistent ingress
Run using an environment file owned by root (mode 0600) or another secure
secret store, never GitHub Actions or the public Git repository:

```bash
# /etc/bgssh/cloudns.env (root:root, 0600), with the *real* secret URL:
# CLOUDNS_DDNS_URL='https://ipv4.cloudns.net/api/dynamicURL/?q=...'
# BGSSH_DDNS_ENABLED=1
# BGSSH_DDNS_PUBLIC_HTTPS_READY=1
# EnvironmentFile=/etc/bgssh/cloudns.env in the persistent server's systemd unit
bash /opt/ssh-connector/scripts/cloudns-ddns.sh
```

The existing `scripts/gh-session.sh` invokes the same updater during its
startup; on GitHub Actions, it intentionally SKIPS without a network request.

## Tests
```bash
bash -n scripts/cloudns-ddns.sh
bash -n scripts/gh-session.sh
python3 tests/test_cloudns_ddns.py
```

## Important
- Neither an RSA 2048 or an RSA 4096 certificate requires a PTR record.
- The cert is bound to the DNS hostname; changing the A-record IP does not
  invalidate the certificate.
- Do not upload the Let's Encrypt private key to this public repository.
- A successful A update is NOT proof that the ingress port 443 is accessible.
- Certificate renewal/download/deploy is separate from DDNS and needs automation.
- For a temporary Quick Tunnel, keep using its own `trycloudflare.com` URL;
  a ClouDNS A record cannot convert it to a custom HTTPS hostname.
