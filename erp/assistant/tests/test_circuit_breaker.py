"""Gateway chain-walk integration with the circuit breaker (ai-reliability T2.3): a breaker-open
provider is skipped without being called; enough consecutive failures open it; a cooldown then a
success closes it again; an exhausted/all-open chain raises ``AllProvidersDown``; the trace records
which provider answered and which were skipped and why."""
from __future__ import annotations

import pytest
from django.test import override_settings

from erp.assistant.errors import AllProvidersDown, AssistantUnavailableError
from erp.assistant.gateway import breaker, core as llm
from erp.assistant.models import Trace
from erp.identity.models import User

pytestmark = pytest.mark.django_db


def _user(username: str = "breaker_user") -> User:
    return User.objects.create_user(username=username, password="Dev12345!",
                                    email=f"{username}@example.test")


@override_settings(ANTHROPIC_API_KEY="a", GEMINI_API_KEY="g", GROQ_API_KEY="", MISTRAL_API_KEY="",
                   ASSISTANT_PROVIDER="")
def test_open_breaker_is_skipped_without_calling_the_provider(monkeypatch):
    for _ in range(breaker.FAILURE_THRESHOLD):
        breaker.record_failure("anthropic")

    def must_not_be_called(*_a, **_k):
        raise AssertionError("a breaker-open provider must never be called")

    monkeypatch.setitem(llm._RUNNERS, "anthropic", must_not_be_called)
    monkeypatch.setitem(llm._RUNNERS, "gemini", lambda *_a, **_k: '{"ok": true}')

    result = llm.complete_json("sys", "user", {}, feature="ask", actor=_user())
    assert result == {"ok": True}

    trace = Trace.objects.get()
    routing = trace.meta["routing"]
    assert routing["chosen"] == "gemini"
    assert {"provider": "anthropic", "reason": "breaker_open"} in routing["skipped"]


@override_settings(ANTHROPIC_API_KEY="a", GEMINI_API_KEY="g", GROQ_API_KEY="", MISTRAL_API_KEY="",
                   ASSISTANT_PROVIDER="")
def test_consecutive_retryable_failures_open_the_breaker(monkeypatch):
    def down(*_a, **_k):
        raise RuntimeError("Error code: 503 - service unavailable")

    monkeypatch.setitem(llm._RUNNERS, "anthropic", down)
    monkeypatch.setitem(llm._RUNNERS, "gemini", lambda *_a, **_k: '{"ok": true}')

    for _ in range(breaker.FAILURE_THRESHOLD):
        assert llm.complete_json("sys", "user", {}, retries=1) == {"ok": True}

    assert breaker.state("anthropic") == "open"

    # a 6th call must not even try the now-open provider
    monkeypatch.setitem(llm._RUNNERS, "anthropic", lambda *_a, **_k: (_ for _ in ()).throw(
        AssertionError("must not call an open breaker")))
    assert llm.complete_json("sys", "user", {}, retries=1) == {"ok": True}


@override_settings(ANTHROPIC_API_KEY="a", GEMINI_API_KEY="g", GROQ_API_KEY="", MISTRAL_API_KEY="",
                   ASSISTANT_PROVIDER="")
def test_permanent_error_never_opens_the_breaker(monkeypatch):
    def unauthorized(*_a, **_k):
        raise RuntimeError("Error code: 401 - invalid api key")

    monkeypatch.setitem(llm._RUNNERS, "anthropic", unauthorized)
    monkeypatch.setitem(llm._RUNNERS, "gemini", lambda *_a, **_k: '{"ok": true}')

    for _ in range(breaker.FAILURE_THRESHOLD + 2):
        assert llm.complete_json("sys", "user", {}, retries=1) == {"ok": True}

    assert breaker.state("anthropic") == "closed"


@override_settings(ANTHROPIC_API_KEY="a", GEMINI_API_KEY="g", GROQ_API_KEY="", MISTRAL_API_KEY="",
                   ASSISTANT_PROVIDER="")
def test_half_open_probe_recovers_the_provider(monkeypatch):
    clock = {"t": 1_000.0}
    monkeypatch.setattr(breaker.time, "time", lambda: clock["t"])

    def down(*_a, **_k):
        raise RuntimeError("Error code: 503 - service unavailable")

    monkeypatch.setitem(llm._RUNNERS, "anthropic", down)
    monkeypatch.setitem(llm._RUNNERS, "gemini", lambda *_a, **_k: '{"ok": true}')
    for _ in range(breaker.FAILURE_THRESHOLD):
        llm.complete_json("sys", "user", {}, retries=1)
    assert breaker.state("anthropic") == "open"

    clock["t"] += breaker.COOLDOWN_S  # cooldown elapsed -> half-open, the probe is allowed through
    monkeypatch.setitem(llm._RUNNERS, "anthropic", lambda *_a, **_k: '{"recovered": true}')
    result = llm.complete_json("sys", "user", {}, feature="ask", actor=_user("breaker_probe"))
    assert result == {"recovered": True}
    assert breaker.state("anthropic") == "closed"

    trace = Trace.objects.get(feature="ask")
    assert trace.meta["routing"]["chosen"] == "anthropic"


@override_settings(ANTHROPIC_API_KEY="a", GEMINI_API_KEY="g", GROQ_API_KEY="", MISTRAL_API_KEY="",
                   ASSISTANT_PROVIDER="")
def test_all_providers_breaker_open_raises_without_calling_any_runner(monkeypatch):
    for prov in ("anthropic", "gemini"):
        for _ in range(breaker.FAILURE_THRESHOLD):
            breaker.record_failure(prov)

    def must_not_be_called(*_a, **_k):
        raise AssertionError("no provider should be called once every breaker is open")

    monkeypatch.setitem(llm._RUNNERS, "anthropic", must_not_be_called)
    monkeypatch.setitem(llm._RUNNERS, "gemini", must_not_be_called)

    with pytest.raises(AllProvidersDown):
        llm.complete_json("sys", "user", {}, feature="ask", actor=_user("breaker_all_open"))

    trace = Trace.objects.get()
    routing = trace.meta["routing"]
    assert routing["chosen"] is None
    assert {s["provider"] for s in routing["skipped"]} == {"anthropic", "gemini"}
    assert trace.error_class == "provider_error"


@override_settings(ANTHROPIC_API_KEY="a", GEMINI_API_KEY="g", GROQ_API_KEY="", MISTRAL_API_KEY="",
                   ASSISTANT_PROVIDER="")
def test_exhausted_chain_raises_all_providers_down_a_subclass_of_assistant_unavailable(monkeypatch):
    def down(*_a, **_k):
        raise RuntimeError("down")

    monkeypatch.setitem(llm._RUNNERS, "anthropic", down)
    monkeypatch.setitem(llm._RUNNERS, "gemini", down)
    with pytest.raises(AllProvidersDown):
        llm.complete_json("sys", "user", {}, retries=1)
    # existing callers that only know about AssistantUnavailableError still catch it
    with pytest.raises(AssistantUnavailableError):
        llm.complete_json("sys", "user", {}, retries=1)


# --- complete_stream: the breaker applies the same way -------------------------------------------

@override_settings(ANTHROPIC_API_KEY="a", GEMINI_API_KEY="g", GROQ_API_KEY="", MISTRAL_API_KEY="",
                   ASSISTANT_PROVIDER="")
def test_stream_open_breaker_is_skipped(monkeypatch):
    from erp.assistant import client

    for _ in range(breaker.FAILURE_THRESHOLD):
        breaker.record_failure("anthropic")

    def must_not_be_called(messages, system, media, prov, **_kw):
        raise AssertionError("a breaker-open provider must never be called")
        yield  # pragma: no cover - marks this a generator

    def good(messages, system, media, prov, **_kw):
        yield "hi"

    monkeypatch.setitem(client._STREAM_RUNNERS, "anthropic", must_not_be_called)
    monkeypatch.setitem(client._STREAM_RUNNERS, "gemini", good)
    out = list(llm.complete_stream([{"role": "user", "content": "x"}], feature="chat",
                                   actor=_user("breaker_stream")))
    assert "".join(out) == "hi"

    trace = Trace.objects.get()
    assert trace.meta["routing"]["chosen"] == "gemini"
