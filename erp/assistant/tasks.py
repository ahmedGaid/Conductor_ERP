"""Celery tasks for the assistant module — the ambient morning digest.

The Celery beat schedule (see ``CELERY_BEAT_SCHEDULE`` in settings) fires ``send_ai_digests`` once a
day; the task itself decides which users are due today (daily vs. weekly preference), same shape as
``accounting.run_scheduled_reports``.
"""
from __future__ import annotations

from celery import shared_task


@shared_task(name="assistant.send_ai_digests")
def send_ai_digests() -> int:
    """Send the morning digest to every due, opted-in user; return the count sent."""
    from .services import send_digests

    return send_digests()
