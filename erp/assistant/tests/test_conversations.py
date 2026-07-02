"""Conversation persistence — CRUD/search/ownership + the persisted ask flow (plan session 01).

The model is never called live: for the ask test we monkeypatch the single ``complete_json`` seam
(route → answer) exactly like ``test_ask.py``, so the real persistence path runs and only the
network hop is faked.
"""
from __future__ import annotations

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from erp.assistant.models import Conversation
from erp.assistant.services import ask
from erp.identity.models import User

pytestmark = pytest.mark.django_db

CONV_URL = "/api/assistant/conversations"
ASK_URL = "/api/assistant/ask"


def _client(username: str = "conv_owner") -> APIClient:
    user = User.objects.create_user(
        username=username, password="Dev12345!", email=f"{username}@example.test",
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _replies(monkeypatch, *canned: dict):
    seq = list(canned)

    def fake(system, user, schema, **_):
        return seq.pop(0)

    monkeypatch.setattr(ask, "complete_json", fake)


def test_create_list_rename_pin_archive_delete_round_trip():
    client = _client()

    created = client.post(CONV_URL, {}, format="json")
    assert created.status_code == 201
    cid = created.json()["data"]["id"]

    listed = client.get(CONV_URL).json()["data"]
    assert [c["id"] for c in listed] == [cid]

    renamed = client.patch(f"{CONV_URL}/{cid}", {"title": "Q3 review"}, format="json")
    assert renamed.status_code == 200
    assert renamed.json()["data"]["title"] == "Q3 review"

    pinned = client.patch(f"{CONV_URL}/{cid}", {"pinned": True}, format="json")
    assert pinned.json()["data"]["pinned"] is True

    # Archived threads drop out of the default list, appear under ?archived=1.
    client.patch(f"{CONV_URL}/{cid}", {"archived": True}, format="json")
    assert client.get(CONV_URL).json()["data"] == []
    assert [c["id"] for c in client.get(f"{CONV_URL}?archived=1").json()["data"]] == [cid]

    assert client.delete(f"{CONV_URL}/{cid}").status_code == 204
    assert client.get(f"{CONV_URL}/{cid}").status_code == 404


def test_pin_moves_conversation_to_top():
    client = _client()
    first = client.post(CONV_URL, {"title": "old"}, format="json").json()["data"]["id"]
    second = client.post(CONV_URL, {"title": "new"}, format="json").json()["data"]["id"]

    # Default order is -updated_at, so the newer one leads.
    assert [c["id"] for c in client.get(CONV_URL).json()["data"]] == [second, first]

    client.patch(f"{CONV_URL}/{first}", {"pinned": True}, format="json")
    assert [c["id"] for c in client.get(CONV_URL).json()["data"]] == [first, second]


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_search_matches_message_content(monkeypatch):
    client = _client()
    cid = client.post(CONV_URL, {}, format="json").json()["data"]["id"]
    _replies(
        monkeypatch,
        {"tool": "none", "period": None, "query": None, "limit": None},
        {"answer": "تمام"},
    )
    client.post(ASK_URL, {"question": "متأخرات التحصيل", "conversation_id": cid}, format="json")

    hits = client.get(f"{CONV_URL}?q=التحصيل").json()["data"]
    assert [c["id"] for c in hits] == [cid]
    assert client.get(f"{CONV_URL}?q=nothing-here").json()["data"] == []


def test_other_user_cannot_see_patch_or_delete():
    owner = _client("owner_a")
    cid = owner.post(CONV_URL, {"title": "private"}, format="json").json()["data"]["id"]

    intruder = _client("intruder_b")
    assert intruder.get(f"{CONV_URL}/{cid}").status_code == 404
    assert intruder.patch(f"{CONV_URL}/{cid}", {"title": "hax"}, format="json").status_code == 404
    assert intruder.delete(f"{CONV_URL}/{cid}").status_code == 404
    # Not listed for the intruder either.
    assert intruder.get(CONV_URL).json()["data"] == []


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_ask_with_conversation_appends_two_messages_and_auto_titles(monkeypatch):
    client = _client()
    cid = client.post(CONV_URL, {}, format="json").json()["data"]["id"]
    _replies(
        monkeypatch,
        {"tool": "none", "period": None, "query": None, "limit": None},
        {"answer": "أقدر أساعدك في المبيعات."},
    )

    resp = client.post(
        ASK_URL, {"question": "ازيك يا مساعد", "conversation_id": cid}, format="json",
    )
    assert resp.status_code == 200

    detail = client.get(f"{CONV_URL}/{cid}").json()["data"]
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant"]
    assert detail["messages"][0]["content"] == "ازيك يا مساعد"
    assert detail["messages"][1]["content"] == "أقدر أساعدك في المبيعات."
    # Empty title filled from the first question (first 60 chars).
    assert detail["title"] == "ازيك يا مساعد"


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_ask_with_foreign_conversation_is_404(monkeypatch):
    owner = _client("owner_c")
    cid = owner.post(CONV_URL, {}, format="json").json()["data"]["id"]
    _replies(monkeypatch, {"tool": "none", "period": None, "query": None, "limit": None},
             {"answer": "x"})
    intruder = _client("intruder_c")
    resp = intruder.post(ASK_URL, {"question": "hi", "conversation_id": cid}, format="json")
    assert resp.status_code == 404


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_ask_without_conversation_still_works(monkeypatch):
    client = _client()
    _replies(monkeypatch, {"tool": "none", "period": None, "query": None, "limit": None},
             {"answer": "ok"})
    resp = client.post(ASK_URL, {"question": "hello"}, format="json")
    assert resp.status_code == 200
    assert resp.json()["data"]["used_tool"] is None
    assert Conversation.objects.count() == 0
