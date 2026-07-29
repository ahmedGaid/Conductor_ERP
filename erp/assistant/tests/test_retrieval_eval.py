"""ai-reliability T3.3 — the offline retrieval eval suite end to end.

Dataset-shape checks (no DB) guard the committed corpus + query set; the DB test builds the fixture
corpus in the test transaction, runs all three strategies, and asserts the fusion path clears a
defensive quality floor. Marked ``retrieval`` so it can be selected/excluded; ``django_db`` gives it
the Postgres test DB (FTS needs Postgres).
"""
from __future__ import annotations

import pytest

from erp.assistant.evals import retrieval
from erp.assistant.evals import retrieval_metrics as metrics
from erp.assistant.services import knowledge

pytestmark = pytest.mark.retrieval


# --- dataset shape (no DB) ----------------------------------------------------------------------

def test_corpus_doc_keys_unique_and_single_topic():
    corpus = retrieval.load_corpus()
    keys = [d["doc_key"] for d in corpus]
    assert len(keys) == len(set(keys)), "duplicate doc_key in corpus"
    assert len(corpus) >= 12
    for d in corpus:
        assert d["lang"] in ("ar", "en")
        assert d["text"].strip()
        # authored single-chunk so a query's relevant map keys cleanly to one doc_key
        assert len(d["text"]) <= 1200


def test_query_set_meets_minimums_and_references_real_docs():
    corpus_keys = {d["doc_key"] for d in retrieval.load_corpus()}
    queries = retrieval.load_queries()
    ids = [q["id"] for q in queries]
    assert len(ids) == len(set(ids)), "duplicate query id"
    assert len(queries) >= 80, f"need >=80 queries, have {len(queries)}"
    assert sum(1 for q in queries if q["lang"] == "ar") >= 50
    for q in queries:
        assert q["query"].strip()
        assert q["relevant"], f"{q['id']} has no relevant docs"
        assert any(g >= 1 for g in q["relevant"].values()), f"{q['id']} has no grade>=1 doc"
        for key, grade in q["relevant"].items():
            assert key in corpus_keys, f"{q['id']} references unknown doc_key {key!r}"
            assert grade in (0, 1, 2), f"{q['id']} grade {grade} out of range"


# --- offline determinism (no DB) ----------------------------------------------------------------

def test_fixture_embed_is_deterministic_and_normalized():
    a = retrieval.fixture_embed("ضريبة القيمة المضافة")
    b = retrieval.fixture_embed("ضريبة القيمة المضافة")
    assert a == b
    assert len(a) == retrieval.knowledge.EMBED_DIM
    assert abs(sum(x * x for x in a) ** 0.5 - 1.0) < 1e-9
    assert retrieval.fixture_embed("") == [0.0] * retrieval.knowledge.EMBED_DIM


# --- suite end to end (Postgres test DB) --------------------------------------------------------

@pytest.mark.django_db
def test_retrieval_suite_scores_and_fusion_clears_floor():
    board = retrieval.score_suite()
    assert board["queries"] >= 80 and board["corpus_docs"] >= 12

    fusion = board["strategies"]["fusion"]["overall"]
    fts = board["strategies"]["fts"]["overall"]

    # Defensive floors (well below the Phase-3 exit targets of recall@5>=0.85 / MRR>=0.75, which
    # land only after T3.4 Arabic normalization) — a real regression trips these, fixture noise
    # does not. Actual numbers are recorded in evals/results/retrieval_baseline_vs_fusion.json.
    assert fusion["recall@5"] >= 0.80, f"fusion recall@5 too low: {fusion}"
    assert fusion["recall@10"] >= 0.90, f"fusion recall@10 too low: {fusion}"
    assert fusion["mrr"] >= 0.70, f"fusion MRR too low: {fusion}"
    assert fusion["ndcg@10"] >= 0.70, f"fusion nDCG@10 too low: {fusion}"

    # Without the whole-corpus pgvector arm the retrieved SET is the FTS pool, so fusion cannot
    # recall FEWER relevant docs than the pure-FTS baseline (its job is to re-rank that set).
    assert fusion["recall@10"] >= fts["recall@10"] - 1e-9


@pytest.mark.django_db
def test_every_primary_target_is_retrievable_within_top_10():
    """A grade-2 doc that no strategy can surface is a mis-authored query, not a model failure —
    catch it here so the dataset stays honest."""
    board = retrieval.score_suite()
    misses = [row["id"] for row in board["per_query"] if row["fusion"]["recall@10"] == 0.0]
    assert not misses, f"queries whose relevant docs never surface (fix the query/corpus): {misses}"


@pytest.mark.django_db
def test_comparison_report_has_fusion_deltas():
    report = retrieval.comparison_report(retrieval.score_suite())
    assert set(report["fusion_vs_blend"]) == {"recall@5", "recall@10", "mrr", "ndcg@10"}
    assert report["offline"] is True
    assert report["queries_ar"] >= 50


# --- T3.9: confidence-threshold tuning -----------------------------------------------------------

def test_unanswerable_query_set_meets_minimum_and_has_no_relevant_key():
    queries = retrieval.load_unanswerable()
    ids = [q["id"] for q in queries]
    assert len(ids) == len(set(ids)), "duplicate unanswerable query id"
    assert len(queries) >= 15
    for q in queries:
        assert q["lang"] in ("ar", "en")
        assert q["query"].strip()
        assert "relevant" not in q, f"{q['id']} looks answerable (has a relevant map)"


@pytest.mark.django_db
def test_confidence_labels_unanswerable_never_clears_the_floor():
    """The separation ``CONFIDENCE_THRESHOLD`` exploits, asserted on the labels themselves.

    With pgvector off (today's production default) a query with zero FTS token overlap never
    reaches the vector arm either — ``search`` only embeds when FTS found candidates to re-rank —
    so it falls to the icontains safety net, scored by content-word coverage. An unanswerable
    query can pick up a partial score there (it may share ONE word with some chunk), which is why
    this asserts the floor rather than a bare zero: no unanswerable query reaches
    ``CONFIDENCE_THRESHOLD``, while answerable ones clear it comfortably. See
    ``retrieval_confidence_threshold.json`` for the full distribution."""
    labels = retrieval.confidence_labels()
    answerable = [row for row in labels if row["answerable"]]
    unanswerable = [row for row in labels if not row["answerable"]]
    assert len(answerable) >= 80
    assert len(unanswerable) >= 15
    assert max(r["top_score"] for r in unanswerable) < knowledge.CONFIDENCE_THRESHOLD
    cleared = [r for r in answerable if r["top_score"] >= knowledge.CONFIDENCE_THRESHOLD]
    assert len(cleared) / len(answerable) >= 0.9


@pytest.mark.django_db
def test_confidence_report_best_threshold_gives_real_protection_not_just_raw_f1():
    report = retrieval.confidence_report()
    best = report["best_threshold"]
    assert report["answerable"] >= 80 and report["unanswerable"] >= 15
    # threshold=0 answers everything, including every unanswerable query (fp = all of them). On a
    # lopsided label set (94 answerable vs 15 unanswerable) F1's recall term can let that unsafe
    # cut outscore a safe one, so ``best_confidence_threshold`` minimizes fp FIRST and only then
    # maximizes F1 — it must never return the answer-everything threshold, whatever F1 says.
    always_confident = metrics.confidence_confusion(
        [(row["top_score"], row["answerable"]) for row in report["per_query"]], threshold=0.0,
    )
    assert always_confident["fp"] == report["unanswerable"]
    assert best["threshold"] > 0.0
    assert best["fp"] == 0, "tuned threshold must give zero false positives on this fixture"
    # Since T3.9 scored the icontains tier by content-word coverage the two goals stopped fighting:
    # the safe cut now also wins on raw F1. Asserted so a retrieval change that re-muddies the
    # separation — dropping the safe cut back below answer-everything — shows up here.
    assert best["f1"] > always_confident["f1"]
