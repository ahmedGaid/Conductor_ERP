"""Redis pub/sub relay for detached durable streaming (ai-reliability T5.9, Twenty study
2026-07-16).

The agent loop used to yield SSE events straight into the HTTP response; now (when
``settings.ASSISTANT_DETACHED_STREAMING`` is on) it runs inside a Celery worker instead, and this
module is the thin, stateless channel between the two: every event the worker produces publishes
here, and the HTTP view subscribes and relays it byte-for-byte, so the wire protocol the frontend
already speaks never changes. Also carries the worker's liveness heartbeat and the cancel signal.

Same direct-``redis`` pattern as ``erp.monitoring.checks``/``scripts.gates.gate00`` — Django's
default cache backend (``LocMemCache``, per-process) can't carry state between the HTTP view
process and a separate Celery worker process, so this talks to Redis directly rather than through
``django.core.cache``.
"""
from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Iterator

import redis
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# Worker heartbeat: refreshed this often, expires after this long with no refresh. A read path
# that finds a claim whose heartbeat key is gone treats the worker as dead, not busy.
HEARTBEAT_TTL_S = 30
HEARTBEAT_REFRESH_S = 5

_client: redis.Redis | None = None


def _redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis.from_url(settings.REDIS_URL)
    return _client


def stream_channel(conversation_id: int) -> str:
    return f"assistant:conv:{conversation_id}"


def _cancel_key(stream_id) -> str:
    return f"assistant:cancel:{stream_id}"


def _heartbeat_key(stream_id) -> str:
    return f"assistant-stream-alive:{stream_id}"


# --- claim ----------------------------------------------------------------------------------

def claim_stream(conversation) -> uuid.UUID | None:
    """Optimistic UPDATE: ``active_stream_id IS NULL`` -> a new id. Returns the new id, or
    ``None`` if another turn already holds the claim (busy). Also clears any stale
    ``last_stream_error`` — a fresh attempt supersedes the last failure it's about to retry."""
    from ..models import Conversation

    new_id = uuid.uuid4()
    updated = Conversation.objects.filter(
        pk=conversation.pk, active_stream_id__isnull=True,
    ).update(active_stream_id=new_id, last_stream_error=None)
    if not updated:
        return None
    conversation.active_stream_id = new_id
    conversation.last_stream_error = None
    return new_id


def release_stream(conversation_id: int, stream_id) -> None:
    """Clear the claim — only if it still belongs to ``stream_id`` (a reap or a newer claim may
    already have moved past it, and must not be clobbered)."""
    from ..models import Conversation

    Conversation.objects.filter(pk=conversation_id, active_stream_id=stream_id).update(
        active_stream_id=None,
    )


def mark_stream_error(conversation_id: int, stream_id, *, reason: str) -> dict:
    from ..models import Conversation

    error = {"reason": reason, "at": timezone.now().isoformat()}
    Conversation.objects.filter(pk=conversation_id, active_stream_id=stream_id).update(
        active_stream_id=None, last_stream_error=error,
    )
    return error


def reap_if_dead(conversation) -> bool:
    """A claim with no heartbeat is a dead worker, not a busy one — clear it (and publish a
    ``stream-error`` so any live relay stops waiting) rather than leaving the conversation stuck
    forever. Call before trusting ``conversation.active_stream_id`` on any read path (a new claim
    attempt, the reconnect endpoint, the retry endpoint). Returns True if a reap happened."""
    stream_id = conversation.active_stream_id
    if stream_id is None:
        return False
    if is_alive(stream_id):
        return False
    error = mark_stream_error(conversation.pk, stream_id, reason="interrupted")
    conversation.active_stream_id = None
    conversation.last_stream_error = error
    publish(conversation.pk, {"type": "stream-error", "reason": "interrupted"})
    clear_heartbeat(stream_id)
    clear_cancel(stream_id)
    return True


# --- pub/sub ----------------------------------------------------------------------------------

def publish(conversation_id: int, event: dict) -> None:
    """Best-effort — a dropped publish must never crash the worker task; the DB checkpoint row and
    the reap path are the durability backstops, not this channel."""
    try:
        _redis().publish(stream_channel(conversation_id), json.dumps(event, ensure_ascii=False))
    except Exception:
        logger.exception("stream_relay: publish failed")


def open_subscription(conversation_id: int):
    """Subscribe NOW (eager, synchronous) — call this BEFORE enqueuing the worker task, so no
    early-published event is lost. Redis buffers everything published to a channel once a
    subscriber is registered, even before that subscriber calls ``listen``/``get_message``.
    Returns the raw pubsub object; iterate it with :func:`iter_events`."""
    pubsub = _redis().pubsub()
    pubsub.subscribe(stream_channel(conversation_id))
    return pubsub


def iter_events(pubsub, *, idle_timeout_s: float = HEARTBEAT_TTL_S) -> Iterator[dict]:
    """Poll for published events with a bounded per-read timeout, so a channel that will never
    receive anything else (e.g. reconnecting after the turn already finished) doesn't hang the
    HTTP connection forever — gives up after ``idle_timeout_s`` with no message at all. Closes the
    pubsub on exit either way (normal completion, caller break, or client disconnect)."""
    try:
        idle = 0.0
        poll = 1.0
        while idle < idle_timeout_s:
            message = pubsub.get_message(timeout=poll, ignore_subscribe_messages=True)
            if message is None:
                idle += poll
                continue
            idle = 0.0
            try:
                yield json.loads(message["data"])
            except ValueError:
                continue
    finally:
        pubsub.close()


# --- heartbeat + cancel -------------------------------------------------------------------------

def touch_heartbeat(stream_id) -> None:
    try:
        _redis().set(_heartbeat_key(stream_id), "1", ex=HEARTBEAT_TTL_S)
    except Exception:
        logger.exception("stream_relay: heartbeat touch failed")


def clear_heartbeat(stream_id) -> None:
    try:
        _redis().delete(_heartbeat_key(stream_id))
    except Exception:
        logger.exception("stream_relay: heartbeat clear failed")


def is_alive(stream_id) -> bool:
    try:
        return bool(_redis().exists(_heartbeat_key(stream_id)))
    except Exception:
        logger.exception("stream_relay: liveness check failed")
        return True  # fail open — never reap a live claim just because Redis hiccuped


def request_cancel(stream_id) -> None:
    try:
        _redis().set(_cancel_key(stream_id), "1", ex=HEARTBEAT_TTL_S)
    except Exception:
        logger.exception("stream_relay: cancel request failed")


def cancel_requested(stream_id) -> bool:
    """Polled by the worker between rounds/chunks — a cheap key check, not a subscription (the
    worker is busy producing, not listening)."""
    try:
        return bool(_redis().exists(_cancel_key(stream_id)))
    except Exception:
        logger.exception("stream_relay: cancel check failed")
        return False


def clear_cancel(stream_id) -> None:
    try:
        _redis().delete(_cancel_key(stream_id))
    except Exception:
        logger.exception("stream_relay: cancel clear failed")
