"""Individual subsystem health checks.

Each returns a (status, detail) tuple. Status is one of: healthy | warning | critical.
Checks never raise — a failing check degrades gracefully into a 'critical' status so the
monitoring endpoint itself stays up.
"""
from __future__ import annotations

from pathlib import Path

HEALTHY = "healthy"
WARNING = "warning"
CRITICAL = "critical"


def check_database() -> tuple[str, str]:
    try:
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return HEALTHY, "ok"
    except Exception as exc:  # noqa: BLE001
        return CRITICAL, f"{type(exc).__name__}: {exc}"


def check_redis() -> tuple[str, str]:
    try:
        import redis
        from django.conf import settings

        client = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        client.ping()
        return HEALTHY, "ok"
    except Exception as exc:  # noqa: BLE001
        return CRITICAL, f"{type(exc).__name__}: {exc}"


def check_storage() -> tuple[str, str]:
    try:
        from django.conf import settings

        root = Path(settings.STORAGE_ROOT)
        root.mkdir(parents=True, exist_ok=True)
        probe = root / ".healthcheck"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return HEALTHY, str(root)
    except Exception as exc:  # noqa: BLE001
        return WARNING, f"{type(exc).__name__}: {exc}"


def check_workers() -> tuple[str, str]:
    """Celery workers. No workers in dev/test is a WARNING, not CRITICAL (jobs queue until one starts)."""
    try:
        from config.celery import app

        replies = app.control.ping(timeout=1.0)
        if replies:
            return HEALTHY, f"{len(replies)} worker(s)"
        return WARNING, "no workers online"
    except Exception as exc:  # noqa: BLE001
        return WARNING, f"{type(exc).__name__}: {exc}"


def run_all() -> dict:
    """Aggregate all checks into a single status report."""
    results = {
        "database": check_database(),
        "redis": check_redis(),
        "storage": check_storage(),
        "workers": check_workers(),
    }
    components = {name: {"status": s, "detail": d} for name, (s, d) in results.items()}
    statuses = [s for s, _ in results.values()]
    overall = CRITICAL if CRITICAL in statuses else (WARNING if WARNING in statuses else HEALTHY)
    return {"status": overall, "components": components}
