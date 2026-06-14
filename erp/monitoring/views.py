"""Health and system-check endpoints (no authentication required)."""
from __future__ import annotations

from django.conf import settings
from django.http import JsonResponse

from . import checks


def health(_request) -> JsonResponse:
    """Liveness probe — cheap, no dependencies."""
    return JsonResponse({"ok": True, "version": settings.APP_VERSION})


def system_check(_request) -> JsonResponse:
    """Readiness/diagnostics — DB, Redis, storage (and more as subsystems come online)."""
    report = checks.run_all()
    report["version"] = settings.APP_VERSION
    http_status = 200 if report["status"] != checks.CRITICAL else 503
    return JsonResponse(report, status=http_status)
