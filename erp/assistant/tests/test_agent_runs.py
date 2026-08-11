"""AgentRun/AgentStep durability (ai-reliability T5.1) — the loop's write-ahead persistence.

Same monkeypatch pattern as ``test_agent.py``: script ``complete_json``/``complete_stream``, run
the REAL loop, then assert on the ``AgentRun``/``AgentStep`` rows it left behind rather than (only)
the SSE events. State transitions are written BEFORE the loop acts on them, so a row's status is
always trustworthy even when a run ends by exception or client disconnect.
"""
from __future__ import annotations

import pytest
from django.test import override_settings

from erp.assistant.models import AgentRun, AgentStep, Conversation
from erp.assistant.services import agent
from erp.identity.models import User

pytestmark = pytest.mark.django_db


def _actor(username: str = "agent_run_user") -> User:
    user = User.objects.create_user(
        username=username, password="Dev12345!", email=f"{username}@example.test",
    )
    user.is_superuser = True
    user.save(update_fields=["is_superuser"])
    return user


def _script(monkeypatch, decisions: list[dict]):
    it = iter(decisions)
    monkeypatch.setattr(agent, "complete_json", lambda system, user, schema, **_: next(it))


def _stream(monkeypatch, *chunks: str):
    monkeypatch.setattr(agent, "complete_stream", lambda messages, **_: iter(chunks))


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_three_tool_round_run_persists_row_states_at_each_phase(monkeypatch):
    user = _actor()
    conv = Conversation.objects.create(user=user)
    _script(monkeypatch, [
        {"action": "tool", "tool": "sales_summary", "why": "Checking sales", "period": "this_month"},
        {"action": "tool", "tool": "low_stock", "why": "Checking stock", "limit": 5},
        {"action": "tool", "tool": "stock_on_hand", "why": "Checking item", "query": "item-a"},
        {"action": "answer"},
    ])
    _stream(monkeypatch, "All good.")

    list(agent.run(actor=user, conversation=conv, question="how are we doing?"))

    run = AgentRun.objects.get(conversation=conv)
    assert run.status == AgentRun.Status.DONE
    assert run.goal == "how are we doing?"
    assert run.current_step == 3
    assert run.result["used_tool"] == "stock_on_hand"
    assert run.trace_id is not None

    steps = list(run.steps.order_by("seq"))
    assert [s.tool for s in steps] == ["sales_summary", "low_stock", "stock_on_hand"]
    assert [s.seq for s in steps] == [1, 2, 3]
    assert all(s.status == AgentStep.Status.OK for s in steps)
    assert steps[0].args == {"period": "this_month"}


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_mid_run_exception_leaves_an_accurate_failed_row(monkeypatch):
    user = _actor()
    conv = Conversation.objects.create(user=user)
    calls = {"n": 0}

    def flaky(system, user_payload, schema, **_):
        calls["n"] += 1
        if calls["n"] == 1:
            return {"action": "tool", "tool": "sales_summary", "why": "Checking sales",
                    "period": "this_month"}
        raise RuntimeError("provider dropped mid-turn")

    monkeypatch.setattr(agent, "complete_json", flaky)
    _stream(monkeypatch, "unreachable")

    with pytest.raises(RuntimeError):
        list(agent.run(actor=user, conversation=conv, question="anything"))

    run = AgentRun.objects.get(conversation=conv)
    assert run.status == AgentRun.Status.FAILED

    steps = list(run.steps.order_by("seq"))
    # The one tool call that actually completed before the raise is an honest OK, not swept away.
    assert len(steps) == 1
    assert steps[0].status == AgentStep.Status.OK


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_disconnect_mid_tool_call_fails_the_in_flight_step(monkeypatch):
    """A client disconnect (SSE generator ``.close()``) while a step is IN FLIGHT — persisted
    ``running`` but not yet finished — must not leave that row stuck forever."""
    user = _actor()
    conv = Conversation.objects.create(user=user)
    _script(monkeypatch, [
        {"action": "tool", "tool": "sales_summary", "why": "Checking sales", "period": "this_month"},
    ])
    _stream(monkeypatch, "unreachable")

    gen = agent.run(actor=user, conversation=conv, question="anything")
    event = next(gen)  # the "running" step event — persisted write-ahead, tool hasn't run yet
    assert event == {"type": "step", "tool": "sales_summary", "label": "Checking sales",
                     "state": "running"}
    gen.close()  # simulates the SSE view's client-disconnect handling

    run = AgentRun.objects.get(conversation=conv)
    assert run.status == AgentRun.Status.CANCELLED

    step = run.steps.get(seq=1)
    assert step.status == AgentStep.Status.FAILED
    assert step.error == "cancelled"
