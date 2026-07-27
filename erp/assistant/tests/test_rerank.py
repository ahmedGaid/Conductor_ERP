"""LLM rerank stage (ai-reliability T3.5): flag-gated, ambiguity-gated, fail-open. No DB needed —
``maybe_rerank`` is pure aside from the (monkeypatched) gateway call."""
from __future__ import annotations

from django.test import override_settings

from erp.assistant.services import rerank
from erp.assistant.services.tracing import TraceHandle

ROWS = [
    {"document_id": 1, "title": "A", "seq": 0, "text": "alpha content about refunds", "score": 0.02, "arms": ["fts"]},
    {"document_id": 2, "title": "B", "seq": 0, "text": "beta content about shipping", "score": 0.019, "arms": ["fts"]},
    {"document_id": 3, "title": "C", "seq": 0, "text": "gamma content about invoices", "score": 0.01, "arms": ["vec"]},
]


def _clear_row(overrides):
    rows = [dict(r) for r in ROWS]
    for row, score in zip(rows, overrides):
        row["score"] = score
    return rows


# --- flag off: byte-identical to plain truncation, never calls the model -------------------------

@override_settings(ASSISTANT_RERANK=False)
def test_disabled_returns_fused_order_truncated(monkeypatch):
    monkeypatch.setattr(rerank, "complete_json", lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("must not call the model when disabled")))
    out = rerank.maybe_rerank("refund policy", ROWS, top_k=2)
    assert out == ROWS[:2]


def test_empty_rows_short_circuits():
    assert rerank.maybe_rerank("q", [], top_k=5) == []


# --- ambiguity gate: an obvious top pick skips the extra round-trip -------------------------------

@override_settings(ASSISTANT_RERANK=True, ASSISTANT_RERANK_AMBIGUITY_GAP=0.004)
def test_unambiguous_top_skips_rerank_call(monkeypatch):
    rows = _clear_row([0.05, 0.01, 0.005])  # top gap 0.04 >> 0.004 threshold
    monkeypatch.setattr(rerank, "complete_json", lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("must not call the model when the top pick is unambiguous")))
    handle = TraceHandle("agent")
    out = rerank.maybe_rerank("q", rows, top_k=2, trace=handle)
    assert out == rows[:2]
    steps = [s for s in handle.steps if s["kind"] == "retrieval"]
    assert len(steps) == 1
    assert steps[0]["name"] == "rerank_skipped"
    assert steps[0]["detail"]["reason"] == "unambiguous"


# --- ambiguous top: calls the model, reorders by its scores ---------------------------------------

@override_settings(ASSISTANT_RERANK=True, ASSISTANT_RERANK_AMBIGUITY_GAP=0.004)
def test_ambiguous_top_reranks_by_model_score(monkeypatch):
    rows = _clear_row([0.02, 0.019, 0.01])  # top gap 0.001 <= 0.004 threshold
    calls = []

    def fake_complete_json(system, user, schema, **kwargs):
        calls.append((system, user, kwargs.get("feature")))
        # Model prefers index 2 (gamma) over 0 and 1, reversing the fused order.
        return {"scores": [{"i": 0, "score": 1}, {"i": 1, "score": 0}, {"i": 2, "score": 3}]}

    monkeypatch.setattr(rerank, "complete_json", fake_complete_json)
    handle = TraceHandle("agent")
    out = rerank.maybe_rerank("q", rows, top_k=2, trace=handle)

    assert [r["document_id"] for r in out] == [3, 1]  # gamma first (score 3), alpha second (score 1)
    assert calls and calls[0][2] == "rerank"
    steps = [s for s in handle.steps if s["kind"] == "retrieval"]
    assert len(steps) == 1 and steps[0]["name"] == "rerank"
    assert steps[0]["detail"] == {"candidates": 3, "top_k": 2}


# --- fail-open: any provider/parse trouble leaves the fused order standing ------------------------

@override_settings(ASSISTANT_RERANK=True, ASSISTANT_RERANK_AMBIGUITY_GAP=0.004)
def test_provider_error_falls_back_to_fused_order(monkeypatch):
    rows = _clear_row([0.02, 0.019, 0.01])

    def boom(*a, **k):
        raise RuntimeError("provider down")

    monkeypatch.setattr(rerank, "complete_json", boom)
    handle = TraceHandle("agent")
    out = rerank.maybe_rerank("q", rows, top_k=2, trace=handle)

    assert out == rows[:2]
    steps = [s for s in handle.steps if s["kind"] == "retrieval"]
    assert len(steps) == 1
    assert steps[0]["name"] == "rerank_skipped" and steps[0]["ok"] is False
    assert steps[0]["detail"]["reason"] == "error"


@override_settings(ASSISTANT_RERANK=True, ASSISTANT_RERANK_AMBIGUITY_GAP=0.004)
def test_unparseable_scores_falls_back_to_fused_order(monkeypatch):
    rows = _clear_row([0.02, 0.019, 0.01])
    monkeypatch.setattr(rerank, "complete_json", lambda *a, **k: {"scores": []})
    out = rerank.maybe_rerank("q", rows, top_k=2)
    assert out == rows[:2]


# --- ambiguity gate itself (pure) ------------------------------------------------------------------

@override_settings(ASSISTANT_RERANK_AMBIGUITY_GAP=0.004)
def test_ambiguous_helper_pure():
    assert rerank._ambiguous(_clear_row([0.02, 0.019, 0.01])) is True
    assert rerank._ambiguous(_clear_row([0.05, 0.01, 0.005])) is False
    assert rerank._ambiguous(_clear_row([0.02])[:1]) is False  # single row: nothing to compare
