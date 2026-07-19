"""Retry policy (ai-reliability T2.2): transient provider errors retry with backoff; permanent
ones fail fast and typed; every retry is visible in the trace; a timeout classifies as such."""
from __future__ import annotations

import pytest
from django.test import override_settings

from erp.assistant.errors import AssistantUnavailableError
from erp.assistant.gateway import core as llm
from erp.assistant.gateway import retry
from erp.assistant.models import Trace, TraceStep
from erp.identity.models import User

pytestmark = pytest.mark.django_db


def _user(username: str = "retry_user") -> User:
    return User.objects.create_user(username=username, password="Dev12345!",
                                    email=f"{username}@example.test")


# --- retry.is_retryable() classification table ---------------------------------------------------

@pytest.mark.parametrize("message", [
    "Error code: 429 - rate limit exceeded",
    "InternalServerError: 500",
    "ServiceUnavailableError: 503",
    "Connection reset by peer",
    "Request timed out",
])
def test_is_retryable_transient_markers(message):
    assert retry.is_retryable(RuntimeError(message)) is True


@pytest.mark.parametrize("message", [
    "Error code: 401 - invalid api key",
    "AuthenticationError: invalid_api_key",
    "PermissionDeniedError: 403 forbidden",
    "BadRequestError: 400 schema mismatch",
    "content_policy violation",
])
def test_is_retryable_permanent_markers(message):
    assert retry.is_retryable(RuntimeError(message)) is False


def test_is_retryable_unrecognized_fails_fast():
    assert retry.is_retryable(RuntimeError("something weird happened")) is False


def test_backoff_seconds_within_jittered_bounds():
    for attempt, ceiling in enumerate([0.5, 1.0, 2.0, 4.0, 4.0]):
        for _ in range(20):
            assert 0 <= retry.backoff_seconds(attempt) <= ceiling


# --- complete_json integration: retry vs fail-fast, trace visibility, timeout classification ------

@override_settings(ANTHROPIC_API_KEY="a", GEMINI_API_KEY="", GROQ_API_KEY="", MISTRAL_API_KEY="",
                   ASSISTANT_PROVIDER="")
def test_429_is_retried_then_succeeds(monkeypatch):
    monkeypatch.setattr(llm.time, "sleep", lambda *_a, **_k: None)
    calls = {"n": 0}

    def flaky(*_a, **_k):
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("Error code: 429 - rate limited")
        return '{"ok": true}'

    monkeypatch.setitem(llm._RUNNERS, "anthropic", flaky)
    result = llm.complete_json("sys", "user", {}, feature="ask", actor=_user())
    assert result == {"ok": True}
    assert calls["n"] == 3  # 2 failed attempts + the one that succeeds

    trace = Trace.objects.get()
    steps = list(TraceStep.objects.filter(trace=trace).order_by("seq"))
    assert [s.detail.get("retry") for s in steps] == [1, 2]
    assert all(s.kind == "llm" and s.ok is False for s in steps)
    assert trace.status == Trace.Status.OK


@override_settings(ANTHROPIC_API_KEY="a", GEMINI_API_KEY="", GROQ_API_KEY="", MISTRAL_API_KEY="",
                   ASSISTANT_PROVIDER="")
def test_401_fails_immediately_without_retry(monkeypatch):
    def must_not_sleep(*_a, **_k):
        raise AssertionError("must not sleep/retry on a permanent error")

    monkeypatch.setattr(llm.time, "sleep", must_not_sleep)
    calls = {"n": 0}

    def unauthorized(*_a, **_k):
        calls["n"] += 1
        raise RuntimeError("Error code: 401 - invalid api key")

    monkeypatch.setitem(llm._RUNNERS, "anthropic", unauthorized)
    with pytest.raises(AssistantUnavailableError):
        llm.complete_json("sys", "user", {}, feature="ask", actor=_user("retry_401"))
    assert calls["n"] == 1  # one attempt only — no retry budget spent on a permanent error

    trace = Trace.objects.get()
    step = TraceStep.objects.get(trace=trace)
    assert step.detail.get("final") is True
    assert "retry" not in step.detail


@override_settings(ANTHROPIC_API_KEY="a", GEMINI_API_KEY="", GROQ_API_KEY="", MISTRAL_API_KEY="",
                   ASSISTANT_PROVIDER="")
def test_timeout_maps_to_timeout_error_class(monkeypatch):
    monkeypatch.setattr(llm.time, "sleep", lambda *_a, **_k: None)

    def always_times_out(*_a, **_k):
        raise TimeoutError("Request timed out")

    monkeypatch.setitem(llm._RUNNERS, "anthropic", always_times_out)
    with pytest.raises(AssistantUnavailableError):
        llm.complete_json("sys", "user", {}, feature="ask", actor=_user("retry_timeout"))

    trace = Trace.objects.get()
    assert trace.error_class == "timeout"
    assert trace.status == Trace.Status.TIMEOUT


# --- complete_stream: same retry/backoff budget before the first token ----------------------------

@override_settings(ANTHROPIC_API_KEY="a", GEMINI_API_KEY="", GROQ_API_KEY="", MISTRAL_API_KEY="",
                   ASSISTANT_PROVIDER="")
def test_stream_429_before_first_token_is_retried_then_succeeds(monkeypatch):
    from erp.assistant import client

    monkeypatch.setattr(llm.time, "sleep", lambda *_a, **_k: None)
    calls = {"n": 0}

    def flaky(*_a, **_k):
        calls["n"] += 1
        if calls["n"] < 2:
            raise RuntimeError("Error code: 429 - rate limited")
        yield "hi"

    monkeypatch.setitem(client._STREAM_RUNNERS, "anthropic", flaky)
    out = list(llm.complete_stream([{"role": "user", "content": "x"}], feature="chat",
                                   actor=_user("retry_stream")))
    assert "".join(out) == "hi"
    assert calls["n"] == 2

    trace = Trace.objects.get()
    steps = list(TraceStep.objects.filter(trace=trace).order_by("seq"))
    assert [s.detail.get("retry") for s in steps] == [1]
