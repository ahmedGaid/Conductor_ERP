"""Request middleware: correlation IDs and IP whitelisting."""
from __future__ import annotations

import ipaddress
from typing import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse

from .correlation import HEADER_NAME, new_correlation_id, set_correlation_id


class CorrelationIdMiddleware:
    """Bind a correlation ID to every request and echo it back on the response."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        incoming = request.headers.get(HEADER_NAME)
        cid = incoming or new_correlation_id()
        set_correlation_id(cid)
        request.correlation_id = cid  # type: ignore[attr-defined]
        response = self.get_response(request)
        response[HEADER_NAME] = cid
        return response


class IpWhitelistMiddleware:
    """Block requests from IPs outside DJANGO_IP_WHITELIST (empty list => allow all)."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response
        self._networks = []
        for entry in getattr(settings, "IP_WHITELIST", []) or []:
            entry = entry.strip()
            if not entry:
                continue
            try:
                self._networks.append(ipaddress.ip_network(entry, strict=False))
            except ValueError:
                # Single address without prefix.
                self._networks.append(ipaddress.ip_network(f"{entry}/32", strict=False))

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if self._networks:
            client = self._client_ip(request)
            if client is not None and not any(client in net for net in self._networks):
                return JsonResponse(
                    {"error": {"code": "GEN-004", "message": "IP not allowed"}}, status=403
                )
        return self.get_response(request)

    @staticmethod
    def _client_ip(request: HttpRequest) -> "ipaddress._BaseAddress | None":
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        raw = xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR", "")
        try:
            return ipaddress.ip_address(raw)
        except ValueError:
            return None
