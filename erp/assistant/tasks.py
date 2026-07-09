"""Celery tasks for the assistant module — the ambient morning digest + weekly ops report.

The Celery beat schedule (see ``CELERY_BEAT_SCHEDULE`` in settings) fires ``send_ai_digests`` once a
day; the task itself decides which users are due today (daily vs. weekly preference), same shape as
``accounting.run_scheduled_reports``. ``send_ai_weekly_report`` fires once a week (T1.9) and always
runs — no due-ness check, since it is a standing ops artifact rather than a per-user preference.
"""
from __future__ import annotations

from celery import shared_task


@shared_task(name="assistant.send_ai_digests")
def send_ai_digests() -> int:
    """Send the morning digest to every due, opted-in user; return the count sent."""
    from .services import send_digests

    return send_digests()


@shared_task(name="assistant.send_ai_weekly_report")
def send_ai_weekly_report() -> str:
    """Write + send the weekly AI ops report; return the written file path as a string."""
    from .services import send_weekly_report

    return str(send_weekly_report())
