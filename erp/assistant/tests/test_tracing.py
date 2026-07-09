"""Tracing seam (ai-reliability T1.1/T1.2): every AI call self-reports to Trace/TraceStep
without changing behavior, and a tracing bug can never break the call it observes."""
from __future__ import annotations

import pytest
from django.test import override_settings

from erp.assistant import client
from erp.assistant.errors import (
    ActionFailedError,
    ActionForbiddenError,
    AssistantUnavailableError,
    classify_exception,
)
from erp.assistant.models import Conversation, Trace, TraceStep
from erp.assistant.services import agent, llm, tracing
from erp.identity.models import User

pytestmark = pytest.mark.django_db


def _user(username: str = "trace_user") -> User:
    return User.objects.create_user(username=username, password="Dev12345!",
                                    email=f"{username}@example.test")


# --- trace_call / TraceHandle -------------------------------------------------------------------

def test_trace_call_writes_exactly_one_trace_with_usage_and_cost():
    u = _user()
    assert Trace.objects.count() == 0
    with tracing.trace_call("ask", actor=u) as handle:
        handle.usage(provider="anthropic", model="claude-opus-4-8", input_tokens=100,
                     output_tokens=50)
    assert Trace.objects.count() == 1
    trace = Trace.objects.get()
    assert trace.feature == "ask"
    assert trace.actor_id == u.id
    assert trace.provider == "anthropic"
    assert trace.model == "claude-opus-4-8"
    assert trace.input_tokens == 100
    assert trace.output_tokens == 50
    assert trace.status == Trace.Status.OK
    in_price, out_price = tracing.PRICING["claude-opus-4-8"]
    expected_cost = round(100 * in_price / 1000 + 50 * out_price / 1000)
    assert trace.cost_microcents == expected_cost


def test_trace_call_records_error_and_reraises():
    with pytest.raises(RuntimeError):
        with tracing.trace_call("agent") as handle:
            handle.usage(provider="anthropic", model="claude-opus-4-8")
            raise RuntimeError("boom")
    trace = Trace.objects.get()
    assert trace.status == Trace.Status.ERROR
    assert trace.error_class == "unknown"
    assert trace.meta["raw_error_class"] == "RuntimeError"


def test_trace_call_records_steps():
    with tracing.trace_call("agent") as handle:
        handle.step(kind="llm", name="round1", ok=True, latency_ms=120)
        handle.step(kind="tool", name="inventory.stock_levels", ok=True, detail={"rows": 3})
    trace = Trace.objects.get()
    steps = list(TraceStep.objects.filter(trace=trace).order_by("seq"))
    assert [s.kind for s in steps] == ["llm", "tool"]
    assert steps[1].detail == {"rows": 3}


def test_unknown_model_costs_zero_and_flags_meta():
    with tracing.trace_call("ask") as handle:
        handle.usage(provider="anthropic", model="some-future-model", input_tokens=10,
                     output_tokens=10)
    trace = Trace.objects.get()
    assert trace.cost_microcents == 0
    assert trace.meta.get("cost_unknown") is True


def test_a_raising_tracer_write_does_not_break_the_call(monkeypatch):
    """If Trace.objects.create() itself blows up, the AI call still returns cleanly."""
    def boom(*_a, **_k):
        raise RuntimeError("db down")

    monkeypatch.setattr(Trace.objects, "create", boom)
    with tracing.trace_call("ask") as handle:
        handle.usage(provider="anthropic", model="claude-opus-4-8", input_tokens=1, output_tokens=1)
    assert Trace.objects.filter(feature="ask").count() == 0  # write failed, but no exception raised


def test_null_trace_is_inert():
    with tracing.null_trace() as handle:
        handle.usage(provider="anthropic", model="x")
        handle.step(kind="llm")
        handle.mark_ttft()
    assert Trace.objects.count() == 0


# --- error taxonomy (T1.9): classify_exception is a closed set, mapped at the seam ---------------

def test_classify_exception_covers_known_shapes():
    class RateLimitError(Exception):
        pass

    class APITimeoutError(Exception):
        pass

    class APIConnectionError(Exception):
        pass

    assert classify_exception(RateLimitError("429 too many requests")) == "rate_limited"
    assert classify_exception(APITimeoutError("timed out")) == "timeout"
    assert classify_exception(APIConnectionError("connection reset")) == "provider_error"
    assert classify_exception(GeneratorExit()) == "cancelled"
    assert classify_exception(ActionForbiddenError()) == "guardrail_blocked"
    assert classify_exception(ActionFailedError()) == "tool_error"
    assert classify_exception(AssistantUnavailableError()) == "provider_error"
    assert classify_exception(ValueError("bad json")) == "validation_failed"
    assert classify_exception(RuntimeError("boom")) == "unknown"
    assert classify_exception(
        Exception("maximum context length exceeded")
    ) == "context_overflow"


def test_trace_call_maps_taxonomy_to_status_and_keeps_raw_class_name():
    class RateLimitError(Exception):
        pass

    with pytest.raises(RateLimitError):
        with tracing.trace_call("ask") as handle:
            raise RateLimitError("429")
    trace = Trace.objects.get()
    assert trace.error_class == "rate_limited"
    assert trace.status == Trace.Status.ERROR  # no dedicated status for this bucket
    assert trace.meta["raw_error_class"] == "RateLimitError"


def test_trace_call_maps_timeout_to_timeout_status():
    class APITimeoutError(Exception):
        pass

    with pytest.raises(APITimeoutError):
        with tracing.trace_call("ask") as handle:
            raise APITimeoutError("timed out")
    trace = Trace.objects.get()
    assert trace.error_class == "timeout"
    assert trace.status == Trace.Status.TIMEOUT


def test_fail_from_exception_classifies_and_sets_status():
    with tracing.trace_call("embed") as handle:
        handle.fail_from_exception(ActionForbiddenError())
    trace = Trace.objects.get()
    assert trace.error_class == "guardrail_blocked"
    assert trace.status == Trace.Status.GUARDRAIL_BLOCKED


# --- complete_json feature wiring ----------------------------------------------------------------

@override_settings(ANTHROPIC_API_KEY="a", GEMINI_API_KEY="", GROQ_API_KEY="", MISTRAL_API_KEY="",
                   ASSISTANT_PROVIDER="")
def test_complete_json_traces_when_feature_given(monkeypatch):
    monkeypatch.setitem(llm._RUNNERS, "anthropic", lambda *_a, **_k: '{"ok": true}')
    u = _user("trace_json_user")
    result = llm.complete_json("sys", "user text", {}, feature="ask", actor=u, retries=1)
    assert result == {"ok": True}
    trace = Trace.objects.get()
    assert trace.feature == "ask"
    assert trace.actor_id == u.id
    assert trace.provider == "anthropic"
    assert trace.input_tokens > 0
    assert trace.output_tokens > 0
    assert trace.meta.get("tokens_estimated") is True


@override_settings(ANTHROPIC_API_KEY="a", GEMINI_API_KEY="", GROQ_API_KEY="", MISTRAL_API_KEY="",
                   ASSISTANT_PROVIDER="")
def test_complete_json_untraced_when_no_feature(monkeypatch):
    monkeypatch.setitem(llm._RUNNERS, "anthropic", lambda *_a, **_k: '{"ok": true}')
    assert llm.complete_json("sys", "user text", {}, retries=1) == {"ok": True}
    assert Trace.objects.count() == 0


@override_settings(ANTHROPIC_API_KEY="a", GEMINI_API_KEY="", GROQ_API_KEY="", MISTRAL_API_KEY="",
                   ASSISTANT_PROVIDER="")
def test_complete_json_traces_failure_when_every_provider_fails(monkeypatch):
    def down(*_a, **_k):
        raise RuntimeError("down")

    monkeypatch.setitem(llm._RUNNERS, "anthropic", down)
    from erp.assistant.errors import AssistantUnavailableError
    with pytest.raises(AssistantUnavailableError):
        llm.complete_json("sys", "user", {}, feature="ask", retries=1)
    trace = Trace.objects.get()
    assert trace.status == Trace.Status.ERROR


# --- complete_stream feature wiring: TTFT + estimated usage ---------------------------------------

@override_settings(ANTHROPIC_API_KEY="a", GEMINI_API_KEY="", GROQ_API_KEY="", MISTRAL_API_KEY="",
                   ASSISTANT_PROVIDER="")
def test_complete_stream_traces_ttft_and_estimated_usage(monkeypatch):
    def fake_stream(_messages, _system, _media, _prov):
        yield "hello "
        yield "world"

    monkeypatch.setitem(client._STREAM_RUNNERS, "anthropic", fake_stream)
    u = _user("trace_stream_user")
    chunks = list(client.complete_stream(
        [{"role": "user", "content": "hi"}], feature="chat", actor=u,
    ))
    assert chunks == ["hello ", "world"]
    trace = Trace.objects.get()
    assert trace.feature == "chat"
    assert trace.provider == "anthropic"
    assert "ttft_ms" in trace.meta
    assert trace.meta.get("tokens_estimated") is True
    assert trace.output_tokens > 0


@override_settings(ANTHROPIC_API_KEY="a", GEMINI_API_KEY="", GROQ_API_KEY="", MISTRAL_API_KEY="",
                   ASSISTANT_PROVIDER="")
def test_complete_stream_untraced_when_no_feature(monkeypatch):
    def fake_stream(_messages, _system, _media, _prov):
        yield "hi"

    monkeypatch.setitem(client._STREAM_RUNNERS, "anthropic", fake_stream)
    assert list(client.complete_stream([{"role": "user", "content": "hi"}])) == ["hi"]
    assert Trace.objects.count() == 0


# --- agent run tracing (T1.3): one Trace per run, steps for each planner round + tool call --------

def _agent_actor(username: str = "trace_agent_user") -> User:
    u = User.objects.create_user(username=username, password="Dev12345!",
                                 email=f"{username}@example.test")
    u.is_superuser = True
    u.save(update_fields=["is_superuser"])
    return u


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_agent_run_writes_one_trace_with_steps_for_two_tools(monkeypatch):
    user = _agent_actor()
    conv = Conversation.objects.create(user=user)
    decisions = iter([
        {"action": "tool", "tool": "sales_summary", "why": "Checking sales", "period": "this_month"},
        {"action": "tool", "tool": "low_stock", "why": "Checking stock", "limit": 5},
        {"action": "answer"},
    ])
    monkeypatch.setattr(agent, "complete_json", lambda *_a, **_k: next(decisions))
    monkeypatch.setattr(agent, "complete_stream", lambda *_a, **_k: iter(["All ", "good."]))

    events = list(agent.run(actor=user, conversation=conv, question="how did we do", page=None))

    assert events[-1]["type"] == "done"
    assert Trace.objects.filter(feature="agent").count() == 1
    trace = Trace.objects.get(feature="agent")
    assert trace.actor_id == user.id
    assert trace.conversation_id == conv.id
    assert trace.status == Trace.Status.OK
    assert trace.meta.get("stop") == "answered"
    assert "ttft_ms" in trace.meta

    steps = list(TraceStep.objects.filter(trace=trace).order_by("seq"))
    assert len(steps) >= 4
    assert [s.kind for s in steps] == ["llm", "tool", "llm", "tool", "llm", "llm"]
    tool_steps = [s for s in steps if s.kind == "tool"]
    assert [s.name for s in tool_steps] == ["sales_summary", "low_stock"]
    assert all(s.ok for s in tool_steps)
    # detail carries sizes, never the raw result rows.
    assert all(set(s.detail.keys()) <= {"result_size"} for s in tool_steps)


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_agent_run_at_round_cap_records_step_budget_stop(monkeypatch):
    user = _agent_actor()
    conv = Conversation.objects.create(user=user)
    monkeypatch.setattr(agent, "complete_json",
                        lambda *_a, **_k: {"action": "tool", "tool": "does_not_exist", "why": "x"})
    monkeypatch.setattr(agent, "complete_stream", lambda *_a, **_k: iter(["Done."]))

    list(agent.run(actor=user, conversation=conv, question="loop forever", page=None))

    trace = Trace.objects.get(feature="agent")
    assert trace.meta.get("stop") == "step_budget"


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_agent_run_traces_error_when_planner_raises(monkeypatch):
    user = _agent_actor()
    conv = Conversation.objects.create(user=user)

    def boom(*_a, **_k):
        raise RuntimeError("planner down")

    monkeypatch.setattr(agent, "complete_json", boom)

    with pytest.raises(RuntimeError):
        list(agent.run(actor=user, conversation=conv, question="anything", page=None))

    trace = Trace.objects.get(feature="agent")
    assert trace.status == Trace.Status.ERROR
    assert trace.error_class == "unknown"


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_agent_run_traces_cancelled_status_on_client_disconnect(monkeypatch):
    user = _agent_actor()
    conv = Conversation.objects.create(user=user)
    monkeypatch.setattr(agent, "complete_json", lambda *_a, **_k: {"action": "answer"})
    monkeypatch.setattr(agent, "complete_stream", lambda *_a, **_k: iter(["Some ", "answer"]))

    gen = agent.run(actor=user, conversation=conv, question="anything", page=None)
    next(gen)  # enter the generator so the trace_call context manager is live
    gen.close()  # simulates a client disconnect mid-stream (GeneratorExit)

    trace = Trace.objects.get(feature="agent")
    assert trace.status == Trace.Status.CANCELLED
    assert trace.error_class == "cancelled"
    assert trace.meta.get("stop") == "cancelled"
