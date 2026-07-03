"""Streaming chat endpoint (SSE) — mocked model, no live calls in gates.

The answer step streams token-by-token via ``complete_stream``. We monkeypatch that single seam
(and ``complete_json`` for the route step) so the real pipeline runs — routing, scoped tool call,
citation building, persistence, audit — and only the network hop is faked.
"""
from __future__ import annotations

import json

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from erp.assistant.models import Conversation, Message
from erp.assistant.services import ask
from erp.identity.models import User

pytestmark = pytest.mark.django_db

CHAT_URL = "/api/assistant/chat"


def _client(username: str = "chat_user") -> APIClient:
    user = User.objects.create_user(
        username=username, password="Dev12345!", email=f"{username}@example.test",
    )
    user.is_superuser = True
    user.save(update_fields=["is_superuser"])
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _conversation(client: APIClient) -> int:
    return client.post("/api/assistant/conversations", {}, format="json").json()["data"]["id"]


def _route_none(monkeypatch):
    """Route to no tool so the pipeline reaches the (mocked) streaming answer with empty data."""
    monkeypatch.setattr(
        ask, "complete_json",
        lambda system, user, schema, **_: {"tool": "none", "period": None, "query": None, "limit": None},
    )


def _stream(monkeypatch, *chunks: str):
    monkeypatch.setattr(ask, "complete_stream", lambda messages, **_: iter(chunks))


def _events(resp) -> list[dict]:
    body = b"".join(resp.streaming_content).decode()
    out = []
    for frame in body.split("\n\n"):
        frame = frame.strip()
        if frame.startswith("data:"):
            out.append(json.loads(frame[len("data:"):].strip()))
    return out


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_stream_emits_tokens_then_done_and_persists_both_messages(monkeypatch):
    client = _client()
    cid = _conversation(client)
    _route_none(monkeypatch)
    _stream(monkeypatch, "Hel", "lo ", "world")

    resp = client.post(CHAT_URL, {"conversation_id": cid, "message": "hi"}, format="json")
    assert resp.status_code == 200
    assert resp["Content-Type"] == "text/event-stream"

    events = _events(resp)
    assert [e["type"] for e in events] == ["token", "token", "token", "citations", "done"]
    assert [e["text"] for e in events if e["type"] == "token"] == ["Hel", "lo ", "world"]

    # Both messages persisted; assistant text = the joined chunks.
    conversation = Conversation.objects.get(pk=cid)
    roles = list(conversation.messages.values_list("role", "content"))
    assert roles == [("user", "hi"), ("assistant", "Hello world")]
    assert events[-1]["message_id"] == conversation.messages.get(role="assistant").id


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_unknown_conversation_id_is_404_before_streaming(monkeypatch):
    client = _client()
    _route_none(monkeypatch)
    _stream(monkeypatch, "x")

    resp = client.post(CHAT_URL, {"conversation_id": 999999, "message": "hi"}, format="json")
    assert resp.status_code == 404
    # Nothing was persisted — the guard runs before any streaming.
    assert Message.objects.count() == 0


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_foreign_conversation_is_404(monkeypatch):
    owner = _client("owner_chat")
    cid = _conversation(owner)
    _route_none(monkeypatch)
    _stream(monkeypatch, "x")

    intruder = _client("intruder_chat")
    resp = intruder.post(CHAT_URL, {"conversation_id": cid, "message": "hi"}, format="json")
    assert resp.status_code == 404


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_blank_and_overlong_messages_are_rejected(monkeypatch):
    client = _client()
    cid = _conversation(client)
    assert client.post(CHAT_URL, {"conversation_id": cid, "message": "  "}, format="json").status_code == 400
    long_msg = "أ" * (ask.MAX_QUESTION_CHARS + 1)
    assert client.post(
        CHAT_URL, {"conversation_id": cid, "message": long_msg}, format="json",
    ).status_code == 400


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_regenerate_replaces_answer_without_new_user_turn(monkeypatch):
    client = _client()
    cid = _conversation(client)
    _route_none(monkeypatch)
    _stream(monkeypatch, "first")
    _events(client.post(CHAT_URL, {"conversation_id": cid, "message": "hi"}, format="json"))

    _stream(monkeypatch, "second")
    resp = client.post(CHAT_URL, {"conversation_id": cid, "regenerate": True}, format="json")
    assert resp.status_code == 200
    events = _events(resp)
    assert events[-1]["type"] == "done"

    # No duplicate question; the old answer is gone, replaced by the fresh one.
    conversation = Conversation.objects.get(pk=cid)
    roles = list(conversation.messages.values_list("role", "content"))
    assert roles == [("user", "hi"), ("assistant", "second")]


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_regenerate_without_prior_question_is_400(monkeypatch):
    client = _client()
    cid = _conversation(client)
    _route_none(monkeypatch)
    _stream(monkeypatch, "x")
    resp = client.post(CHAT_URL, {"conversation_id": cid, "regenerate": True}, format="json")
    assert resp.status_code == 400


@override_settings(ASSISTANT_ENABLED=False)
def test_disabled_endpoint_is_404():
    client = _client()
    resp = client.post(CHAT_URL, {"conversation_id": 1, "message": "hi"}, format="json")
    assert resp.status_code == 404
