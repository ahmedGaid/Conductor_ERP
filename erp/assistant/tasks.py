"""Celery tasks for the assistant module — the ambient morning digest + weekly ops report,
(T3.7) the rolling conversation-summary refresh fired post-response from the chat flow, and
(T5.9) the detached agent-turn worker that carries a chat/agent turn off the HTTP request.

The Celery beat schedule (see ``CELERY_BEAT_SCHEDULE`` in settings) fires ``send_ai_digests`` once a
day; the task itself decides which users are due today (daily vs. weekly preference), same shape as
``accounting.run_scheduled_reports``. ``send_ai_weekly_report`` fires once a week (T1.9) and always
runs — no due-ness check, since it is a standing ops artifact rather than a per-user preference.
"""
from __future__ import annotations

import logging
import time

from celery import shared_task

logger = logging.getLogger(__name__)


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


@shared_task(name="assistant.run_detached_stream", queue="ai_stream")
def run_detached_stream(*, stream_id: str, conversation_id: int, actor_id: int | None,
                        question: str, page: dict | None, regenerate: bool,
                        attachment_ids: list | None) -> None:
    """Runs one agent/chat turn off the HTTP request (ai-reliability T5.9, Twenty study
    2026-07-16): every event the loop yields publishes to the conversation's Redis channel instead
    of streaming straight into a response, so the turn survives the requesting browser tab
    closing, reloading, or losing its connection. A heartbeat proves the worker is alive; any read
    path finding a claim with an expired heartbeat (this process got killed) reaps it — see
    ``services.stream_relay.reap_if_dead``.

    Idempotency is scoped to what this task actually needs: on a Celery redelivery (``acks_late``)
    the SAME ``stream_id`` is passed again, so the checkpoint row upserts (``get_or_create`` in
    ``agent.run``) rather than duplicating. A stale/superseded claim (a reap or a newer send
    already moved the conversation on) makes this a no-op instead of a duplicate answer.
    """
    from django.contrib.auth import get_user_model

    from .errors import AssistantUnavailableError
    from .models import Conversation
    from .services import stream_relay
    from .services.agent import run as agent_run

    try:
        conversation = Conversation.objects.get(pk=conversation_id)
    except Conversation.DoesNotExist:
        return
    if str(conversation.active_stream_id) != str(stream_id):
        # Superseded: reaped for a dead heartbeat, or a newer claim already replaced this one.
        return

    actor = None
    if actor_id is not None:
        actor = get_user_model().objects.filter(pk=actor_id).first()

    stream_relay.touch_heartbeat(stream_id)
    gen = agent_run(actor=actor, conversation=conversation, question=question, page=page,
                    regenerate=regenerate, attachment_ids=attachment_ids, stream_id=stream_id)
    last_heartbeat = time.monotonic()
    last_checkpoint = last_heartbeat
    checkpoint_message_id: int | None = None
    token_buffer: list[str] = []
    try:
        for event in gen:
            stream_relay.publish(conversation_id, event)
            now = time.monotonic()
            if now - last_heartbeat >= stream_relay.HEARTBEAT_REFRESH_S:
                stream_relay.touch_heartbeat(stream_id)
                last_heartbeat = now
            if event.get("type") == "checkpoint":
                checkpoint_message_id = event.get("message_id")
            elif event.get("type") == "token":
                token_buffer.append(event.get("text") or "")
            # A courtesy write for reload-mid-answer: the row's authoritative final content comes
            # from ``agent.run``'s own persist on completion/cancel/error, which always runs last
            # and overwrites whatever this loop wrote — so a redelivered/duplicate partial here is
            # harmless, never a source of truth by itself.
            if (checkpoint_message_id is not None and token_buffer
                    and now - last_checkpoint >= 2.0):
                from .models import Message

                Message.objects.filter(pk=checkpoint_message_id).update(
                    content="".join(token_buffer))
                last_checkpoint = now
            if stream_relay.cancel_requested(stream_id):
                # Closes the generator at its current yield — ``agent.run`` catches the resulting
                # GeneratorExit exactly like an HTTP disconnect (stop="cancelled"), persisting the
                # partial via its own ``finally``. Same code path, same guarantee, new trigger.
                gen.close()
                break
    except Exception:
        logger.exception("assistant: detached stream task failed")
        stream_relay.publish(conversation_id, {
            "type": "error", "message": AssistantUnavailableError.message,
            "code": AssistantUnavailableError.code,
        })
        stream_relay.mark_stream_error(conversation_id, stream_id, reason="error")
        return
    finally:
        stream_relay.clear_heartbeat(stream_id)
        stream_relay.clear_cancel(stream_id)
    stream_relay.release_stream(conversation_id, stream_id)
