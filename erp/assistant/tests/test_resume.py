"""Workflow continuity (plan session 13) — a guided detour returns and resumes the paused work.

The return half of session 12: a suggestion sent the user off to create a missing record; when they
come back ``resume_detour`` settles the card, records an honest ``detour_return`` turn, and rebuilds
the paused proposal against the now-existing record — the ORIGINAL extracted/entered values intact,
no re-extraction. These pin the service seam (``agent.resume_detour``); the loop that produces the
paused ``meta.pending`` is pinned in ``test_suggestions``.
"""
from __future__ import annotations

import pytest
from django.test import override_settings

from erp.assistant.models import Conversation, Message
from erp.assistant.services import agent
from erp.identity.models import User
from erp.inventory.domain.models import Warehouse
from erp.inventory.domain.models import Item
from erp.sales.domain.models import Customer

pytestmark = pytest.mark.django_db


def _admin(username: str = "res_admin") -> User:
    u = User.objects.create_user(username=username, password="Dev12345!",
                                 email=f"{username}@example.test")
    u.is_superuser = True
    u.save(update_fields=["is_superuser"])
    return u


def _paused_message(user, conv, monkeypatch, *, customer="ABC Trading") -> Message:
    """Drive the loop to the exact state session 13 resumes from: a sales-order proposal blocked on a
    missing customer, so the assistant message carries ``meta.suggestion`` (open) + ``meta.pending``
    (the blocked decision). Item + warehouse already exist, so the ONLY blocker is the customer."""
    Item.objects.create(sku="SKU-1", name="Blue Widget")
    Warehouse.objects.create(code="WH-1", name="Main")
    decisions = iter([
        {"action": "propose", "name": "create_sales_order_draft", "why": "Drafting order",
         "customer": customer, "items": [{"item": "SKU-1", "quantity": "1"}], "warehouse": "WH-1"},
        {"action": "suggest", "resume": "I'll prepare the sales order for ABC Trading."},
    ])
    monkeypatch.setattr(agent, "complete_json", lambda *a, **k: next(decisions))
    monkeypatch.setattr(agent, "complete_stream", lambda messages, **_: iter(["On it."]))
    list(agent.run(actor=user, conversation=conv, question="order for ABC Trading"))
    msg = conv.messages.get(role="assistant")
    assert msg.meta["suggestion"]["status"] == "open"
    assert msg.meta["pending"]["name"] == "create_sales_order_draft"
    return msg


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_resume_with_resolved_record_settles_and_reproposes(monkeypatch):
    user = _admin()
    conv = Conversation.objects.create(user=user)
    msg = _paused_message(user, conv, monkeypatch)

    # The user created the customer during the detour; now they're back.
    Customer.objects.create(code="C-NEW", name="ABC Trading")
    monkeypatch.setattr(agent, "complete_stream", lambda messages, **_: iter(["Welcome back."]))
    events = list(agent.resume_detour(
        actor=user, conversation=conv, source_message=msg,
        resolved={"entity": "customer", "id": "C-NEW", "label": "ABC Trading"},
    ))

    # A fresh proposal card is emitted with the paused order's original lines intact.
    proposal = next(e for e in events if e["type"] == "proposal")
    assert proposal["proposal"]["status"] == "pending"
    assert proposal["proposal"]["action"] == "create_sales_order_draft"

    # The original card settles (single-use, reload-safe) and the reply carries the proposal.
    msg.refresh_from_db()
    assert msg.meta["suggestion"]["status"] == "resolved"
    reply = conv.messages.filter(role="assistant").last()
    assert reply.meta["kind"] == "detour_return_reply"
    assert reply.meta["proposal"]["action"] == "create_sales_order_draft"


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_resume_null_reresolves_by_query(monkeypatch):
    user = _admin()
    conv = Conversation.objects.create(user=user)
    msg = _paused_message(user, conv, monkeypatch)

    # "I'm done" without our capturing a record: the customer now exists, found by the pending query.
    Customer.objects.create(code="C-NEW", name="ABC Trading")
    monkeypatch.setattr(agent, "complete_stream", lambda messages, **_: iter(["Welcome back."]))
    events = list(agent.resume_detour(
        actor=user, conversation=conv, source_message=msg, resolved=None,
    ))
    assert any(e["type"] == "proposal" for e in events)
    msg.refresh_from_db()
    assert msg.meta["suggestion"]["status"] == "resolved"


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_resume_still_missing_reopens_card(monkeypatch):
    user = _admin()
    conv = Conversation.objects.create(user=user)
    msg = _paused_message(user, conv, monkeypatch)

    # The user came back without creating the customer — the record still can't be found.
    monkeypatch.setattr(agent, "complete_stream", lambda messages, **_: iter(["Still missing."]))
    events = list(agent.resume_detour(
        actor=user, conversation=conv, source_message=msg, resolved=None,
    ))
    assert not any(e["type"] == "proposal" for e in events)  # nothing to propose yet
    msg.refresh_from_db()
    assert msg.meta["suggestion"]["status"] == "open"  # card un-settles, actionable again
    reply = conv.messages.filter(role="assistant").last()
    assert "proposal" not in reply.meta


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_detour_return_turn_recorded_honestly_in_transcript(monkeypatch):
    user = _admin()
    conv = Conversation.objects.create(user=user)
    msg = _paused_message(user, conv, monkeypatch)
    Customer.objects.create(code="C-NEW", name="ABC Trading")
    monkeypatch.setattr(agent, "complete_stream", lambda messages, **_: iter(["Welcome back."]))
    list(agent.resume_detour(
        actor=user, conversation=conv, source_message=msg,
        resolved={"entity": "customer", "id": "C-NEW", "label": "ABC Trading"},
    ))
    turn = conv.messages.filter(role="user", meta__kind="detour_return").get()
    assert turn.meta["entity"] == "customer"
    assert turn.meta["label"] == "ABC Trading"
    assert turn.content  # a real, honest sentence — not blank


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_resume_makes_no_planner_or_vision_call(monkeypatch):
    """Task D: resume reuses the paused args — it never re-plans and never re-runs the vision/JSON
    seam (``complete_json``). If it did, the already-extracted work would be redone (and cost)."""
    user = _admin()
    conv = Conversation.objects.create(user=user)
    msg = _paused_message(user, conv, monkeypatch)
    Customer.objects.create(code="C-NEW", name="ABC Trading")

    def _forbidden(*a, **k):
        raise AssertionError("resume must not call complete_json (no re-plan, no re-extraction)")

    monkeypatch.setattr(agent, "complete_json", _forbidden)
    monkeypatch.setattr(agent, "complete_stream", lambda messages, **_: iter(["Welcome back."]))
    events = list(agent.resume_detour(
        actor=user, conversation=conv, source_message=msg,
        resolved={"entity": "customer", "id": "C-NEW", "label": "ABC Trading"},
    ))
    assert any(e["type"] == "proposal" for e in events)  # succeeded without any planner/vision call
