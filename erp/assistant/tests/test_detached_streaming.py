"""Detached durable streaming (ai-reliability T5.9, Twenty study 2026-07-16).

Exercises the real Redis instance (no fake) the same way ``scripts/gates/gate00.py`` proves Redis
is reachable — this module's whole point is the claim/heartbeat/relay machinery living OUTSIDE the
Django ORM, so a fake would prove nothing. ``CELERY_TASK_ALWAYS_EAGER=True`` (matches CI's own
setting) makes ``.delay()`` run the worker task synchronously in-process, so the full view -> task
-> Redis relay round trip is deterministic without a separately running worker.

Two tests are the phase's accept-criteria drills, named for what they prove:
- ``test_drill_a_...`` — refresh mid-answer: the partial is visible via a normal fetch, and the
  turn still completes.
- ``test_drill_b_...`` — kill -9 the worker: a dead heartbeat is reaped (not mistaken for "busy"),
  and retry recovers the conversation.
"""
from __future__ import annotations

import time
import uuid

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from erp.assistant.models import Conversation, Message
from erp.assistant.services import agent, stream_relay
from erp.assistant.tasks import run_detached_stream
from erp.identity.models import User

pytestmark = pytest.mark.django_db

CHAT_URL = "/api/assistant/chat"


def _user(username: str) -> User:
    user = User.objects.create_user(
        username=username, password="Dev12345!", email=f"{username}@example.test",
    )
    user.is_superuser = True
    user.save(update_fields=["is_superuser"])
    return user


def _client(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _script(monkeypatch, decisions: list[dict]):
    it = iter(decisions)
    monkeypatch.setattr(agent, "complete_json", lambda system, user, schema, **_: next(it))


def _answer_now(monkeypatch):
    _script(monkeypatch, [{"action": "answer"}])


def _stream(monkeypatch, *chunks: str):
    monkeypatch.setattr(agent, "complete_stream", lambda messages, **_: iter(chunks))


# --- claim / reap (pure stream_relay + model state, no Redis pub/sub needed) ---------------------

def test_claim_stream_race_two_claimants_one_wins():
    conv = Conversation.objects.create(user=_user("claim_race"))

    first = stream_relay.claim_stream(conv)
    second = stream_relay.claim_stream(Conversation.objects.get(pk=conv.pk))  # a second request's view

    assert first is not None
    assert second is None  # busy — the second send must not also start a turn
    assert Conversation.objects.get(pk=conv.pk).active_stream_id == first

    stream_relay.release_stream(conv.pk, first)
    third = stream_relay.claim_stream(Conversation.objects.get(pk=conv.pk))
    assert third is not None  # released — a fresh send may claim it again


def test_reap_if_dead_clears_a_claim_with_no_heartbeat():
    conv = Conversation.objects.create(user=_user("reap_dead"))
    stream_id = stream_relay.claim_stream(conv)
    assert not stream_relay.is_alive(stream_id)  # never touched — simulates a worker that never started

    reaped = stream_relay.reap_if_dead(conv)

    assert reaped is True
    conv.refresh_from_db()
    assert conv.active_stream_id is None
    assert conv.last_stream_error["reason"] == "interrupted"


def test_reap_if_dead_leaves_a_live_claim_alone():
    conv = Conversation.objects.create(user=_user("reap_alive"))
    stream_id = stream_relay.claim_stream(conv)
    stream_relay.touch_heartbeat(stream_id)

    reaped = stream_relay.reap_if_dead(conv)

    assert reaped is False
    conv.refresh_from_db()
    assert conv.active_stream_id == stream_id
    stream_relay.clear_heartbeat(stream_id)  # tidy up — this key has a 30s TTL either way


# --- idempotent checkpoint (agent.py, real DB) ----------------------------------------------------

@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_checkpoint_row_upserts_instead_of_duplicating_on_redelivery(monkeypatch):
    """Mirrors a Celery redelivery (``acks_late``): the SAME stream_id passed to ``agent.run``
    twice must write into ONE Message row, never create a second — the idempotency this task
    actually needs (not exactly-once for the whole turn, see ``tasks.run_detached_stream``)."""
    user = _user("checkpoint_upsert")
    conv = Conversation.objects.create(user=user)
    stream_id = uuid.uuid4()  # a claim id in shape only — this test is about the Message row's key

    _answer_now(monkeypatch)
    _stream(monkeypatch, "first ", "answer")
    list(agent.run(actor=user, conversation=conv, question="q1", stream_id=stream_id))

    _answer_now(monkeypatch)
    _stream(monkeypatch, "second ", "answer")
    list(agent.run(actor=user, conversation=conv, question="q1", regenerate=True, stream_id=stream_id))

    rows = Message.objects.filter(conversation=conv, stream_id=stream_id)
    assert rows.count() == 1
    assert rows.get().content == "second answer"


# --- the full detached round trip: view -> task -> real Redis relay ------------------------------

def _events(resp) -> list[dict]:
    import json

    body = b"".join(resp.streaming_content).decode()
    out = []
    for frame in body.split("\n\n"):
        frame = frame.strip()
        if frame.startswith("data:"):
            out.append(json.loads(frame[len("data:"):].strip()))
    return out


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic",
                   ASSISTANT_DETACHED_STREAMING=True, CELERY_TASK_ALWAYS_EAGER=True)
def test_detached_chat_round_trip_relays_events_and_releases_the_claim(monkeypatch):
    user = _user("detached_roundtrip")
    client = _client(user)
    conv = Conversation.objects.create(user=user)
    _answer_now(monkeypatch)
    _stream(monkeypatch, "Hel", "lo")

    resp = client.post(CHAT_URL, {"conversation_id": conv.id, "message": "hi"}, format="json")

    assert resp.status_code == 200
    events = _events(resp)
    assert [e["type"] for e in events][:1] == ["checkpoint"]
    assert "".join(e["text"] for e in events if e["type"] == "token") == "Hello"
    assert events[-1]["type"] == "done"

    conv.refresh_from_db()
    assert conv.active_stream_id is None  # released once the task's own finally ran
    msg = Message.objects.get(conversation=conv, role="assistant")
    assert msg.content == "Hello"
    assert msg.meta.get("streaming") is None  # final persist replaced meta wholesale


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_DETACHED_STREAMING=True)
def test_second_send_while_busy_gets_a_calm_409(monkeypatch):
    user = _user("detached_busy")
    client = _client(user)
    conv = Conversation.objects.create(user=user)
    stream_id = stream_relay.claim_stream(conv)  # a turn "already running" (no task actually enqueued)
    stream_relay.touch_heartbeat(stream_id)

    resp = client.post(CHAT_URL, {"conversation_id": conv.id, "message": "again"}, format="json")

    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "AI-009"
    stream_relay.clear_heartbeat(stream_id)


# --- drill (a): refresh mid-answer -----------------------------------------------------------------

@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic",
                   ASSISTANT_DETACHED_STREAMING=True)
def test_drill_a_refresh_mid_answer_shows_partial_and_the_turn_completes(monkeypatch):
    """Drill (a): reload mid-answer -> partial visible via a normal fetch, turn still finishes.

    Runs the worker task directly (not through Celery) so the test can inspect the checkpoint row
    from INSIDE the token stream, at the exact point a page reload would have raced it — the
    periodic checkpoint write (every ~2s of wall clock; faked here via monkeypatched
    ``time.monotonic`` so the test doesn't sleep) is what a reload's ``getConversation`` reads.
    """
    user = _user("drill_a")
    conv = Conversation.objects.create(user=user)
    stream_id = stream_relay.claim_stream(conv)

    _answer_now(monkeypatch)
    seen_mid_stream: dict = {}
    fake_clock = {"t": 0.0}
    monkeypatch.setattr(time, "monotonic", lambda: fake_clock["t"])

    def chunks():
        yield "The "
        fake_clock["t"] += 5.0  # past the 2s checkpoint threshold
        yield "answer "
        # A "reload" right now: the exact read path a page refresh takes.
        seen_mid_stream["content"] = Message.objects.get(
            conversation=conv, stream_id=stream_id).content
        seen_mid_stream["active_stream_id"] = Conversation.objects.get(pk=conv.pk).active_stream_id
        fake_clock["t"] += 5.0
        yield "is here."

    monkeypatch.setattr(agent, "complete_stream", lambda messages, **_: chunks())

    run_detached_stream(
        stream_id=str(stream_id), conversation_id=conv.id, actor_id=user.id,
        question="q", page=None, regenerate=False, attachment_ids=None,
    )

    # What the reload would have seen: the partial written so far, and the turn still marked live.
    assert seen_mid_stream["content"] == "The answer "
    assert seen_mid_stream["active_stream_id"] == stream_id

    # And the turn itself still ran to completion despite the "reload" in the middle.
    conv.refresh_from_db()
    assert conv.active_stream_id is None
    msg = Message.objects.get(conversation=conv, stream_id=stream_id)
    assert msg.content == "The answer is here."


# --- drill (b): kill -9 the worker ------------------------------------------------------------------

@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_DETACHED_STREAMING=True)
def test_drill_b_worker_kill_reaps_and_retry_recovers(monkeypatch):
    """Drill (b): kill -9 the worker mid-turn -> a read path reaps the dead claim (error card +
    retry), and retry completes. The "kill" is simulated the same way an actual SIGKILL would leave
    things: the claim exists, its heartbeat was NEVER refreshed again (no ``finally`` ran)."""
    user = _user("drill_b")
    client = _client(user)
    conv = Conversation.objects.create(user=user)
    conv.messages.create(role="user", content="what changed this week?")

    stream_id = stream_relay.claim_stream(conv)  # a real turn "was" running under this id
    # No touch_heartbeat call: this IS what a killed worker looks like from the outside.

    # A read path (here: loading the conversation) discovers and reaps the dead claim.
    detail = client.get(f"/api/assistant/conversations/{conv.id}")
    assert detail.status_code == 200
    body = detail.json()["data"]
    assert body["active_stream_id"] is None
    assert body["last_stream_error"]["reason"] == "interrupted"

    # Retry recovers it: claims a fresh stream and dispatches a new task (stubbed — this test is
    # about the endpoint's claim/dispatch contract, not re-proving the round trip test above).
    dispatched = {}

    def _fake_delay(**kw):
        dispatched.update(kw)
        dispatched["_called"] = True

    monkeypatch.setattr(run_detached_stream, "delay", _fake_delay)

    resp = client.post(f"/api/assistant/conversations/{conv.id}/retry-turn")

    assert resp.status_code == 200
    assert dispatched.get("_called") is True
    assert dispatched["regenerate"] is True
    conv.refresh_from_db()
    assert conv.active_stream_id is not None  # the retry's own fresh claim
    assert conv.active_stream_id != stream_id
    stream_relay.clear_heartbeat(conv.active_stream_id)  # tidy — no real worker will ever finish it


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_DETACHED_STREAMING=True)
def test_retry_turn_without_a_failed_turn_is_rejected():
    user = _user("retry_nothing")
    client = _client(user)
    conv = Conversation.objects.create(user=user)

    resp = client.post(f"/api/assistant/conversations/{conv.id}/retry-turn")

    assert resp.status_code == 400


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_DETACHED_STREAMING=True)
def test_cancel_stream_publishes_the_signal_the_worker_polls():
    conv = Conversation.objects.create(user=_user("cancel_signal"))
    client = _client(conv.user)
    stream_id = stream_relay.claim_stream(conv)
    stream_relay.touch_heartbeat(stream_id)

    resp = client.post(f"/api/assistant/conversations/{conv.id}/cancel-stream")

    assert resp.status_code == 200
    assert stream_relay.cancel_requested(stream_id) is True
    stream_relay.clear_heartbeat(stream_id)
    stream_relay.clear_cancel(stream_id)
