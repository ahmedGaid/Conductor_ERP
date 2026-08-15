"""Structured clarify + mid-turn cost stop (ai-reliability T5.10).

Three layers, tested separately on purpose:

- ``services.clarify`` is pure — the option rules (2–4, one recommended, no duplicates, free-text
  fallback) are asserted with no provider, no DB, no loop.
- the parking/resume path goes through the real ``agent.run`` / ``agent.resume_clarify``
  generators with both model seams monkeypatched (same technique as ``test_agent.py``): what
  matters is that the parked run keeps what it gathered and that the answer CONTINUES it rather
  than starting over.
- the budget stop goes through the real ``gateway.budgets`` rows, because the thing worth
  protecting is that a turn out of money still answers calmly from what it has.
"""
from __future__ import annotations

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from erp.assistant.models import AgentRun, Budget, Conversation, Message, SpendRollup
from erp.assistant.services import agent, clarify
from erp.identity.models import User

pytestmark = pytest.mark.django_db

AI_ON = dict(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")


def _actor(username: str = "clarify_user") -> User:
    user = User.objects.create_user(
        username=username, password="Dev12345!", email=f"{username}@example.test",
    )
    user.is_superuser = True
    user.save(update_fields=["is_superuser"])
    return user


def _decisions(monkeypatch, decisions: list[dict]):
    it = iter(decisions)
    monkeypatch.setattr(agent, "complete_json", lambda system, user, schema, **_: next(it))


def _capture_decisions(monkeypatch, decisions: list[dict]) -> list[str]:
    """Same, but keeps every round's user payload so a test can assert what the model was told."""
    seen: list[str] = []
    it = iter(decisions)

    def fake(system, user, schema, **_):
        seen.append(user)
        return next(it)

    monkeypatch.setattr(agent, "complete_json", fake)
    return seen


def _stream(monkeypatch, *chunks: str):
    monkeypatch.setattr(agent, "complete_stream", lambda messages, **_: iter(chunks))


def _capture_stream(monkeypatch, *chunks: str) -> list[str]:
    seen: list[str] = []

    def fake(messages, **_):
        seen.append(messages[0]["content"])
        return iter(chunks)

    monkeypatch.setattr(agent, "complete_stream", fake)
    return seen


def _clarify_decision(question: str, options: list[dict] | None) -> dict:
    return {"action": "clarify", "why": "Need one detail", "question": question,
            "options": options, "intent": "lookup"}


def _tool_decision(tool: str, **kwargs) -> dict:
    return {"action": "tool", "why": f"Checking {tool}", "tool": tool, "intent": "lookup", **kwargs}


def _drain(events) -> list[dict]:
    return list(events)


# --- pure: the option rules -----------------------------------------------------------------------

def test_two_options_survive_as_a_card():
    card = clarify.build_card(_clarify_decision(
        "Which period?", [{"label": "This month"}, {"label": "Last month"}]))
    assert card["question"] == "Which period?"
    assert [o["label"] for o in card["options"]] == ["This month", "Last month"]
    assert card["allow_free_text"] is True and card["status"] == "open"
    assert clarify.parks(card)


def test_one_option_is_not_a_choice_and_degrades_to_free_text():
    card = clarify.build_card(_clarify_decision("Which customer?", [{"label": "ABC Trading"}]))
    assert card["options"] == []
    # Still a legal question — it just gets typed, not tapped, so it does not park the run.
    assert not clarify.parks(card)


def test_options_are_capped_at_four():
    card = clarify.build_card(_clarify_decision(
        "Which?", [{"label": f"Option {i}"} for i in range(1, 8)]))
    assert len(card["options"]) == clarify.MAX_OPTIONS


def test_duplicate_labels_are_dropped_case_insensitively():
    card = clarify.build_card(_clarify_decision(
        "Which?", [{"label": "Draft"}, {"label": "draft"}, {"label": "Final"}]))
    assert [o["label"] for o in card["options"]] == ["Draft", "Final"]


def test_at_most_one_option_is_recommended():
    card = clarify.build_card(_clarify_decision("Which?", [
        {"label": "A", "recommended": True},
        {"label": "B", "recommended": True},
        {"label": "C", "recommended": True},
    ]))
    assert [o.get("recommended") for o in card["options"]] == [True, None, None]


def test_labels_and_descriptions_are_trimmed_to_a_glance():
    card = clarify.build_card(_clarify_decision("Which?", [
        {"label": "x" * 200, "description": "y" * 400}, {"label": "B"},
    ]))
    assert len(card["options"][0]["label"]) == clarify.MAX_LABEL_CHARS
    assert len(card["options"][0]["description"]) == clarify.MAX_DESCRIPTION_CHARS


def test_a_clarify_with_no_question_is_no_card_at_all():
    assert clarify.build_card(_clarify_decision("   ", [{"label": "A"}, {"label": "B"}])) is None
    assert clarify.build_card({}) is None
    assert not clarify.parks(None)


def test_garbage_options_are_ignored_rather_than_crashing():
    card = clarify.build_card(_clarify_decision(
        "Which?", ["nope", {"no_label": 1}, {"label": ""}, {"label": "A"}, {"label": "B"}]))
    assert [o["label"] for o in card["options"]] == ["A", "B"]


def test_the_answer_becomes_a_gathered_result():
    result = clarify.answer_result("Which period?", "Last month")
    assert result["tool"] == clarify.USER_ANSWER_TOOL
    assert result["data"] == {"question": "Which period?", "answer": "Last month"}


# --- parking: the run waits instead of ending -----------------------------------------------------

@override_settings(**AI_ON)
def test_a_clarify_with_options_parks_the_run_with_what_it_gathered(monkeypatch):
    actor = _actor()
    conversation = Conversation.objects.create(user=actor)
    _decisions(monkeypatch, [
        _tool_decision("sales_summary", period="this_month"),
        _clarify_decision("Which period did you mean?",
                          [{"label": "This month", "recommended": True}, {"label": "Last month"}]),
    ])
    _stream(monkeypatch, "unused")

    events = _drain(agent.run(actor=actor, conversation=conversation, question="How were sales?"))

    run = AgentRun.objects.get(conversation=conversation)
    assert run.status == AgentRun.Status.WAITING_CLARIFY
    # What it already fetched is kept — the whole point of parking instead of ending.
    assert [g["tool"] for g in run.parked["gathered"]] == ["sales_summary"]
    assert run.parked["question"] == "How were sales?"

    card_events = [e for e in events if e["type"] == "clarify"]
    assert len(card_events) == 1
    assert card_events[0]["clarify"]["run_id"] == str(run.id)
    assert card_events[0]["clarify"]["options"][0]["recommended"] is True

    message = Message.objects.filter(conversation=conversation, role="assistant").last()
    assert message.meta["clarify"]["status"] == "open"
    assert message.meta["stop_reason"] == "clarify"
    assert message.content == "Which period did you mean?"


@override_settings(**AI_ON)
def test_a_free_text_clarify_does_not_park(monkeypatch):
    actor = _actor()
    conversation = Conversation.objects.create(user=actor)
    _decisions(monkeypatch, [_clarify_decision("Which customer do you mean?", None)])
    _stream(monkeypatch, "unused")

    events = _drain(agent.run(actor=actor, conversation=conversation, question="Show the orders"))

    run = AgentRun.objects.get(conversation=conversation)
    assert run.status == AgentRun.Status.DONE
    assert run.parked == {}
    assert not [e for e in events if e["type"] == "clarify"]
    message = Message.objects.filter(conversation=conversation, role="assistant").last()
    assert message.content == "Which customer do you mean?"
    assert "clarify" not in message.meta or not message.meta["clarify"]["options"]


# --- resume: the answer continues the SAME run ----------------------------------------------------

def _park(monkeypatch, actor, conversation, question="How were sales?") -> Message:
    _decisions(monkeypatch, [
        _tool_decision("sales_summary", period="this_month"),
        _clarify_decision("Which period did you mean?",
                          [{"label": "This month"}, {"label": "Last month"}]),
    ])
    _stream(monkeypatch, "unused")
    _drain(agent.run(actor=actor, conversation=conversation, question=question))
    return Message.objects.filter(conversation=conversation, role="assistant").last()


@override_settings(**AI_ON)
def test_answering_resumes_the_same_run_with_prior_results_intact(monkeypatch):
    actor = _actor()
    conversation = Conversation.objects.create(user=actor)
    parked_message = _park(monkeypatch, actor, conversation)
    run = AgentRun.objects.get(conversation=conversation)

    # A reload happens between parking and answering: the state must live in the DB, not in memory.
    parked_message = Message.objects.get(pk=parked_message.pk)

    seen = _capture_decisions(monkeypatch, [{"action": "answer", "why": "Have what I need",
                                             "intent": "lookup"}])
    _stream(monkeypatch, "Sales last month were 12,500.00 EGP.")
    events = _drain(agent.resume_clarify(actor=actor, conversation=conversation,
                                         source_message=parked_message, answer="Last month"))

    # Same run, no second row, and the answer landed as a gathered result the model can read.
    assert AgentRun.objects.filter(conversation=conversation).count() == 1
    run.refresh_from_db()
    assert run.status == AgentRun.Status.DONE
    assert run.parked == {}
    assert "sales_summary" in seen[0] and clarify.USER_ANSWER_TOOL in seen[0]
    assert "Last month" in seen[0]

    parked_message.refresh_from_db()
    assert parked_message.meta["clarify"]["status"] == "answered"
    assert parked_message.meta["clarify"]["answer"] == "Last month"
    # The pick is an honest user turn in the transcript, and the reply follows it.
    assert Message.objects.filter(conversation=conversation, role="user").last().content == "Last month"
    assert "".join(e.get("text", "") for e in events if e["type"] == "token").startswith("Sales last month")


@override_settings(**AI_ON)
def test_a_typed_answer_resumes_exactly_like_a_tapped_option(monkeypatch):
    actor = _actor()
    conversation = Conversation.objects.create(user=actor)
    parked_message = _park(monkeypatch, actor, conversation)

    seen = _capture_decisions(monkeypatch, [{"action": "answer", "why": "Done", "intent": "lookup"}])
    _stream(monkeypatch, "Here is the quarter.")
    _drain(agent.resume_clarify(actor=actor, conversation=conversation,
                                source_message=parked_message,
                                answer="Actually the whole quarter, please"))

    assert "whole quarter" in seen[0]
    AgentRun.objects.get(conversation=conversation, status=AgentRun.Status.DONE)


@override_settings(**AI_ON)
def test_the_resumed_run_never_re_runs_the_planner_or_the_earlier_steps(monkeypatch):
    actor = _actor()
    conversation = Conversation.objects.create(user=actor)
    parked_message = _park(monkeypatch, actor, conversation)

    calls: list[str] = []

    def fake_tool(actor_, decision, **_):
        calls.append(decision.get("tool"))
        return {"total": 1}, True

    monkeypatch.setattr(agent, "_run_tool", fake_tool)
    _decisions(monkeypatch, [{"action": "answer", "why": "Done", "intent": "lookup"}])
    _stream(monkeypatch, "Answer.")
    _drain(agent.resume_clarify(actor=actor, conversation=conversation,
                                source_message=parked_message, answer="Last month"))

    assert calls == []  # nothing already gathered is fetched twice


# --- the API: single-use, own-checked --------------------------------------------------------------

@override_settings(**AI_ON)
def test_answering_twice_is_a_conflict(monkeypatch):
    actor = _actor()
    conversation = Conversation.objects.create(user=actor)
    parked_message = _park(monkeypatch, actor, conversation)
    client = APIClient()
    client.force_authenticate(user=actor)

    _decisions(monkeypatch, [{"action": "answer", "why": "Done", "intent": "lookup"}])
    _stream(monkeypatch, "Answer.")
    first = client.post("/api/assistant/clarify/answer",
                        {"message_id": parked_message.pk, "answer": "Last month"}, format="json")
    assert first.status_code == 200, first.content[:500]
    b"".join(first.streaming_content)

    second = client.post("/api/assistant/clarify/answer",
                         {"message_id": parked_message.pk, "answer": "This month"}, format="json")
    assert second.status_code == 409


@override_settings(**AI_ON)
def test_an_empty_answer_is_refused(monkeypatch):
    actor = _actor()
    conversation = Conversation.objects.create(user=actor)
    parked_message = _park(monkeypatch, actor, conversation)
    client = APIClient()
    client.force_authenticate(user=actor)
    response = client.post("/api/assistant/clarify/answer",
                           {"message_id": parked_message.pk, "answer": "   "}, format="json")
    assert response.status_code == 400


@override_settings(**AI_ON)
def test_another_users_parked_question_is_a_404(monkeypatch):
    owner = _actor("clarify_owner")
    conversation = Conversation.objects.create(user=owner)
    parked_message = _park(monkeypatch, owner, conversation)
    client = APIClient()
    client.force_authenticate(user=_actor("clarify_stranger"))
    response = client.post("/api/assistant/clarify/answer",
                           {"message_id": parked_message.pk, "answer": "Last month"}, format="json")
    assert response.status_code == 404


# --- the mid-turn cost stop -------------------------------------------------------------------------

def _budget(scope: str, limit: int, action: str) -> None:
    """Budgets are one row per scope (unique), and an install may already carry one."""
    Budget.objects.update_or_create(scope=scope,
                                    defaults={"limit_microcents": limit, "action": action})


@override_settings(**AI_ON)
def test_a_turn_that_crosses_the_budget_stops_gathering_and_answers_calmly(monkeypatch):
    actor = _actor()
    conversation = Conversation.objects.create(user=actor)
    # A daily ceiling of 1 microcent: round 1 runs (the pre-call gate owns that decision), and the
    # boundary before round 2 is where this turn stops.
    _budget(Budget.Scope.USER, 1, Budget.Action.BLOCK)
    monkeypatch.setattr(agent.budgets, "estimate_cost_microcents", lambda *a, **k: 10_000)
    _decisions(monkeypatch, [
        _tool_decision("sales_summary", period="this_month"),
        _tool_decision("low_stock"),  # never reached — the boundary stops the turn first
    ])
    prompts = _capture_stream(monkeypatch, "Sales this month: 12,500.00 EGP.")

    events = _drain(agent.run(actor=actor, conversation=conversation, question="Sales and stock?"))

    done = [e for e in events if e["type"] == "done"][0]
    assert done["stop_reason"] == "budget"
    # The answer is real, from real gathered data, with an honest note — never an error screen.
    assert "spending limit" in prompts[0]
    assert "12,500.00 EGP" in "".join(e.get("text", "") for e in events if e["type"] == "token")
    message = Message.objects.filter(conversation=conversation, role="assistant").last()
    assert message.meta["stop_reason"] == "budget"


@override_settings(**AI_ON)
def test_a_turn_inside_its_budget_is_never_cut_short(monkeypatch):
    actor = _actor()
    conversation = Conversation.objects.create(user=actor)
    _budget(Budget.Scope.USER, 10_000_000, Budget.Action.BLOCK)
    _decisions(monkeypatch, [
        _tool_decision("sales_summary", period="this_month"),
        _tool_decision("low_stock"),
        {"action": "answer", "why": "Have both", "intent": "report"},
    ])
    _stream(monkeypatch, "Both figures.")
    events = _drain(agent.run(actor=actor, conversation=conversation, question="Sales and stock?"))
    assert [e for e in events if e["type"] == "done"][0]["stop_reason"] == "answered"


@override_settings(**AI_ON)
def test_a_notify_budget_only_logs_and_never_stops_the_turn(monkeypatch):
    actor = _actor()
    conversation = Conversation.objects.create(user=actor)
    _budget(Budget.Scope.ORG, 1, Budget.Action.NOTIFY)
    SpendRollup.objects.all().delete()
    monkeypatch.setattr(agent.budgets, "estimate_cost_microcents", lambda *a, **k: 10_000)
    _decisions(monkeypatch, [
        _tool_decision("sales_summary", period="this_month"),
        {"action": "answer", "why": "Done", "intent": "report"},
    ])
    _stream(monkeypatch, "Answer.")
    events = _drain(agent.run(actor=actor, conversation=conversation, question="Sales?"))
    assert [e for e in events if e["type"] == "done"][0]["stop_reason"] == "answered"


@override_settings(**AI_ON)
def test_the_per_call_request_ceiling_never_cuts_a_multi_round_turn(monkeypatch):
    """``request`` is a per-CALL ceiling the pre-call gate applies to every round — a turn whose
    rounds each fit inside it must run to its natural end, however many it takes."""
    actor = _actor()
    conversation = Conversation.objects.create(user=actor)
    _budget(Budget.Scope.REQUEST, 1, Budget.Action.BLOCK)
    monkeypatch.setattr(agent.budgets, "estimate_cost_microcents", lambda *a, **k: 10_000)
    _decisions(monkeypatch, [
        _tool_decision("sales_summary", period="this_month"),
        _tool_decision("low_stock"),
        {"action": "answer", "why": "Have both", "intent": "report"},
    ])
    _stream(monkeypatch, "Both figures.")
    events = _drain(agent.run(actor=actor, conversation=conversation, question="Sales and stock?"))
    assert [e for e in events if e["type"] == "done"][0]["stop_reason"] == "answered"


def test_check_round_degrades_to_keep_going_when_its_own_lookup_breaks(monkeypatch):
    from erp.assistant.gateway import budgets

    monkeypatch.setattr(budgets, "_check_round", lambda **_: (_ for _ in ()).throw(RuntimeError("db")))
    assert budgets.check_round(actor=None, spent_so_far=10**9) is False


# --- the prompt-rule eval cases ---------------------------------------------------------------------

CLARIFY_CASE_IDS = [
    "clarify_period_options_ar_01",
    "clarify_warehouse_options_en_02",
    "clarify_draft_status_options_ar_03",
    "clarify_open_customer_en_04",
    "clarify_never_asks_lookup_ar_05",
    "clarify_never_asks_lookup_en_06",
    "clarify_never_asks_default_en_07",
]


@pytest.mark.parametrize("case_id", CLARIFY_CASE_IDS)
@override_settings(**AI_ON)
def test_the_clarify_prompt_rule_cases_grade_as_written(case_id):
    """The T5.10 rule cases run end-to-end through the eval runner: three that must ask WITH
    options, one open question that must not offer any, and three the tools settle without asking
    anything at all."""
    from erp.assistant.evals import loader, runner

    case = next(c for c in loader.load_cases() if c["id"] == case_id)
    recording = runner.load_recording(case_id)
    assert recording is not None, f"missing recording for {case_id}"
    result = runner.run_case(case, recording)
    assert result["status"] == "pass", result["reason"]
