"""Semantic cache for knowledge Q&A (ai-reliability T2.8): a near-duplicate question reuses a
verified knowledge answer instead of re-running the router + answer model. Scoped per user,
invalidated by a knowledge-version bump, bypassed cleanly by the kill switch."""
from __future__ import annotations

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from erp.assistant.gateway import cache
from erp.assistant.models import SemanticCache
from erp.assistant.services import ask, knowledge
from erp.identity.models import User

pytestmark = pytest.mark.django_db

ASK_URL = "/api/assistant/ask"
PROVIDER_SETTINGS = dict(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")

VEC_A = [1.0, 0.0]
VEC_A_PARAPHRASE = [0.999, 0.0447]  # cosine ≈ 0.999 vs VEC_A — clears the 0.95 threshold
VEC_B = [0.0, 1.0]  # orthogonal — cosine 0.0, well under threshold


def _user(username: str) -> User:
    return User.objects.create_user(username=username, password="Dev12345!",
                                    email=f"{username}@example.test")


def _client(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _route_and_answer(monkeypatch, calls: list, *, answer: str = "Return within 14 days."):
    """complete_json returns (route → search_documents, then answer) on each fresh call; a cache
    hit never reaches this fake, so ``calls`` only grows on an actual model round-trip."""

    def fake(system, user, schema, **_):
        calls.append(user)
        if len(calls) % 2 == 1:
            return {"tool": "search_documents", "period": None, "query": "return policy",
                    "limit": None}
        return {"answer": answer}

    monkeypatch.setattr(ask, "complete_json", fake)


def _embed(monkeypatch, vector_by_question: dict[str, list[float]]):
    def fake(text, *_a, **_k):
        return vector_by_question.get(text)

    monkeypatch.setattr(ask.client, "embed_text", fake)


@override_settings(**PROVIDER_SETTINGS)
def test_paraphrase_within_threshold_hits_cache(monkeypatch):
    user = _user("sem_hit")
    calls: list = []
    _route_and_answer(monkeypatch, calls)
    _embed(monkeypatch, {"what is the return policy?": VEC_A,
                         "what's the return policy?": VEC_A_PARAPHRASE})

    c = _client(user)
    first = c.post(ASK_URL, {"question": "what is the return policy?"}, format="json").json()["data"]
    assert first["from_cache"] is False
    assert len(calls) == 2  # one route call + one answer call

    second = c.post(ASK_URL, {"question": "what's the return policy?"}, format="json").json()["data"]
    assert second["from_cache"] is True
    assert second["answer"] == first["answer"]
    assert second["citations"] == first["citations"]
    assert len(calls) == 2  # the cache hit never touched the model
    assert SemanticCache.objects.filter(user=user).count() == 1


@override_settings(**PROVIDER_SETTINGS)
def test_other_user_never_hits(monkeypatch):
    owner, other = _user("sem_owner"), _user("sem_other")
    calls: list = []
    _route_and_answer(monkeypatch, calls)
    _embed(monkeypatch, {"what is the return policy?": VEC_A})

    _client(owner).post(ASK_URL, {"question": "what is the return policy?"}, format="json")
    assert len(calls) == 2

    resp = _client(other).post(ASK_URL, {"question": "what is the return policy?"}, format="json")
    assert resp.json()["data"]["from_cache"] is False
    assert len(calls) == 4  # the second user re-paid — no row leaked across users


@override_settings(**PROVIDER_SETTINGS)
def test_ingestion_bump_invalidates(monkeypatch):
    user = _user("sem_bump")
    calls: list = []
    _route_and_answer(monkeypatch, calls)
    _embed(monkeypatch, {"what is the return policy?": VEC_A})

    c = _client(user)
    c.post(ASK_URL, {"question": "what is the return policy?"}, format="json")
    assert len(calls) == 2

    knowledge.ingest_document(
        data=b"Updated policy text.", media_type="text/plain",
        filename="policy.txt", title="Policy", actor=user,
    )

    c.post(ASK_URL, {"question": "what is the return policy?"}, format="json")
    assert len(calls) == 4  # the bump made the cached row invisible — re-ran and re-cached


@override_settings(**PROVIDER_SETTINGS, ASSISTANT_SEMANTIC_CACHE=False)
def test_kill_switch_bypasses(monkeypatch):
    user = _user("sem_off")
    calls: list = []
    _route_and_answer(monkeypatch, calls)
    _embed(monkeypatch, {"what is the return policy?": VEC_A})

    c = _client(user)
    c.post(ASK_URL, {"question": "what is the return policy?"}, format="json")
    c.post(ASK_URL, {"question": "what is the return policy?"}, format="json")

    assert len(calls) == 4  # never looked up, never stored
    assert SemanticCache.objects.count() == 0


@override_settings(**PROVIDER_SETTINGS)
def test_non_knowledge_answers_are_never_cached(monkeypatch):
    """Only ``search_documents`` answers are safe to reuse blind of tool args — a sales_summary
    answer depends on the period/filters the router chose, so it must never be semantic-cached."""
    user = _user("sem_sales")
    calls: list = []

    def fake(system, u, schema, **_):
        calls.append(u)
        if len(calls) % 2 == 1:
            return {"tool": "sales_summary", "period": "this_month", "query": None, "limit": None}
        return {"answer": "No sales yet."}

    monkeypatch.setattr(ask, "complete_json", fake)
    _embed(monkeypatch, {"how are sales?": VEC_A})

    _client(user).post(ASK_URL, {"question": "how are sales?"}, format="json")
    assert SemanticCache.objects.count() == 0


def test_semantic_lookup_below_threshold_misses():
    user = _user("sem_thresh")
    cache.semantic_put(user, question_text="q", embedding=VEC_A, answer="a", citations=[])
    assert cache.semantic_lookup(user, VEC_B) is None
    assert cache.semantic_lookup(user, VEC_A) == {"answer": "a", "citations": []}


def test_semantic_put_evicts_oldest_beyond_cap():
    user = _user("sem_cap")
    with override_settings(ASSISTANT_SEMANTIC_CACHE_CAP=3):
        for i in range(5):
            cache.semantic_put(user, question_text=f"q{i}", embedding=[1.0, float(i)],
                               answer=f"a{i}", citations=[])
    rows = list(SemanticCache.objects.filter(user=user).order_by("question_text"))
    assert [r.question_text for r in rows] == ["q2", "q3", "q4"]  # oldest two evicted
