"""Integration: knowledge.search() wiring to the T3.5 rerank stage — the fused candidates it hands
rerank, and that a disabled flag never loads more chunks than `limit` (byte-identical to pre-T3.5
behavior, see knowledge.search's fuse_depth comment)."""
from __future__ import annotations

import pytest

from erp.assistant.services import knowledge
from erp.identity.models import User

pytestmark = pytest.mark.django_db


def _admin(username: str) -> User:
    u = User.objects.create_user(username=username, password="Dev12345!",
                                 email=f"{username}@example.test")
    u.is_superuser = True
    u.save(update_fields=["is_superuser"])
    return u


def _ingest_many(n: int, actor) -> None:
    for i in range(n):
        knowledge.ingest_document(
            data=f"Warranty policy document number {i}: coverage terms apply.".encode("utf-8"),
            media_type="text/plain", filename=f"warranty{i}.txt", title=f"Warranty {i}", actor=actor,
        )


def test_search_calls_maybe_rerank_with_fused_candidates_and_limit(monkeypatch):
    actor = _admin("rerank_wire")
    _ingest_many(5, actor)
    monkeypatch.setattr(knowledge.client, "embed_text", lambda *_a, **_k: None)

    captured = {}

    def spy(query, rows, *, top_k, trace=None):
        captured["query"] = query
        captured["rows"] = rows
        captured["top_k"] = top_k
        return list(reversed(rows))[:top_k]

    monkeypatch.setattr(knowledge.rerank, "maybe_rerank", spy)
    result = knowledge.search("warranty policy", limit=3)

    assert captured["query"] == "warranty policy"
    assert captured["top_k"] == 3
    assert result == list(reversed(captured["rows"]))[:3]


def test_search_loads_only_limit_chunks_when_rerank_disabled(monkeypatch, settings):
    settings.ASSISTANT_RERANK = False
    actor = _admin("rerank_disabled")
    _ingest_many(5, actor)
    monkeypatch.setattr(knowledge.client, "embed_text", lambda *_a, **_k: None)

    seen_depths = []
    real_load = knowledge._load_chunks

    def spy_load(ids, fts_candidates):
        seen_depths.append(len(ids))
        return real_load(ids, fts_candidates)

    monkeypatch.setattr(knowledge, "_load_chunks", spy_load)
    knowledge.search("warranty policy", limit=2)

    assert seen_depths == [2]  # never widened past `limit` when the flag is off


def test_search_loads_full_fuse_depth_when_rerank_enabled(monkeypatch, settings):
    settings.ASSISTANT_RERANK = True
    actor = _admin("rerank_enabled")
    _ingest_many(5, actor)
    monkeypatch.setattr(knowledge.client, "embed_text", lambda *_a, **_k: None)
    # Keep this test about candidate depth, not the model call — a trivial pass-through rerank.
    monkeypatch.setattr(knowledge.rerank, "maybe_rerank", lambda query, rows, *, top_k, trace=None: rows[:top_k])

    seen_depths = []
    real_load = knowledge._load_chunks

    def spy_load(ids, fts_candidates):
        seen_depths.append(len(ids))
        return real_load(ids, fts_candidates)

    monkeypatch.setattr(knowledge, "_load_chunks", spy_load)
    knowledge.search("warranty policy", limit=2)

    assert seen_depths == [5]  # all 5 fused candidates loaded, not just the requested limit of 2
