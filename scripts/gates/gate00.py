"""Gate 00 — scaffold, DB/Redis reachability, and /health.

Asserts:
- key scaffold files exist and Django settings import cleanly;
- a raw DB query (SELECT 1) succeeds;
- Redis/Memurai responds to PING;
- GET /health returns {"ok": true};
- GET /system-check reports a non-critical overall status.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def check() -> None:
    # 1. Scaffold files present.
    for rel in [
        "manage.py",
        "config/settings/base.py",
        "config/celery.py",
        "erp/core/middleware.py",
        "erp/monitoring/views.py",
    ]:
        _assert((REPO_ROOT / rel).exists(), f"missing scaffold file: {rel}")

    # 2. Settings import cleanly.
    from django.conf import settings

    _assert("erp.core" in settings.INSTALLED_APPS, "core app not installed")

    # 3. Database reachable.
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        _assert(cursor.fetchone() == (1,), "SELECT 1 did not return 1")

    # 4. Redis reachable.
    import redis

    client = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=3)
    _assert(client.ping() is True, "Redis PING failed")

    # 5. /health endpoint.
    from django.test import Client

    c = Client()
    resp = c.get("/health")
    _assert(resp.status_code == 200, f"/health status {resp.status_code}")
    _assert(resp.json().get("ok") is True, "/health did not return ok:true")

    # 6. /system-check not critical.
    resp = c.get("/system-check")
    body = resp.json()
    _assert(body.get("status") != "critical", f"system-check critical: {body}")
