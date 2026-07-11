"""Streaming resilience (ai-reliability T2.6): a mid-stream provider failure restarts the turn on
the next chain model with the partial folded in — the user never loses the turn."""
from __future__ import annotations

import pytest
from django.test import override_settings

from erp.assistant import client
from erp.assistant.errors import AssistantUnavailableError
from erp.assistant.gateway import core as llm
from erp.assistant.models import Trace, TraceStep
from erp.identity.models import User

pytestmark = pytest.mark.django_db

PROVIDER_SETTINGS = dict(ANTHROPIC_API_KEY="a", GEMINI_API_KEY="g", GROQ_API_KEY="",
                         MISTRAL_API_KEY="", ASSISTANT_PROVIDER="")


def _user(username: str = "stream_user") -> User:
    return User.objects.create_user(username=username, password="Dev12345!",
                                    email=f"{username}@example.test")


@override_settings(**PROVIDER_SETTINGS)
def test_mid_stream_failure_recovers_on_next_provider(monkeypatch):
    monkeypatch.setattr(llm.time, "sleep", lambda *_a, **_k: None)
    captured: dict = {}

    def anthropic_stream(*_a, **_k):
        yield "Hello "
        raise RuntimeError("Error code: 500 - internal server error")

    def gemini_stream(messages, *_a, **_k):
        captured["messages"] = messages
        yield "world."

    monkeypatch.setitem(client._STREAM_RUNNERS, "anthropic", anthropic_stream)
    monkeypatch.setitem(client._STREAM_RUNNERS, "gemini", gemini_stream)

    retries: list[int] = []
    out = list(llm.complete_stream(
        [{"role": "user", "content": "hi"}], feature="chat", actor=_user(),
        on_retry=lambda: retries.append(1),
    ))

    assert "".join(out) == "Hello world."
    assert len(retries) == 1

    # The continuation carries the partial as an assistant turn plus a continue instruction —
    # the question is never re-asked and the partial is never repeated.
    msgs = captured["messages"]
    assert msgs[0] == {"role": "user", "content": "hi"}
    assert msgs[1] == {"role": "assistant", "content": "Hello "}
    assert msgs[-1]["role"] == "user" and "continue" in msgs[-1]["content"].lower()

    trace = Trace.objects.get()
    assert trace.status == Trace.Status.OK
    assert trace.meta.get("stream_recovered") is True
    steps = list(TraceStep.objects.filter(trace=trace).order_by("seq"))
    mid_stream_steps = [s for s in steps if s.detail.get("mid_stream")]
    recovered_steps = [s for s in steps if s.detail.get("recovered")]
    assert len(mid_stream_steps) == 1 and mid_stream_steps[0].name == "anthropic"
    assert len(recovered_steps) == 1 and recovered_steps[0].name == "gemini"


@override_settings(**PROVIDER_SETTINGS)
def test_mid_stream_failure_without_on_retry_still_recovers(monkeypatch):
    monkeypatch.setattr(llm.time, "sleep", lambda *_a, **_k: None)

    def anthropic_stream(*_a, **_k):
        yield "Partial. "
        raise RuntimeError("Error code: 503")

    def gemini_stream(*_a, **_k):
        yield "Rest."

    monkeypatch.setitem(client._STREAM_RUNNERS, "anthropic", anthropic_stream)
    monkeypatch.setitem(client._STREAM_RUNNERS, "gemini", gemini_stream)

    out = list(llm.complete_stream([{"role": "user", "content": "hi"}], feature="chat",
                                   actor=_user("no_callback")))
    assert "".join(out) == "Partial. Rest."


@override_settings(**PROVIDER_SETTINGS)
def test_on_retry_exception_is_swallowed(monkeypatch):
    monkeypatch.setattr(llm.time, "sleep", lambda *_a, **_k: None)

    def anthropic_stream(*_a, **_k):
        yield "A"
        raise RuntimeError("Error code: 500")

    def gemini_stream(*_a, **_k):
        yield "B"

    monkeypatch.setitem(client._STREAM_RUNNERS, "anthropic", anthropic_stream)
    monkeypatch.setitem(client._STREAM_RUNNERS, "gemini", gemini_stream)

    def _boom():
        raise ValueError("callback broke")

    out = list(llm.complete_stream([{"role": "user", "content": "hi"}], feature="chat",
                                   actor=_user("callback_broke"), on_retry=_boom))
    assert "".join(out) == "AB"


@override_settings(**PROVIDER_SETTINGS)
def test_mid_stream_failure_exhausts_chain_raises_with_partial_already_yielded(monkeypatch):
    monkeypatch.setattr(llm.time, "sleep", lambda *_a, **_k: None)

    def anthropic_stream(*_a, **_k):
        yield "Hello "
        raise RuntimeError("Error code: 500")

    def gemini_stream(*_a, **_k):
        yield "world"
        raise RuntimeError("Error code: 500")

    monkeypatch.setitem(client._STREAM_RUNNERS, "anthropic", anthropic_stream)
    monkeypatch.setitem(client._STREAM_RUNNERS, "gemini", gemini_stream)

    collected: list[str] = []
    with pytest.raises(AssistantUnavailableError):
        for chunk in llm.complete_stream([{"role": "user", "content": "hi"}], feature="chat",
                                         actor=_user("exhaust")):
            collected.append(chunk)

    # The partial from both providers already reached the caller before the final raise.
    assert "".join(collected) == "Hello world"
    trace = Trace.objects.get()
    assert trace.status == Trace.Status.ERROR
    assert trace.meta.get("stream_recovered") is True
