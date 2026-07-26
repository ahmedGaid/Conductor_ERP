"""ai-reliability T3.3 — pure retrieval-metric math, checked against values computed by hand.

No DB, no Django, no network: just the functions in ``evals/retrieval_metrics.py``. Each nDCG
expected value is written as the explicit human formula (``gain / log2(rank + 1)``) so the test
documents the derivation rather than echoing the implementation.
"""
from __future__ import annotations

from math import log2

import pytest

from erp.assistant.evals import retrieval_metrics as m


# --- relevant_ids -------------------------------------------------------------------------------

def test_relevant_ids_is_grade_one_or_higher():
    grades = {"a": 2, "b": 1, "c": 0, "d": 3}
    assert m.relevant_ids(grades) == {"a", "b", "d"}


# --- recall@k -----------------------------------------------------------------------------------

def test_recall_counts_relevant_in_top_k_over_all_relevant():
    grades = {"a": 2, "d": 1, "z": 2}  # 3 relevant; "z" never retrieved
    ranked = ["a", "b", "c", "d", "e", "f"]
    assert m.recall_at_k(ranked, grades, 5) == pytest.approx(2 / 3)   # a@1, d@4 in top-5
    assert m.recall_at_k(ranked, grades, 10) == pytest.approx(2 / 3)  # f irrelevant, z absent


def test_recall_at_5_excludes_relevant_below_the_cutoff():
    grades = {"a": 1, "f": 2}  # f is at position 6
    ranked = ["a", "b", "c", "d", "e", "f"]
    assert m.recall_at_k(ranked, grades, 5) == pytest.approx(1 / 2)   # only a within top-5
    assert m.recall_at_k(ranked, grades, 10) == pytest.approx(1.0)    # both within top-10


def test_recall_is_zero_when_no_relevant_items():
    assert m.recall_at_k(["a", "b"], {"a": 0}, 5) == 0.0
    assert m.recall_at_k(["a", "b"], {}, 5) == 0.0


# --- reciprocal rank (MRR is the mean of these) -------------------------------------------------

def test_reciprocal_rank_is_inverse_of_first_relevant_position():
    grades = {"a": 2}
    assert m.reciprocal_rank(["a", "b", "c"], grades) == pytest.approx(1.0)     # rank 1
    assert m.reciprocal_rank(["b", "a", "c"], grades) == pytest.approx(1 / 2)   # rank 2
    assert m.reciprocal_rank(["b", "c", "a"], grades) == pytest.approx(1 / 3)   # rank 3


def test_reciprocal_rank_zero_when_no_relevant_retrieved():
    assert m.reciprocal_rank(["b", "c"], {"a": 2}) == 0.0


# --- nDCG@k -------------------------------------------------------------------------------------

def test_ndcg_perfect_ordering_is_one():
    grades = {"a": 2, "b": 1, "c": 0}
    assert m.ndcg_at_k(["a", "b", "c"], grades, 10) == pytest.approx(1.0)


def test_ndcg_suboptimal_ordering_hand_computed():
    grades = {"a": 2, "b": 1, "c": 0}
    ranked = ["b", "a", "c"]  # a grade-2 demoted below a grade-1
    # gains: 2**g - 1 -> a=3, b=1, c=0
    dcg = 1 / log2(2) + 3 / log2(3) + 0 / log2(4)   # b@1, a@2, c@3
    idcg = 3 / log2(2) + 1 / log2(3) + 0 / log2(4)  # ideal order a, b, c
    assert m.ndcg_at_k(ranked, grades, 10) == pytest.approx(dcg / idcg)


def test_ndcg_respects_the_k_cutoff():
    grades = {"a": 2, "b": 2, "c": 1, "d": 1}
    ranked = ["c", "a", "b", "d"]  # a grade-1 first, at k=2 only c and a count
    dcg = 1 / log2(2) + 3 / log2(3)   # gain(c)=1 @1, gain(a)=3 @2
    idcg = 3 / log2(2) + 3 / log2(3)  # best two gains are 3, 3
    assert m.ndcg_at_k(ranked, grades, 2) == pytest.approx(dcg / idcg)


def test_ndcg_zero_when_nothing_relevant():
    assert m.ndcg_at_k(["a", "b"], {"a": 0}, 10) == 0.0
    assert m.ndcg_at_k(["a", "b"], {}, 10) == 0.0


# --- aggregation --------------------------------------------------------------------------------

def test_score_query_bundles_the_four_headline_metrics():
    grades = {"a": 2, "b": 1}
    out = m.score_query(["a", "b", "c"], grades)
    assert set(out) == {"recall@5", "recall@10", "mrr", "ndcg@10"}
    assert out["recall@5"] == pytest.approx(1.0)
    assert out["mrr"] == pytest.approx(1.0)
    assert out["ndcg@10"] == pytest.approx(1.0)


def test_mean_metrics_macro_averages_per_query():
    q1 = {"recall@5": 1.0, "recall@10": 1.0, "mrr": 1.0, "ndcg@10": 1.0}
    q2 = {"recall@5": 0.0, "recall@10": 0.5, "mrr": 0.5, "ndcg@10": 0.0}
    avg = m.mean_metrics([q1, q2])
    assert avg["recall@5"] == pytest.approx(0.5)
    assert avg["recall@10"] == pytest.approx(0.75)
    assert avg["mrr"] == pytest.approx(0.75)


def test_mean_metrics_empty_is_zero():
    assert m.mean_metrics([]) == {"recall@5": 0.0, "recall@10": 0.0, "mrr": 0.0, "ndcg@10": 0.0}
