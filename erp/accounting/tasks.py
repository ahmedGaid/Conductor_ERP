"""Celery tasks for the accounting module — scheduled report exports.

The Celery beat schedule (see ``CELERY_BEAT_SCHEDULE`` in settings) fires ``run_scheduled_reports``
periodically; the task itself decides which saved definitions are *due* and writes their CSV exports
to the reports directory. Retryable + idempotent (a definition only re-runs once its interval elapses).
"""
from __future__ import annotations

from celery import shared_task


@shared_task(name="accounting.run_scheduled_reports")
def run_scheduled_reports() -> list[str]:
    """Run every due scheduled report definition; return the names that were written."""
    from .services import run_scheduled

    written = run_scheduled()
    return [name for name, _path in written]
