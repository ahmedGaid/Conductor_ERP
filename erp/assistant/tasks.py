"""Celery tasks for the assistant module — the ambient morning digest + weekly ops report, and
(T3.7) the rolling conversation-summary refresh fired post-response from the chat flow.

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


@shared_task(name="assistant.refresh_thread_summary")
def refresh_thread_summary(conversation_id: int) -> bool:
    """Fold new older-than-tail turns into a conversation's rolling summary (T3.7). Fired
    fire-and-forget right after an assistant turn is persisted (``summarize.maybe_trigger``) —
    runs after the response, never blocking it. Returns ``False`` if the conversation is already
    gone (deleted mid-flight) instead of raising — nothing left to summarize."""
    from .models import Conversation
    from .services.summarize import refresh_summary

    try:
        conversation = Conversation.objects.get(id=conversation_id)
    except Conversation.DoesNotExist:
        return False
    refresh_summary(conversation)
    return True
