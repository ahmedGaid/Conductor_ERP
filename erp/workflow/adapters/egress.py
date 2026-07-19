"""Outbound-URL guard for workflow adapters (SSRF protection).

Workflow REST/webhook nodes call user-configured URLs from inside the customer's network, so an
unchecked URL could reach loopback services, the cloud metadata endpoint (169.254.169.254), or
RFC-1918 hosts. ``assert_public_url`` is default-deny: only http(s) to a host whose *every* resolved
address is public passes. An optional allowlist (``WORKFLOW_EGRESS_ALLOWLIST`` — host suffixes)
narrows egress further: when set, the host must also match one of the suffixes.
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from django.conf import settings


class EgressBlockedError(Exception):
    """Raised when a workflow adapter URL fails the egress policy. Message is operator-facing."""


def _blocked(reason: str) -> EgressBlockedError:
    return EgressBlockedError(f"egress blocked: {reason}")


def assert_public_url(url: str) -> None:
    """Validate an adapter's outbound URL. Raises EgressBlockedError; returns None when allowed."""
    try:
        parsed = urlparse(url)
    except ValueError:
        raise _blocked("unparseable URL") from None
    if parsed.scheme not in ("http", "https"):
        raise _blocked(f"scheme '{parsed.scheme}' not allowed (http/https only)")
    host = parsed.hostname
    if not host:
        raise _blocked("no host")

    allowlist = [s.lower().lstrip(".") for s in getattr(settings, "WORKFLOW_EGRESS_ALLOWLIST", [])]
    if allowlist:
        h = host.lower()
        if not any(h == suffix or h.endswith("." + suffix) for suffix in allowlist):
            raise _blocked(f"host '{host}' not in the egress allowlist")

    try:
        infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    except OSError:
        raise _blocked(f"host '{host}' does not resolve") from None
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
                or ip.is_multicast or ip.is_unspecified):
            raise _blocked(f"host '{host}' resolves to a non-public address ({ip})")
