"""Embedded page assistant (plan session 11) — the page record becomes the conversation's subject.

Three behaviours are pinned: the envelope names the record the user is viewing (or marks it
background once detached), the loop prompt carries the pronoun-resolution rule only while the
record is attached, and a scripted loop actually reaches the record's detail tool. The model seams
are monkeypatched exactly as in ``test_agent``; the tools run for real, as the actor.
"""
from __future__ import annotations

import pytest
from django.test import override_settings

from erp.assistant.models import Conversation
from erp.assistant.services import agent
from erp.assistant.services.context import build_system_prompt
from erp.assistant.tools import TOOLS
from erp.crm.domain.models import Opportunity
from erp.identity.models import User

pytestmark = pytest.mark.django_db


def _actor(username: str = "page_user") -> User:
    user = User.objects.create_user(
        username=username, password="Dev12345!", email=f"{username}@example.test",
    )
    user.is_superuser = True  # full access — tools never refuse for permission in these tests
    user.save(update_fields=["is_superuser"])
    return user


def _page(detached: bool = False) -> dict:
    page = {
        "path": "/sales/orders/42",
        "module": "sales",
        "language": "ar",
        "record": {"type": "sales.orders", "id": "42", "label": "SO-1042"},
    }
    if detached:
        page["detached"] = True
    return page


def _stream(monkeypatch, *chunks: str):
    monkeypatch.setattr(agent, "complete_stream", lambda messages, **_: iter(chunks))


# --- the envelope (context.py) -------------------------------------------------------------------

def test_envelope_names_the_viewed_record():
    actor = _actor()
    prompt = build_system_prompt(actor, page=_page())
    assert "They are viewing sales.orders SO-1042." in prompt


def test_detached_record_becomes_background_only():
    actor = _actor()
    prompt = build_system_prompt(actor, page=_page(detached=True))
    assert "They are viewing" not in prompt
    assert "detached it from this conversation" in prompt
    assert "SO-1042" in prompt  # still present — background, not erased
    # The rest of the page block survives detach: the module line still grounds navigation help.
    assert "sales module" in prompt


# --- the loop prompt (agent.py) ------------------------------------------------------------------

def _capture_loop_system(monkeypatch, decisions: list[dict]) -> dict:
    captured: dict = {}
    it = iter(decisions)

    def fake(system, user, schema, **_):
        captured.setdefault("system", system)
        return next(it)

    monkeypatch.setattr(agent, "complete_json", fake)
    return captured


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_loop_prompt_carries_resolution_rule_with_record(monkeypatch):
    user = _actor()
    conv = Conversation.objects.create(user=user)
    captured = _capture_loop_system(monkeypatch, [{"action": "answer"}])
    _stream(monkeypatch, "Done.")

    list(agent.run(actor=user, conversation=conv, question="what's the margin on this?",
                   page=_page()))

    system = captured["system"]
    assert "sales.orders 42 (SO-1042)" in system
    assert "resolve to this page record" in system
    assert "هذا الأمر" in system  # the rule covers Arabic bare references too


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_detached_page_renders_no_resolution_rule(monkeypatch):
    user = _actor()
    conv = Conversation.objects.create(user=user)
    captured = _capture_loop_system(monkeypatch, [{"action": "answer"}])
    _stream(monkeypatch, "Done.")

    list(agent.run(actor=user, conversation=conv, question="what's the margin on this?",
                   page=_page(detached=True)))

    assert "resolve to this page record" not in captured["system"]


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_scripted_loop_resolves_this_order_to_the_detail_tool(monkeypatch):
    """With the rule in place the planner's scripted first move is the record's detail tool with
    the record identifier — the loop must execute it for real and stream its step events."""
    user = _actor()
    conv = Conversation.objects.create(user=user)
    _capture_loop_system(monkeypatch, [
        {"action": "tool", "tool": "find_orders", "why": "Checking this order", "query": "SO-1042"},
        {"action": "answer"},
    ])
    _stream(monkeypatch, "It is a confirmed order.")

    events = list(agent.run(actor=user, conversation=conv, question="ما حالة هذا الأمر؟",
                            page=_page()))

    steps = [e for e in events if e["type"] == "step"]
    assert [(s["tool"], s["state"]) for s in steps] == [
        ("find_orders", "running"), ("find_orders", "done"),
    ]
    assert steps[1]["ok"] is True
    assert events[-1]["type"] == "done"


# --- the one thin tool added for DocumentCrumb coverage (crm.opportunities) ----------------------

def test_find_opportunities_tool_returns_scoped_rows():
    actor = _actor()
    Opportunity.objects.create(number="OPP-0001", name="Warehouse expansion",
                               customer_code="C-00001", amount_minor=1_250_00)

    result = TOOLS["find_opportunities"].run(actor, query="OPP-0001")

    rows = result["opportunities"]
    assert len(rows) == 1
    assert rows[0]["number"] == "OPP-0001"
    assert rows[0]["stage"] == "qualifying"
    assert rows[0]["amount"] == "1,250.00 EGP"  # money formatted at the edge, server-side
