"""SSRF protection utilities.

Validates outbound URLs before any HTTP call to a VCS platform.
Two layers of defence:
  1. Hostname allowlist — only recognised VCS API hosts are permitted.
  2. IP blocklist — private/loopback/link-local ranges always rejected even
     if the hostname resolves to them (counters DNS rebinding).

Configure allowed hosts via the comma-separated env var ALLOWED_DIFF_HOSTS.
Default allowlist covers the three supported VCS platforms.
"""

import ipaddress
import logging
import os
import socket
from urllib.parse import urlparse

logger = logging.getLogger("worker.security.ssrf")

_DEFAULT_ALLOWED_HOSTS = frozenset(
    {
        "api.github.com",
        "gitlab.com",
        "api.bitbucket.org",
    }
)

_BLOCKED_NETWORKS = [
    ipaddress.ip_network(cidr)
    for cidr in (
        "127.0.0.0/8",
        "::1/128",
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "169.254.0.0/16",
        "fe80::/10",
        "fc00::/7",
        "0.0.0.0/8",
        "100.64.0.0/10",
        "192.0.0.0/24",
        "198.18.0.0/15",
        "198.51.100.0/24",
        "203.0.113.0/24",
        "224.0.0.0/4",
        "240.0.0.0/4",
    )
]


def _get_allowed_hosts() -> frozenset:
    raw = os.getenv("ALLOWED_DIFF_HOSTS", "")
    if raw:
        extra = frozenset(h.strip().lower() for h in raw.split(",") if h.strip())
        return _DEFAULT_ALLOWED_HOSTS | extra
    return _DEFAULT_ALLOWED_HOSTS


def _is_private_ip(ip_str: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        return True
    return any(addr in net for net in _BLOCKED_NETWORKS)


def validate_outbound_url(url: str, context: str = "outbound") -> None:
    """Raise ValueError if *url* targets a private/reserved address or an
    un-allowlisted hostname.

    Call this before every outbound HTTP request to a URL derived from
    webhook payload data.
    """
    try:
        parsed = urlparse(url)
    except Exception as exc:
        raise ValueError(f"SSRF: unparseable URL {url!r}") from exc

    if parsed.scheme not in ("https", "http"):
        raise ValueError(f"SSRF: disallowed scheme {parsed.scheme!r} in {url!r}")

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise ValueError(f"SSRF: missing hostname in {url!r}")

    allowed = _get_allowed_hosts()
    if hostname not in allowed:
        raise ValueError(
            f"SSRF: host {hostname!r} not in allowlist for {context}. "
            f"Set ALLOWED_DIFF_HOSTS to extend it."
        )

    # Hosts explicitly added via ALLOWED_DIFF_HOSTS are operator-trusted
    # (e.g. self-hosted GitLab on a private IP). Skip IP check for those.
    raw_custom = os.getenv("ALLOWED_DIFF_HOSTS", "")
    custom_hosts = frozenset(h.strip().lower() for h in raw_custom.split(",") if h.strip())
    if hostname in custom_hosts:
        return

    # Pre-flight DNS resolution to block DNS rebinding at request time.
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise ValueError(f"SSRF: DNS resolution failed for {hostname!r}: {exc}") from exc

    for _family, _type, _proto, _canon, sockaddr in infos:
        ip = sockaddr[0]
        if _is_private_ip(ip):
            logger.warning(
                "SSRF block: %s resolved to private IP %s (context=%s)", hostname, ip, context
            )
            raise ValueError(
                f"SSRF: {hostname!r} resolved to private/reserved address {ip!r}"
            )
