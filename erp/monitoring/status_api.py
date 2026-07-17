"""System status panel API (twenty-harvest FILE_19, Task A) — admin-only, read-only.

Unlike ``health``/``system-check`` (unauthenticated liveness/readiness probes in ``views.py``),
this is the operator-facing surface: version, subsystem latency, worker/queue depth, storage
headroom, backup freshness, and which env vars are configured — NAMES only, never values, so the
panel can never leak a secret. No config-mutation path here by design (see the plan file):
changing config stays in ``.env`` + restart.
"""
from __future__ import annotations

import os
import shutil
import time
from pathlib import Path

from django.conf import settings
from django.urls import path
from django.utils import timezone
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from erp.identity.permissions import HasAnyRole
from erp.identity.roles import SYSTEM_ADMIN

from . import checks

_IsAdmin = HasAnyRole.require(SYSTEM_ADMIN)

# Process start — an honest per-process uptime (this worker), not "since last deploy".
_STARTED_AT = timezone.now()

# The env var NAMES catalog (mirrors .env.example). Values never leave the server: each is
# reported as "set" | "unset" only. Keep this list in sync when .env.example gains a key.
ENV_VAR_NAMES = (
    "DJANGO_SETTINGS_MODULE", "DJANGO_SECRET_KEY", "DJANGO_DEBUG", "DJANGO_ALLOWED_HOSTS",
    "DJANGO_IP_WHITELIST", "APP_VERSION", "DATABASE_URL", "REDIS_URL",
    "CELERY_TASK_ALWAYS_EAGER", "STORAGE_ROOT", "BACKUP_DIR", "API_PORT", "WEB_PORT",
    "DJANGO_COOKIE_SECURE", "DJANGO_SSL_REDIRECT", "DJANGO_HSTS_SECONDS", "DJANGO_CSP_POLICY",
    "DJANGO_CSRF_TRUSTED_ORIGINS", "DJANGO_CORS_ALLOWED_ORIGINS", "DRF_THROTTLE_ANON",
    "DRF_THROTTLE_USER", "DRF_THROTTLE_LOGIN", "WORKFLOW_EGRESS_ALLOWLIST", "EMAIL_BACKEND",
    "DEFAULT_FROM_EMAIL", "EMAIL_HOST", "EMAIL_PORT", "EMAIL_HOST_USER", "EMAIL_HOST_PASSWORD",
    "EMAIL_USE_TLS", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GROQ_API_KEY", "MISTRAL_API_KEY",
    "ASSISTANT_PROVIDER",
)

_DEFAULT_QUEUE = "celery"


def _envelope(data) -> Response:
    return Response({"data": data})


def _timed(check_fn) -> dict:
    t0 = time.perf_counter()
    status, detail = check_fn()
    return {"status": status, "detail": detail, "latency_ms": round((time.perf_counter() - t0) * 1000, 1)}


def _storage_report() -> dict:
    report = _timed(checks.check_storage)
    try:
        usage = shutil.disk_usage(settings.STORAGE_ROOT)
        report["free_bytes"] = usage.free
        report["total_bytes"] = usage.total
    except OSError:
        report["free_bytes"] = None
        report["total_bytes"] = None
    return report


def _worker_report() -> dict:
    try:
        from config.celery import app

        replies = app.control.ping(timeout=1.0)
        count = len(replies) if replies else 0
        status = checks.HEALTHY if count else checks.WARNING
        detail = f"{count} worker(s)" if count else "no workers online"
    except Exception as exc:  # noqa: BLE001 — mirrors checks.py: never raise out of a status probe
        count, status, detail = 0, checks.WARNING, f"{type(exc).__name__}: {exc}"

    queue_depth = None
    try:
        import redis

        client = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        queue_depth = client.llen(_DEFAULT_QUEUE)
    except Exception:  # noqa: BLE001 — depth is a bonus field, absence shouldn't fail the panel
        queue_depth = None

    return {"status": status, "count": count, "queue_depth": queue_depth, "detail": detail}


def _backup_report() -> dict:
    backup_dir = getattr(settings, "BACKUP_DIR", "") or ""
    if not backup_dir:
        return {"configured": False, "last_backup_at": None, "detail": "BACKUP_DIR not set"}
    root = Path(backup_dir)
    if not root.is_dir():
        return {"configured": True, "last_backup_at": None, "detail": f"{root} does not exist"}
    snapshots = [p for p in root.iterdir() if p.is_dir()]
    if not snapshots:
        return {"configured": True, "last_backup_at": None, "detail": "no backups found yet"}
    latest = max(snapshots, key=lambda p: p.stat().st_mtime)
    last_backup_at = timezone.datetime.fromtimestamp(latest.stat().st_mtime, tz=timezone.get_current_timezone())
    return {"configured": True, "last_backup_at": last_backup_at.isoformat(), "detail": latest.name}


def _env_report() -> dict:
    return {name: ("set" if os.environ.get(name) else "unset") for name in ENV_VAR_NAMES}


def _overall(*component_statuses: str) -> str:
    if checks.CRITICAL in component_statuses:
        return checks.CRITICAL
    if checks.WARNING in component_statuses:
        return checks.WARNING
    return checks.HEALTHY


class SystemStatusView(APIView):
    """``GET /api/system/status/`` — admin-only operator panel (twenty-harvest FILE_19)."""

    permission_classes = [_IsAdmin]

    def get(self, request: Request) -> Response:
        database = _timed(checks.check_database)
        redis_report = _timed(checks.check_redis)
        storage = _storage_report()
        workers = _worker_report()

        return _envelope({
            "version": settings.APP_VERSION,
            "uptime_seconds": int((timezone.now() - _STARTED_AT).total_seconds()),
            "status": _overall(database["status"], redis_report["status"], storage["status"], workers["status"]),
            "database": database,
            "redis": redis_report,
            "storage": storage,
            "workers": workers,
            "backup": _backup_report(),
            "env": _env_report(),
        })


urlpatterns = [
    path("status/", SystemStatusView.as_view(), name="system-status"),
]
