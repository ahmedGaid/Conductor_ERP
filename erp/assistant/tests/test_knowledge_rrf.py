"""ai-reliability T3.2 — hybrid retrieval by Reciprocal Rank Fusion.

Pure ``_rrf_fuse`` math (no DB, runs everywhere) plus DB-level checks that ``search`` carries
per-hit arm provenance and records a ``kind="retrieval"`` trace step.
"""
from __future__ import annotations

import pytest

from erp.assistant.services import knowledge
from erp.assistant.services.knowledge import RRF_K
from erp.assistant.services.tracing import TraceHandle
from erp.identity.models import User


# --- pure RRF math (no DB) ---------------------------------------------------------------------

def _rrf(a: float) -> float:
    return 1.0 / (RRF_K + a)


def test_rrf_fuses_and_reorders_by_combined_rank():
    # 30 is FTS-last but vector-first; 10 is FTS-first but vector-last → they tie on fused score,
    # and the semantic (vector, listed last) arm breaks the tie for 30. 20 is middle in both.
    fused = knowledge._rrf_fuse({"fts": [10, 20, 30], "vec": [30, 20, 10]})
    assert [cid for cid, _s, _a in fused] == [30, 10, 20]
    assert fused[0][2] == ["fts", "vec"]  # provenance, arm order preserved
    assert fused[0][1] == pytest.approx(_rrf(3) + _rrf(1), abs=1e-6)  # 30: fts rank3 + vec rank1 (score rounded 6dp)


def test_rrf_single_arm_degrades_to_passthrough():
    fused = knowledge._rrf_fuse({"fts": [5, 6, 7], "vec": []})
    assert [cid for cid, _s, _a in fused] == [5, 6, 7]  # same order, no reshuffle
    assert all(arms == ["fts"] for _cid, _s, arms in fused)
    scores = [s for _cid, s, _a in fused]
    assert scores == sorted(scores, reverse=True)  # rank-monotonic


def test_rrf_tie_breaks_toward_semantic_arm():
    # perfectly symmetric ranks: only the tie-break rule (semantic arm listed last wins) decides.
    fused = knowledge._rrf_fuse({"fts": [1, 2], "vec": [2, 1]})
    assert [cid for cid, _s, _a in fused] == [2, 1]  # 2 is vector rank 1


def test_rrf_id_present_in_one_arm_only_is_scored_and_labeled():
    fused = knowledge._rrf_fuse({"fts": [1], "vec": [2]})
    by_id = {cid: (score, arms) for cid, score, arms in fused}
    assert by_id[1][1] == ["fts"] and by_id[2][1] == ["vec"]
    assert by_id[1][0] == pytest.approx(_rrf(1), abs=1e-6) and by_id[2][0] == pytest.approx(_rrf(1), abs=1e-6)
    assert [cid for cid, _s, _a in fused] == [2, 1]  # tie → semantic arm wins


def test_rrf_empty_input_is_empty():
    assert knowledge._rrf_fuse({"fts": [], "vec": []}) == []
    assert knowledge._rrf_fuse({}) == []


# --- DB: provenance + trace step ---------------------------------------------------------------

pytestmark_db = pytest.mark.django_db


def _admin(username: str) -> User:
    u = User.objects.create_user(username=username, password="Dev12345!",
                                 email=f"{username}@example.test")
    u.is_superuser = True
    u.save(update_fields=["is_superuser"])
    return u


def _ingest(body: str, title: str, actor):
    return knowledge.ingest_document(
        data=body.encode("utf-8"), media_type="text/plain",
        filename=f"{title}.txt", title=title, actor=actor,
    )


@pytest.mark.django_db
def test_search_hits_carry_arm_provenance(monkeypatch):
    actor = _admin("rrf_prov")
    _ingest("Refund policy: returns accepted within 14 days.", "Refunds", actor)
    monkeypatch.setattr(knowledge.client, "embed_text", lambda *_a, **_k: None)  # no vector arm
    results = knowledge.search("refund policy")
    assert results
    assert results[0]["arms"] == ["fts"]  # FTS-only, honestly labeled


@pytest.mark.django_db
def test_search_records_retrieval_trace_step(monkeypatch):
    actor = _admin("rrf_trace")
    _ingest("Refund policy: returns accepted within 14 days.", "Refunds", actor)
    monkeypatch.setattr(knowledge.client, "embed_text", lambda *_a, **_k: None)
    handle = TraceHandle("agent")
    knowledge.search("refund policy", trace=handle)
    steps = [s for s in handle.steps if s["kind"] == "retrieval"]
    assert len(steps) == 1
    detail = steps[0]["detail"]
    assert detail["fts"] >= 1 and detail["vec"] == 0
    assert detail["mode"] == "rrf" and detail["fused"] >= 1
    assert "top_score" in detail


@pytest.mark.django_db
def test_search_empty_still_records_retrieval_step(monkeypatch):
    _admin("rrf_trace_empty")
    monkeypatch.setattr(knowledge.client, "embed_text", lambda *_a, **_k: None)
    handle = TraceHandle("agent")
    assert knowledge.search("nonexistent zqxjw term", trace=handle) == []
    steps = [s for s in handle.steps if s["kind"] == "retrieval"]
    assert len(steps) == 1
    assert steps[0]["detail"]["fused"] == 0 and steps[0]["detail"]["mode"] == "icontains"
