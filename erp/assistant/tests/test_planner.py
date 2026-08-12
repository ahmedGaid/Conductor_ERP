"""The typed planner (ai-reliability T5.2) — a validated Plan before any tool runs.

Two layers are tested separately, on purpose:

- ``planner.validate`` is pure — every rule (unknown tool, step cap, registry-owned
  ``needs_confirm``, renumbering, write-action truncation) is asserted with no provider, no DB and
  no loop, so a regression points straight at the rule that broke.
- the agent loop's use of it goes through the real ``agent.run`` generator with both model seams
  monkeypatched (the same technique as ``test_agent.py``), because the parts most likely to break
  are the seams — the plan event, the cursor, the replan, and above all the FALLBACK: every planner
  failure must land the run on the reactive loop that shipped before this task.
"""
from __future__ import annotations

import pytest
from django.test import override_settings

from erp.assistant.models import AgentRun, Conversation
from erp.assistant.services import agent, planner
from erp.identity.models import User

pytestmark = pytest.mark.django_db

PLANNER_ON = dict(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic",
                  ASSISTANT_TYPED_PLANNER=True)


def _actor(username: str = "planner_user") -> User:
    user = User.objects.create_user(
        username=username, password="Dev12345!", email=f"{username}@example.test",
    )
    user.is_superuser = True
    user.save(update_fields=["is_superuser"])
    return user


def _step(tool: str, *, step: int = 1, why: str = "Checking", intent: str = "this month",
          needs_confirm: bool = False) -> dict:
    return {"step": step, "tool": tool, "args_intent": intent, "why": why,
            "needs_confirm": needs_confirm}


def _plans(monkeypatch, plans: list[dict]):
    """Feed ``planner.make_plan``'s model seam a fixed sequence of raw JSON responses."""
    it = iter(plans)

    def fake(system, user, schema, **_):
        return next(it)

    monkeypatch.setattr(planner, "complete_json", fake)


def _decisions(monkeypatch, decisions: list[dict]):
    it = iter(decisions)
    monkeypatch.setattr(agent, "complete_json", lambda system, user, schema, **_: next(it))


def _stream(monkeypatch, *chunks: str):
    monkeypatch.setattr(agent, "complete_stream", lambda messages, **_: iter(chunks))


# --- validate(): pure rules ----------------------------------------------------------------------

def test_direct_is_valid_and_yields_no_steps():
    steps, reasons = planner.validate({"direct": True, "steps": []})
    assert steps == [] and reasons == []


def test_unknown_tool_invalidates_the_plan():
    steps, reasons = planner.validate(
        {"direct": False, "steps": [_step("sales_summary"), _step("teleport", step=2)]})
    assert steps == []
    assert any("teleport" in r for r in reasons)


def test_over_the_step_cap_is_rejected():
    many = [_step("sales_summary", step=i) for i in range(1, planner.MAX_PLAN_STEPS + 3)]
    steps, reasons = planner.validate({"direct": False, "steps": many})
    assert steps == []
    assert any(str(planner.MAX_PLAN_STEPS) in r for r in reasons)


def test_empty_plan_is_rejected():
    steps, reasons = planner.validate({"direct": False, "steps": []})
    assert steps == [] and reasons


def test_needs_confirm_comes_from_the_registry_not_the_model():
    # The model claims a read-only tool confirms and a write action does not — both are overwritten.
    steps, reasons = planner.validate({"direct": False, "steps": [
        _step("sales_summary", step=1, needs_confirm=True),
        _step("create_sales_order_draft", step=2, needs_confirm=False),
    ]})
    assert reasons == []
    assert [s.needs_confirm for s in steps] == [False, True]


def test_steps_are_renumbered_from_the_accepted_list():
    steps, _ = planner.validate({"direct": False, "steps": [
        _step("sales_summary", step=7), _step("low_stock", step=7),
    ]})
    assert [s.step for s in steps] == [1, 2]


def test_a_write_action_truncates_everything_planned_after_it():
    # The confirm card ends the turn, so a step planned after a write could never run.
    steps, _ = planner.validate({"direct": False, "steps": [
        _step("low_stock", step=1),
        _step("create_purchase_request_draft", step=2),
        _step("sales_summary", step=3),
    ]})
    assert [s.tool for s in steps] == ["low_stock", "create_purchase_request_draft"]


def test_a_step_with_no_why_falls_back_to_a_readable_label():
    steps, _ = planner.validate({"direct": False, "steps": [_step("sales_summary", why="")]})
    assert steps[0].why == "sales summary"


# --- make_plan(): retry, direct, and the two failure exits ---------------------------------------

def test_invalid_plan_is_repaired_on_one_retry(monkeypatch):
    _plans(monkeypatch, [
        {"direct": False, "steps": [_step("not_a_tool")]},
        {"direct": False, "steps": [_step("sales_summary")]},
    ])
    outcome = planner.make_plan(question="how did we do?")
    assert outcome.planned
    assert [s.tool for s in outcome.steps] == ["sales_summary"]


def test_two_invalid_plans_fall_back(monkeypatch):
    _plans(monkeypatch, [{"direct": False, "steps": [_step("not_a_tool")]}] * 2)
    outcome = planner.make_plan(question="how did we do?")
    assert not outcome.planned
    assert outcome.fallback_reason == planner.FALLBACK_INVALID


def test_a_planner_outage_falls_back_instead_of_raising(monkeypatch):
    def boom(*_a, **_k):
        raise RuntimeError("provider down")

    monkeypatch.setattr(planner, "complete_json", boom)
    outcome = planner.make_plan(question="how did we do?")
    assert not outcome.planned
    assert outcome.fallback_reason == planner.FALLBACK_ERROR


def test_direct_is_its_own_fallback_reason(monkeypatch):
    _plans(monkeypatch, [{"direct": True, "steps": []}])
    outcome = planner.make_plan(question="hello")
    assert not outcome.planned
    assert outcome.fallback_reason == planner.FALLBACK_DIRECT


def test_the_repair_retry_is_told_what_was_wrong(monkeypatch):
    seen: list[str] = []

    def fake(system, user, schema, **_):
        seen.append(user)
        return {"direct": False, "steps": [_step("not_a_tool")]}

    monkeypatch.setattr(planner, "complete_json", fake)
    planner.make_plan(question="how did we do?")
    assert len(seen) == 2
    assert "not_a_tool" in seen[1] and "rejected" in seen[1]


# --- the loop walks the plan ---------------------------------------------------------------------

@override_settings(**PLANNER_ON)
def test_plan_streams_up_front_and_the_loop_walks_it(monkeypatch):
    user = _actor()
    conv = Conversation.objects.create(user=user)
    _plans(monkeypatch, [{"direct": False, "steps": [
        _step("sales_summary", step=1, why="Checking sales"),
        _step("low_stock", step=2, why="Checking stock"),
    ]}])
    _decisions(monkeypatch, [
        {"action": "tool", "tool": "sales_summary", "why": "Checking sales", "period": "this_month"},
        {"action": "tool", "tool": "low_stock", "why": "Checking stock", "limit": 5},
        {"action": "answer"},
    ])
    _stream(monkeypatch, "Done.")

    events = list(agent.run(actor=user, conversation=conv, question="sales and stock"))

    # The plan is the FIRST event — the panel paints it before any tool runs.
    assert events[0]["type"] == "plan"
    assert [s["tool"] for s in events[0]["steps"]] == ["sales_summary", "low_stock"]
    assert all(s["needs_confirm"] is False for s in events[0]["steps"])
    assert [(e["tool"], e["state"]) for e in events if e["type"] == "step"] == [
        ("sales_summary", "running"), ("sales_summary", "done"),
        ("low_stock", "running"), ("low_stock", "done"),
    ]
    # Durable: the plan is persisted on the run, and visible on the trace for ops.
    run = AgentRun.objects.get(conversation=conv)
    assert [s["tool"] for s in run.plan] == ["sales_summary", "low_stock"]
    assert run.status == AgentRun.Status.DONE


@override_settings(**PLANNER_ON)
def test_planner_fallback_runs_the_reactive_loop_unchanged(monkeypatch):
    user = _actor()
    conv = Conversation.objects.create(user=user)
    _plans(monkeypatch, [{"direct": True, "steps": []}])
    _decisions(monkeypatch, [
        {"action": "tool", "tool": "sales_summary", "why": "Checking sales", "period": "this_month"},
        {"action": "answer"},
    ])
    _stream(monkeypatch, "Fine.")

    events = list(agent.run(actor=user, conversation=conv, question="sales?"))

    assert not [e for e in events if e["type"] == "plan"]  # nothing planned, nothing painted
    assert [(e["tool"], e["state"]) for e in events if e["type"] == "step"] == [
        ("sales_summary", "running"), ("sales_summary", "done"),
    ]
    assert conv.messages.get(role="assistant").content == "Fine."
    assert AgentRun.objects.get(conversation=conv).plan == []


@override_settings(**PLANNER_ON)
def test_a_failed_step_triggers_one_replan(monkeypatch):
    user = _actor()
    conv = Conversation.objects.create(user=user)
    _plans(monkeypatch, [
        {"direct": False, "steps": [_step("sales_summary", why="Checking sales")]},
        {"direct": False, "steps": [_step("low_stock", why="Checking stock")]},
    ])
    _decisions(monkeypatch, [
        # An unknown tool name — ``_run_tool`` turns it into an {"error": ...} result, i.e. a
        # failed step, which is what the replan reacts to.
        {"action": "tool", "tool": "no_such_tool", "why": "Checking sales"},
        {"action": "tool", "tool": "low_stock", "why": "Checking stock", "limit": 5},
        {"action": "answer"},
    ])
    _stream(monkeypatch, "Recovered.")

    events = list(agent.run(actor=user, conversation=conv, question="sales and stock"))

    plans = [e for e in events if e["type"] == "plan"]
    assert len(plans) == 2                                  # the original, then the replan
    assert [s["tool"] for s in plans[1]["steps"]] == ["low_stock"]
    assert conv.messages.get(role="assistant").content == "Recovered."
    assert [s["tool"] for s in AgentRun.objects.get(conversation=conv).plan] == ["low_stock"]


@override_settings(**PLANNER_ON)
def test_replan_cap_ends_the_turn_with_an_honest_answer(monkeypatch):
    user = _actor()
    conv = Conversation.objects.create(user=user)
    # Every plan names a tool the loop then fails on: the cap must stop the re-planning.
    _plans(monkeypatch, [{"direct": False, "steps": [_step("sales_summary", why="Checking sales")]}]
           * (planner.MAX_REPLANS + 2))
    _decisions(monkeypatch, [{"action": "tool", "tool": "no_such_tool", "why": "Checking sales"}] * 6)
    seen_user: list[str] = []

    def fake_stream(messages, **_):
        seen_user.append(messages[0]["content"])
        return iter(["Partly."])

    monkeypatch.setattr(agent, "complete_stream", fake_stream)

    events = list(agent.run(actor=user, conversation=conv, question="sales and stock"))

    # MAX_REPLANS replans happened, then the run stopped instead of spinning to the round cap.
    assert len([e for e in events if e["type"] == "plan"]) == 1 + planner.MAX_REPLANS
    # Only the FIRST attempt actually ran: the loop's duplicate-call guard stops the identical
    # retries before they execute, and each of those still counts as a step that did not advance —
    # which is exactly what drives the replans above.
    assert len([e for e in events if e["type"] == "step" and e["state"] == "running"]) == 1
    # The answer is told to name the step it could not finish — never a silent partial answer.
    assert "could not be completed" in seen_user[-1]
    assert conv.messages.get(role="assistant").content == "Partly."


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic",
                   ASSISTANT_TYPED_PLANNER=False)
def test_flag_off_never_calls_the_planner(monkeypatch):
    user = _actor()
    conv = Conversation.objects.create(user=user)

    def boom(*_a, **_k):  # pragma: no cover - asserted by not being reached
        raise AssertionError("the planner must not run while the flag is off")

    monkeypatch.setattr(planner, "complete_json", boom)
    _decisions(monkeypatch, [
        {"action": "tool", "tool": "sales_summary", "why": "Checking sales", "period": "this_month"},
        {"action": "answer"},
    ])
    _stream(monkeypatch, "Fine.")

    events = list(agent.run(actor=user, conversation=conv, question="sales?"))

    assert not [e for e in events if e["type"] == "plan"]
    assert conv.messages.get(role="assistant").content == "Fine."
