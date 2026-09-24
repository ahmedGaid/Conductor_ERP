"""Request middleware: correlation IDs, IP whitelisting, the CSP header, and license enforcement."""
from __future__ import annotations

import ipaddress
import logging
from collections.abc import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse

from .correlation import HEADER_NAME, get_correlation_id, new_correlation_id, set_correlation_id
from .errors import AppError, LicenseReadOnlyError, ModuleNotLicensedError


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


class ContentSecurityPolicyMiddleware:
    """Attach Content-Security-Policy from settings.CSP_POLICY (empty string disables).

    The policy is a plain header string so an installer can tune it per deployment via env;
    a response that already set its own CSP (e.g. a sandboxed download) is left alone.
    """

    HEADER = "Content-Security-Policy"

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response
        self._policy = (getattr(settings, "CSP_POLICY", "") or "").strip()

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        if self._policy and self.HEADER not in response:
            response[self.HEADER] = self._policy
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
    def _client_ip(request: HttpRequest) -> ipaddress._BaseAddress | None:
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        raw = xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR", "")
        try:
            return ipaddress.ip_address(raw)
        except ValueError:
            return None


# URL prefix -> the erp.identity.rbac module it gates. Only modules with a clean, single-purpose
# API prefix are listed — "administration" (identity/users/roles) is bundled into every edition by
# EDITIONS in erp.licensing.core, so gating it risks locking out the very login/user-management
# surface a customer would need to fix a licensing problem in the first place.
MODULE_URL_PREFIXES: dict[str, str] = {
    "/api/accounting/": "accounting",
    "/api/inventory/": "inventory",
    "/api/sales/": "sales",
    "/api/purchasing/": "purchasing",
    "/api/crm/": "crm",
    "/api/einvoice/": "einvoice",
    "/api/workflow/": "workflow",
    "/api/notifications/": "notifications",
}


def _path_matches(path: str, prefix: str) -> bool:
    """``prefix`` gates ``path`` if it IS the prefix or a sub-path of it — a bare string
    ``startswith`` would also match an unrelated route that merely shares the same leading
    characters (e.g. a hypothetical ``/api/notifications-x``)."""
    stripped = prefix.rstrip("/")
    return path == stripped or path.startswith(stripped + "/")

WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

# Always reachable even in a read-only license state: the license endpoint itself (so a key can be
# installed to escape read-only), and sign-in/out (a locked-out install must still let its admin in).
READ_ONLY_ALLOWLIST_PREFIXES = ("/api/license/", "/api/identity/login", "/api/identity/logout",
                                "/api/identity/token/refresh")


def _error_response(exc: AppError) -> JsonResponse:
    return JsonResponse(
        {"error": {**exc.to_dict(), "correlation_id": get_correlation_id()}},
        status=exc.status_code,
    )


class LicenseEnforcementMiddleware:
    """``LICENSE_MODE=enforce`` only (off is a no-op, checked once up front): hides an unlicensed
    module's API behind a typed 403, and blocks writes everywhere once the install has gone
    read-only (trial ended / invalid key / company mismatch) — reads, exports, and the license/
    sign-in endpoints above always keep working. See license-key FILE_03.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if settings.LICENSE_MODE == "off" or not request.path.startswith("/api/"):
            return self.get_response(request)

        from erp.licensing.state import current_state

        try:
            state = current_state()
        except Exception:
            # A customer's own data must never become unreadable because THIS gate broke — an
            # unexpected failure here (DB hiccup, a malformed keys.py) fails OPEN, exactly as if
            # the request had arrived before this middleware existed. Opus review (FILE_03).
            logging.getLogger("erp.core").exception(
                "license enforcement: current_state() failed — request allowed through unchecked"
            )
            return self.get_response(request)

        if state.status == "active":
            for prefix, module in MODULE_URL_PREFIXES.items():
                if _path_matches(request.path, prefix) and module not in state.modules:
                    return _error_response(ModuleNotLicensedError(
                        f"The {module} module is not in your license package.",
                        data={"module": module},
                    ))

        if (
            request.method in WRITE_METHODS
            and state.status in ("trial_ended", "invalid", "company_mismatch")
            and not any(_path_matches(request.path, p) for p in READ_ONLY_ALLOWLIST_PREFIXES)
        ):
            return _error_response(LicenseReadOnlyError(data={"status": state.status}))

        return self.get_response(request)
