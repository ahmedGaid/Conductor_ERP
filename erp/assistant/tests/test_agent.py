"""The agentic loop (plan session 09) — plan → run tools → validate → answer.

The planner (``complete_json``) and the final prose (``complete_stream``) are the two model seams;
we monkeypatch both on the ``agent`` module so the *real* loop runs — tool execution as the actor,
step events, citation merge, persistence, audit — with no live call. ``complete_json`` is driven by
a scripted sequence of decisions so each test pins one loop behaviour.
"""
from __future__ import annotations

import json

import pytest
from django.test import override_settings

from erp.assistant.models import Conversation
from erp.assistant.services import agent, knowledge
from erp.identity.models import User

pytestmark = pytest.mark.django_db


def _actor(username: str = "agent_user") -> User:
    user = User.objects.create_user(
        username=username, password="Dev12345!", email=f"{username}@example.test",
    )
    user.is_superuser = True  # full access — tools never refuse for permission in these tests
    user.save(update_fields=["is_superuser"])
    return user


def _script(monkeypatch, decisions: list[dict]):
    """Feed the planner a fixed sequence of decisions, one per round."""
    it = iter(decisions)

    def fake(system, user, schema, **_):
        return next(it)

    monkeypatch.setattr(agent, "complete_json", fake)


def _stream(monkeypatch, *chunks: str):
    monkeypatch.setattr(agent, "complete_stream", lambda messages, **_: iter(chunks))


def _run(user, conversation, question="anything") -> list[dict]:
    return list(agent.run(actor=user, conversation=conversation, question=question, page=None))


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_two_tool_rounds_then_answer(monkeypatch):
    user = _actor()
    conv = Conversation.objects.create(user=user)
    _script(monkeypatch, [
        {"action": "tool", "tool": "sales_summary", "why": "Checking sales", "period": "this_month"},
        {"action": "tool", "tool": "low_stock", "why": "Checking stock", "limit": 5},
        {"action": "answer"},
    ])
    _stream(monkeypatch, "All ", "good.")

    events = _run(user, conv)

    # Steps stream running→done per tool, in order, then the prose, then citations + done.
    assert [e["type"] for e in events] == [
        "step", "step", "step", "step", "token", "token", "citations", "done",
    ]
    steps = [e for e in events if e["type"] == "step"]
    assert [(s["tool"], s["state"]) for s in steps] == [
        ("sales_summary", "running"), ("sales_summary", "done"),
        ("low_stock", "running"), ("low_stock", "done"),
    ]

    # The assistant message persisted the step trail (summaries, not raw payloads).
    msg = conv.messages.get(role="assistant")
    assert msg.content == "All good."
    persisted = msg.meta["steps"]
    assert [s["tool"] for s in persisted] == ["sales_summary", "low_stock"]
    assert all(s["ok"] for s in persisted)


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_unknown_tool_error_is_fed_back_then_loop_recovers(monkeypatch):
    user = _actor()
    conv = Conversation.objects.create(user=user)
    _script(monkeypatch, [
        {"action": "tool", "tool": "does_not_exist", "why": "First try"},
        {"action": "tool", "tool": "sales_summary", "why": "Checking sales", "period": "this_month"},
        {"action": "answer"},
    ])
    _stream(monkeypatch, "Done.")

    events = _run(user, conv)

    steps = [e for e in events if e["type"] == "step" and e["state"] == "done"]
    # The bad call is marked failed; the model corrects and the loop still reaches an answer.
    assert steps[0]["tool"] == "does_not_exist" and steps[0]["ok"] is False
    assert steps[1]["tool"] == "sales_summary" and steps[1]["ok"] is True
    assert events[-1]["type"] == "done"
    # used_tool is the last tool that *succeeded*, so follow-ups stay sensible.
    assert events[-1]["used_tool"] == "sales_summary"


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_runaway_is_capped_at_max_rounds(monkeypatch):
    user = _actor()
    conv = Conversation.objects.create(user=user)
    calls = {"n": 0}

    def never_answers(system, user, schema, **_):
        calls["n"] += 1
        # A distinct arg each round — this is a runaway planner, not a duplicate-call case (that's
        # covered by test_duplicate_tool_call_blocked below); the dup guard must not mask it.
        return {"action": "tool", "tool": "sales_summary", "why": "loop", "limit": calls["n"]}

    monkeypatch.setattr(agent, "complete_json", never_answers)
    _stream(monkeypatch, "Forced answer.")

    events = _run(user, conv)

    # Exactly MAX_ROUNDS planner calls — it never spins past the cap — then it force-answers.
    assert calls["n"] == agent.MAX_ROUNDS
    running = [e for e in events if e["type"] == "step" and e["state"] == "running"]
    # Distinct args each round mean the dup guard never fires — all MAX_ROUNDS calls actually ran.
    assert len(running) == agent.MAX_ROUNDS
    assert events[-1]["type"] == "done"
    assert conv.messages.get(role="assistant").content == "Forced answer."


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_clarify_short_circuits_without_tools_or_model_stream(monkeypatch):
    user = _actor()
    conv = Conversation.objects.create(user=user)
    _script(monkeypatch, [{"action": "clarify", "question": "Which month do you mean?"}])
    # If the loop wrongly streamed, this text would leak into the answer — assert it never does.
    _stream(monkeypatch, "SHOULD-NOT-APPEAR")

    events = _run(user, conv)

    assert not any(e["type"] == "step" for e in events)  # no tools ran
    tokens = [e["text"] for e in events if e["type"] == "token"]
    assert tokens == ["Which month do you mean?"]
    assert events[-1]["type"] == "done"

    msg = conv.messages.get(role="assistant")
    assert msg.content == "Which month do you mean?"
    assert msg.meta["steps"] == []
    assert msg.meta["citations"] == []


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_loop_runs_search_documents_and_cites(monkeypatch):
    user = _actor()
    conv = Conversation.objects.create(user=user)
    knowledge.ingest_document(
        data=b"Refund policy: customers can return items within 14 days.",
        media_type="text/plain", filename="refunds.txt", title="Refund Policy", actor=user,
    )
    _script(monkeypatch, [
        {"action": "tool", "tool": "search_documents", "why": "Checking policy",
         "query": "refund policy"},
        {"action": "answer"},
    ])
    _stream(monkeypatch, "Refunds allowed within 14 days.")

    events = _run(user, conv, question="what is the refund policy?")

    steps = [e for e in events if e["type"] == "step"]
    assert [(s["tool"], s["state"]) for s in steps] == [
        ("search_documents", "running"), ("search_documents", "done"),
    ]
    assert steps[1]["ok"] is True

    cites_event = next(e for e in events if e["type"] == "citations")
    assert cites_event["citations"][0]["type"] == "document"
    assert cites_event["citations"][0]["value"] == "Refund Policy"


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_document_intent_without_search_is_forced_to_search(monkeypatch):
    """Deterministic grounding guard (FILE_11 follow-up): the planner classifies the question as
    document-shaped but tries to answer without ever calling search_documents — the loop must
    force one real search before the final answer, so the answer is grounded either way."""
    user = _actor()
    conv = Conversation.objects.create(user=user)
    knowledge.ingest_document(
        data=b"Refund policy: customers can return items within 14 days.",
        media_type="text/plain", filename="refunds.txt", title="Refund Policy", actor=user,
    )
    _script(monkeypatch, [{"action": "answer", "intent": "document_search"}])
    _stream(monkeypatch, "Refunds allowed within 14 days.")

    events = _run(user, conv, question="what is the refund policy?")

    steps = [e for e in events if e["type"] == "step"]
    assert [(s["tool"], s["state"]) for s in steps] == [
        ("search_documents", "running"), ("search_documents", "done"),
    ]
    cites_event = next(e for e in events if e["type"] == "citations")
    assert cites_event["citations"][0]["value"] == "Refund Policy"


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_guard_skips_when_search_already_ran(monkeypatch):
    user = _actor()
    conv = Conversation.objects.create(user=user)
    _script(monkeypatch, [
        {"action": "tool", "tool": "search_documents", "why": "Checking", "query": "x",
         "intent": "document_search"},
        {"action": "answer"},
    ])
    _stream(monkeypatch, "No document covers this.")

    events = _run(user, conv, question="policy on x?")

    steps = [e for e in events if e["type"] == "step"]
    assert [(s["tool"], s["state"]) for s in steps] == [
        ("search_documents", "running"), ("search_documents", "done"),
    ]


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_guard_does_not_fire_for_non_document_intent(monkeypatch):
    user = _actor()
    conv = Conversation.objects.create(user=user)
    _script(monkeypatch, [{"action": "answer", "intent": "explain"}])
    _stream(monkeypatch, "FIFO means first-in first-out.")

    events = _run(user, conv, question="what does FIFO mean?")

    assert [e for e in events if e["type"] == "step"] == []


def test_loop_system_contains_source_routing():
    assert "search_documents" in agent._LOOP_SYSTEM
    assert "never" in agent._LOOP_SYSTEM.lower()
    assert "invent" in agent._LOOP_SYSTEM.lower()
    assert "before calling search_documents" in agent._LOOP_SYSTEM


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_intent_recorded_on_message_meta(monkeypatch):
    user = _actor()
    conv = Conversation.objects.create(user=user)
    _script(monkeypatch, [
        {"action": "tool", "tool": "sales_summary", "why": "Checking sales",
         "period": "this_month", "intent": "report"},
        {"action": "answer"},
    ])
    _stream(monkeypatch, "Done.")

    _run(user, conv)

    msg = conv.messages.get(role="assistant")
    assert msg.meta["intent"] == "report"


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_duplicate_tool_call_blocked(monkeypatch):
    user = _actor()
    conv = Conversation.objects.create(user=user)
    _script(monkeypatch, [
        {"action": "tool", "tool": "sales_summary", "why": "Checking sales", "period": "this_month"},
        {"action": "tool", "tool": "sales_summary", "why": "Checking sales again",
         "period": "this_month"},
        {"action": "answer"},
    ])
    captured = {}

    def fake_stream(messages, **_):
        captured["messages"] = messages
        return iter(["Done."])

    monkeypatch.setattr(agent, "complete_stream", fake_stream)

    events = _run(user, conv)

    # Only one real tool execution ran — the duplicate round never fires step events.
    steps = [e for e in events if e["type"] == "step"]
    assert [(s["tool"], s["state"]) for s in steps] == [
        ("sales_summary", "running"), ("sales_summary", "done"),
    ]

    gathered = json.loads(captured["messages"][0]["content"])["data"]
    assert len(gathered) == 2
    assert "error" not in gathered[0]["result"]
    assert "already ran this exact call" in gathered[1]["result"]["error"]

    msg = conv.messages.get(role="assistant")
    assert len(msg.meta["steps"]) == 1  # the duplicate never counts as an executed step


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_same_tool_different_args_allowed(monkeypatch):
    user = _actor()
    conv = Conversation.objects.create(user=user)
    _script(monkeypatch, [
        {"action": "tool", "tool": "stock_on_hand", "why": "Checking item A", "query": "item-a"},
        {"action": "tool", "tool": "stock_on_hand", "why": "Checking item B", "query": "item-b"},
        {"action": "answer"},
    ])
    _stream(monkeypatch, "Done.")

    events = _run(user, conv)

    done_steps = [e for e in events if e["type"] == "step" and e["state"] == "done"]
    assert [s["tool"] for s in done_steps] == ["stock_on_hand", "stock_on_hand"]

    msg = conv.messages.get(role="assistant")
    assert len(msg.meta["steps"]) == 2
