"""Provider failover routing (2026-07-08).

Every key that is set joins an automatic chain: the JSON/stream helpers try the preferred provider
first and fall to the next available one when it is down / rate-limited / returns garbage. These
tests exercise the chain ordering and the failover paths without any live call (the per-provider
runners are monkeypatched).
"""
from __future__ import annotations

import pytest
from django.test import override_settings

from erp.assistant import client
from erp.assistant.errors import AssistantUnavailableError
from erp.assistant.gateway import core as llm

pytestmark = pytest.mark.django_db


# --- chain construction ------------------------------------------------------------------------

@override_settings(ANTHROPIC_API_KEY="a", GEMINI_API_KEY="g", MISTRAL_API_KEY="m",
                   GROQ_API_KEY="q", ASSISTANT_PROVIDER="")
def test_chain_is_preference_order_of_available_keys():
    assert client.provider_chain() == ["anthropic", "gemini", "mistral", "groq"]
    assert client.provider() == "anthropic"


@override_settings(MISTRAL_API_KEY="m", ANTHROPIC_API_KEY="", GEMINI_API_KEY="", GROQ_API_KEY="",
                   ASSISTANT_PROVIDER="")
def test_only_available_keys_join_the_chain():
    assert client.provider_chain() == ["mistral"]
    assert client.provider() == "mistral"
    assert client.model_id() == "mistral-small-latest"


@override_settings(ANTHROPIC_API_KEY="a", MISTRAL_API_KEY="m", GEMINI_API_KEY="", GROQ_API_KEY="",
                   ASSISTANT_PROVIDER="mistral")
def test_configured_provider_jumps_to_the_front():
    assert client.provider_chain() == ["mistral", "anthropic"]
    assert client.provider() == "mistral"


@override_settings(ANTHROPIC_API_KEY="a", MISTRAL_API_KEY="m", GEMINI_API_KEY="", GROQ_API_KEY="",
                   ASSISTANT_PROVIDER="anthropic", ASSISTANT_MODEL="claude-custom")
def test_assistant_model_applies_only_to_the_primary():
    assert client.model_id("anthropic") == "claude-custom"      # primary honours ASSISTANT_MODEL
    assert client.model_id("mistral") == "mistral-small-latest"  # fallback keeps its own default


# --- JSON failover -----------------------------------------------------------------------------

@override_settings(ANTHROPIC_API_KEY="a", GEMINI_API_KEY="g", GROQ_API_KEY="", MISTRAL_API_KEY="",
                   ASSISTANT_PROVIDER="")
def test_complete_json_falls_over_to_the_next_provider(monkeypatch):
    def down(*_a, **_k):
        raise RuntimeError("provider down")

    def good(*_a, **_k):
        return '{"action": "answer"}'

    monkeypatch.setitem(llm._RUNNERS, "anthropic", down)
    monkeypatch.setitem(llm._RUNNERS, "gemini", good)
    # retries=1 so the primary fails fast into the fallback (no test sleep).
    assert llm.complete_json("sys", "user", {}, retries=1) == {"action": "answer"}


@override_settings(ANTHROPIC_API_KEY="a", GEMINI_API_KEY="g", GROQ_API_KEY="", MISTRAL_API_KEY="",
                   ASSISTANT_PROVIDER="")
def test_complete_json_skips_a_provider_that_returns_garbage(monkeypatch):
    monkeypatch.setitem(llm._RUNNERS, "anthropic", lambda *_a, **_k: "not json")
    monkeypatch.setitem(llm._RUNNERS, "gemini", lambda *_a, **_k: '{"ok": true}')
    assert llm.complete_json("sys", "user", {}, retries=1) == {"ok": True}


@override_settings(ANTHROPIC_API_KEY="a", GEMINI_API_KEY="g", GROQ_API_KEY="", MISTRAL_API_KEY="",
                   ASSISTANT_PROVIDER="")
def test_a_failing_non_terminal_provider_is_tried_once_then_handed_off(monkeypatch):
    """Fail fast while a fallback remains: a down primary must not burn its whole retry budget before
    failing over (the primary here would otherwise sleep 3x on every call)."""
    calls = {"anthropic": 0}

    def down(*_a, **_k):
        calls["anthropic"] += 1
        raise RuntimeError("down")

    monkeypatch.setitem(llm._RUNNERS, "anthropic", down)
    monkeypatch.setitem(llm._RUNNERS, "gemini", lambda *_a, **_k: '{"ok": true}')
    assert llm.complete_json("s", "u", {}, retries=3) == {"ok": True}
    assert calls["anthropic"] == 1  # one attempt, then straight to the fallback


@override_settings(ANTHROPIC_API_KEY="a", GEMINI_API_KEY="g", GROQ_API_KEY="", MISTRAL_API_KEY="",
                   ASSISTANT_PROVIDER="")
def test_complete_json_raises_when_every_provider_fails(monkeypatch):
    def down(*_a, **_k):
        raise RuntimeError("down")

    monkeypatch.setitem(llm._RUNNERS, "anthropic", down)
    monkeypatch.setitem(llm._RUNNERS, "gemini", down)
    with pytest.raises(AssistantUnavailableError):
        llm.complete_json("sys", "user", {}, retries=1)


# --- stream failover ---------------------------------------------------------------------------

@override_settings(ANTHROPIC_API_KEY="a", GEMINI_API_KEY="g", GROQ_API_KEY="", MISTRAL_API_KEY="",
                   ASSISTANT_PROVIDER="")
def test_complete_stream_falls_over_before_the_first_token(monkeypatch):
    def down(messages, system, media, prov, **_kw):
        raise RuntimeError("down")
        yield  # pragma: no cover - marks this a generator

    def good(messages, system, media, prov, **_kw):
        yield "hi"
        yield " there"

    monkeypatch.setitem(client._STREAM_RUNNERS, "anthropic", down)
    monkeypatch.setitem(client._STREAM_RUNNERS, "gemini", good)
    out = list(llm.complete_stream([{"role": "user", "content": "x"}]))
    assert "".join(out) == "hi there"


# --- the Mistral runner ------------------------------------------------------------------------

@override_settings(MISTRAL_API_KEY="m", ANTHROPIC_API_KEY="", GEMINI_API_KEY="", GROQ_API_KEY="",
                   ASSISTANT_PROVIDER="")
def test_mistral_runner_parses_an_openai_shaped_body(monkeypatch):
    captured: dict = {}

    def fake_chat(messages, *, model, max_tokens, json_mode=True, timeout=60.0):
        captured["model"] = model
        return {"choices": [{"message": {"content": '{"action": "answer"}'}}]}

    monkeypatch.setattr(llm, "mistral_chat", fake_chat)
    assert llm.complete_json("sys", "user", {}, retries=1) == {"action": "answer"}
    assert captured["model"] == "mistral-small-latest"
