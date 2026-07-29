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


# --- T3.9: confidence-threshold tuning ("I don't know" discipline) ------------------------------
#
# Separate from ranking quality above: here each query has a single fused *top score* and a true
# label — answerable (>=1 labeled-relevant doc) or not. A threshold turns the score into a binary
# decision (answer / decline); these functions find the threshold that best matches the labels.

def confidence_confusion(labels: list, threshold: float) -> dict:
    """Confusion counts + precision/recall/F1 of the "answer" decision (predict confident when
    ``top_score >= threshold``) against true answerability, at one threshold.

    ``labels`` is ``[(top_score, answerable), ...]``. False positives (confident on an
    unanswerable query) are the hallucination risk this threshold exists to bound; false negatives
    (declining an answerable query) are the cost of being too cautious — F1 weighs both equally.
    """
    tp = fp = fn = tn = 0
    for score, answerable in labels:
        confident = score >= threshold
        if confident and answerable:
            tp += 1
        elif confident and not answerable:
            fp += 1
        elif not confident and answerable:
            fn += 1
        else:
            tn += 1
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {"threshold": threshold, "precision": precision, "recall": recall, "f1": f1,
            "tp": tp, "fp": fp, "fn": fn, "tn": tn}


def best_confidence_threshold(labels: list) -> dict:
    """The threshold — scanned over every observed top score, so it's always an achievable cut —
    that best separates answerable from unanswerable queries.

    Plain argmax-F1 is unsafe here: retrieval eval sets are typically lopsided (far more
    answerable than unanswerable queries), and F1's harmonic mean lets a handful of false
    positives hide behind a large recall term — the threshold that maximizes raw F1 can be the
    trivial "answer everything" one, which gives zero protection against the exact failure T3.9
    exists to prevent (see ``retrieval_confidence_threshold.json`` for the real numbers that
    exposed this). A false "confident" on an unanswerable query risks a fabricated-sounding
    answer; a false decline on an answerable one just asks the user to rephrase — so false
    positives are minimized FIRST, and F1 only chooses among the thresholds tied at that minimum
    (ties broken toward the higher threshold — the stricter of two equally-good cuts).

    Empty input has nothing to separate; returns an all-zero result rather than raising.
    """
    if not labels:
        return {"threshold": 0.0, "precision": 0.0, "recall": 0.0, "f1": 0.0,
                "tp": 0, "fp": 0, "fn": 0, "tn": 0}
    candidates = sorted({score for score, _answerable in labels})
    scored = [confidence_confusion(labels, threshold) for threshold in candidates]
    min_fp = min(result["fp"] for result in scored)
    best = None
    for result in scored:
        if result["fp"] != min_fp:
            continue
        if (best is None or result["f1"] > best["f1"]
                or (result["f1"] == best["f1"] and result["threshold"] > best["threshold"])):
            best = result
    return best
