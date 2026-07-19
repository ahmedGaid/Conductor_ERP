"""Exact-match response cache (ai-reliability T2.5): identical input pays once; TTL and version
bumps invalidate; denied task classes never cache; hits show cost 0 in traces and a hit rate in
the ops summary."""
from __future__ import annotations

from datetime import timedelta

import pytest
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from erp.assistant.gateway import cache
from erp.assistant.gateway import core as llm
from erp.assistant.models import ResponseCache, Trace, TraceStep
from erp.identity.models import User

pytestmark = pytest.mark.django_db

PROVIDER_SETTINGS = dict(ANTHROPIC_API_KEY="a", GEMINI_API_KEY="", GROQ_API_KEY="",
                         MISTRAL_API_KEY="", ASSISTANT_PROVIDER="")


def _user(username: str = "cache_user") -> User:
    return User.objects.create_user(username=username, password="Dev12345!",
                                    email=f"{username}@example.test")


def _counting_runner(monkeypatch, response: str = '{"ok": true}') -> dict:
    calls = {"n": 0}

    def runner(*_a, **_k):
        calls["n"] += 1
        return response

    monkeypatch.setitem(llm._RUNNERS, "anthropic", runner)
    return calls


# --- hit path: same input pays once, hit is visible at cost 0 -------------------------------------

@override_settings(**PROVIDER_SETTINGS)
def test_same_input_twice_calls_provider_once(monkeypatch):
    calls = _counting_runner(monkeypatch)
    actor = _user()

    first = llm.complete_json("sys", "user", {}, feature="digest", actor=actor)
    second = llm.complete_json("sys", "user", {}, feature="digest", actor=actor)

    assert first == second == {"ok": True}
    assert calls["n"] == 1

    row = ResponseCache.objects.get()
    assert row.task == "digest"
    assert row.hit_count == 1

    hit_trace = Trace.objects.order_by("created_at").last()
    assert hit_trace.provider == "cache"
    assert hit_trace.cost_microcents == 0
    assert hit_trace.input_tokens == 0 and hit_trace.output_tokens == 0
    step = TraceStep.objects.get(trace=hit_trace)
    assert step.kind == "llm" and step.detail == {"cache": "exact"}


@override_settings(**PROVIDER_SETTINGS)
def test_different_input_misses(monkeypatch):
    calls = _counting_runner(monkeypatch)
    actor = _user("cache_miss")

    llm.complete_json("sys", "user A", {}, feature="digest", actor=actor)
    llm.complete_json("sys", "user B", {}, feature="digest", actor=actor)

    assert calls["n"] == 2
    assert ResponseCache.objects.count() == 2


def test_make_key_changes_with_media_bytes():
    base = dict(task="digest", prompt_ref="p", model="m", system="s", user="u", schema={})
    key_a = cache.make_key(media=[{"media_type": "image/png", "data": b"aa"}], **base)
    key_b = cache.make_key(media=[{"media_type": "image/png", "data": b"bb"}], **base)
    assert key_a != key_b


# --- invalidation: TTL + explicit version bump ----------------------------------------------------

@override_settings(**PROVIDER_SETTINGS)
def test_ttl_expiry_recomputes(monkeypatch):
    calls = _counting_runner(monkeypatch)
    actor = _user("cache_ttl")

    llm.complete_json("sys", "user", {}, feature="digest", actor=actor)
    ResponseCache.objects.update(created_at=timezone.now() - timedelta(hours=21))  # digest TTL 20h

    llm.complete_json("sys", "user", {}, feature="digest", actor=actor)
    assert calls["n"] == 2
    # The recompute refreshed the row: TTL counts from the new write, hits reset.
    row = ResponseCache.objects.get()
    assert row.created_at > timezone.now() - timedelta(minutes=1)
    assert row.hit_count == 0


@override_settings(**PROVIDER_SETTINGS)
def test_bump_invalidates_then_recaches(monkeypatch):
    calls = _counting_runner(monkeypatch)
    actor = _user("cache_bump")

    llm.complete_json("sys", "user", {}, feature="digest", actor=actor)
    cache.bump("digest")
    llm.complete_json("sys", "user", {}, feature="digest", actor=actor)
    assert calls["n"] == 2  # the bump made the first row invisible

    llm.complete_json("sys", "user", {}, feature="digest", actor=actor)
    assert calls["n"] == 2  # re-cached at the new version — third call is a hit again
    assert ResponseCache.objects.get().input_version == 1


# --- denied / disabled task classes ---------------------------------------------------------------

@override_settings(**PROVIDER_SETTINGS, ASSISTANT_CACHE_TASKS={"extract"})
def test_hard_denied_task_never_caches_even_if_allowlisted(monkeypatch):
    calls = _counting_runner(monkeypatch)
    actor = _user("cache_extract")

    llm.complete_json("sys", "user", {}, feature="extract", actor=actor)
    llm.complete_json("sys", "user", {}, feature="extract", actor=actor)

    assert calls["n"] == 2
    assert ResponseCache.objects.count() == 0


@override_settings(**PROVIDER_SETTINGS)
def test_unlisted_task_not_cached(monkeypatch):
    calls = _counting_runner(monkeypatch)
    actor = _user("cache_eval")

    llm.complete_json("sys", "user", {}, feature="eval", actor=actor)
    llm.complete_json("sys", "user", {}, feature="eval", actor=actor)

    assert calls["n"] == 2
    assert ResponseCache.objects.count() == 0


@override_settings(**PROVIDER_SETTINGS)
def test_untraced_call_not_cached(monkeypatch):
    calls = _counting_runner(monkeypatch)

    llm.complete_json("sys", "user", {})
    llm.complete_json("sys", "user", {})

    assert calls["n"] == 2
    assert ResponseCache.objects.count() == 0


# --- ops visibility --------------------------------------------------------------------------------

@override_settings(**PROVIDER_SETTINGS)
def test_ops_summary_exposes_hit_rate(monkeypatch):
    _counting_runner(monkeypatch)
    actor = _user("cache_ops")
    llm.complete_json("sys", "user", {}, feature="digest", actor=actor)  # miss
    llm.complete_json("sys", "user", {}, feature="digest", actor=actor)  # hit

    admin = User.objects.create_user(username="cache_ops_admin", password="Dev12345!",
                                     email="cache_ops_admin@example.test", is_superuser=True)
    client = APIClient()
    client.force_authenticate(user=admin)
    data = client.get("/api/assistant/ops/summary").json()["data"]
    assert data["cache"] == {"lookups": 2, "hits": 1, "hit_rate": pytest.approx(0.5)}
