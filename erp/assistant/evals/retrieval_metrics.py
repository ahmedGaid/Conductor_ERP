"""Pure retrieval-quality metrics (ai-reliability T3.3).

Ranking metrics over an ordered list of retrieved item ids and a per-query relevance labelling.
No DB, no provider, no Django — pure functions, exhaustively unit-tested against hand-computed
values (``tests/test_retrieval_metrics.py``). The retrieval suite (``evals/retrieval.py``) feeds
these the ranked ids a real ``knowledge.search`` produced; nothing here knows where the ranking
came from, so a metric can never be quietly "helped" by the thing it measures.

Terms:
  * ``ranked`` — item ids best-first, as returned by search (deduplicated by the caller).
  * ``grades`` — ``{item_id: grade}`` where grade is 0 (irrelevant), 1 (related), 2 (ideal).
    An id absent from ``grades`` is grade 0. "Relevant" means grade >= 1.

nDCG uses the exponential gain ``2**grade - 1`` (the common IR form: grade 2 is worth more than
two grade-1 hits) and the standard ``log2(rank + 1)`` discount. All metrics are in ``[0, 1]``.
"""
from __future__ import annotations

from math import log2

RELEVANT_MIN_GRADE = 1


def relevant_ids(grades: dict, *, min_grade: int = RELEVANT_MIN_GRADE) -> set:
    """The set of ids counted as relevant (grade >= ``min_grade``)."""
    return {item_id for item_id, g in grades.items() if g >= min_grade}


def recall_at_k(ranked: list, grades: dict, k: int) -> float:
    """Fraction of the query's relevant items that appear in the top ``k`` retrieved.

    ``0.0`` when the query has no relevant items (nothing to recall) — the caller decides whether
    such queries belong in the set; here it is simply an undefined ratio pinned to 0.
    """
    relevant = relevant_ids(grades)
    if not relevant:
        return 0.0
    hits = sum(1 for item_id in ranked[:k] if item_id in relevant)
    return hits / len(relevant)


def reciprocal_rank(ranked: list, grades: dict) -> float:
    """``1 / rank`` of the first relevant item (rank counts from 1), else ``0.0``."""
    relevant = relevant_ids(grades)
    for rank, item_id in enumerate(ranked, start=1):
        if item_id in relevant:
            return 1.0 / rank
    return 0.0


def _dcg(gains: list) -> float:
    """Discounted cumulative gain of an ordered list of per-position gains."""
    return sum(gain / log2(rank + 1) for rank, gain in enumerate(gains, start=1))


def ndcg_at_k(ranked: list, grades: dict, k: int) -> float:
    """Normalized DCG at ``k`` with exponential gain ``2**grade - 1``.

    IDCG is the DCG of the best possible ordering of the graded items. Returns ``0.0`` when no
    graded item is relevant (IDCG would be 0).
    """
    def gain(item_id) -> float:
        return (2 ** grades.get(item_id, 0)) - 1

    dcg = _dcg([gain(item_id) for item_id in ranked[:k]])
    ideal_gains = sorted((gain(item_id) for item_id in grades), reverse=True)[:k]
    idcg = _dcg(ideal_gains)
    return dcg / idcg if idcg else 0.0


def score_query(ranked: list, grades: dict) -> dict:
    """All four headline metrics for one query's ranking, as a plain dict."""
    return {
        "recall@5": recall_at_k(ranked, grades, 5),
        "recall@10": recall_at_k(ranked, grades, 10),
        "mrr": reciprocal_rank(ranked, grades),
        "ndcg@10": ndcg_at_k(ranked, grades, 10),
    }


def mean_metrics(per_query: list) -> dict:
    """Macro-average of per-query metric dicts (each query weighted equally). Empty -> zeros."""
    keys = ["recall@5", "recall@10", "mrr", "ndcg@10"]
    if not per_query:
        return {key: 0.0 for key in keys}
    return {key: sum(m[key] for m in per_query) / len(per_query) for key in keys}
