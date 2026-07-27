"""LLM rerank stage (ai-reliability T3.5): sharpens RRF's fused top-N into a better top-K by
having a model score each candidate's relevance, one batched call. Eval-gated — kept ON only if
``evals/results/rerank_decision.json`` shows a real nDCG lift within the latency budget — and
fail-open: any provider/parse trouble leaves the fused order standing, since a broken rerank must
never be worse than no rerank at all.
"""
from __future__ import annotations

import logging

from django.conf import settings

from ..gateway.core import complete_json
from ..services.prompt_registry import get as get_prompt

logger = logging.getLogger(__name__)

# Excerpt length kept short: 20 candidates x a long excerpt would blow the rerank call's own
# token budget for no benefit — the model only needs enough text to judge topical relevance.
EXCERPT_CHARS = 400

_SCHEMA = {
    "type": "object", "required": ["scores"],
    "properties": {"scores": {"type": "array", "items": {
        "type": "object", "required": ["i", "score"],
        "properties": {"i": {"type": "integer"}, "score": {"type": "integer"}},
    }}},
}


def enabled() -> bool:
    return bool(getattr(settings, "ASSISTANT_RERANK", False))


def _ambiguous(rows: list[dict]) -> bool:
    """True when the fused top-2 scores are close enough that reranking could change the winner
    (T3.5 step 4's latency guard) — a clear-cut top pick skips the extra round-trip entirely.
    ``rows`` is the fused RRF order, best first; ``score`` is the RRF score (see
    ``knowledge._rrf_fuse``), not a probability, so the gap is compared against a settings
    constant tuned empirically against the retrieval eval set, not a fixed statistical bound."""
    if len(rows) < 2:
        return False
    gap = rows[0]["score"] - rows[1]["score"]
    return gap <= getattr(settings, "ASSISTANT_RERANK_AMBIGUITY_GAP", 0.004)


def _excerpt_block(rows: list[dict]) -> str:
    return "\n".join(f"[{i}] {r['text'][:EXCERPT_CHARS]}" for i, r in enumerate(rows))


def maybe_rerank(query: str, rows: list[dict], *, top_k: int, trace=None) -> list[dict]:
    """Narrow ``rows`` (fused RRF order, best first) to ``top_k`` — reranked by LLM relevance when
    the flag is on and the fused top is ambiguous, else the fused order truncated as before.

    Never raises: a rerank failure (provider down, unparseable JSON) logs and falls back to the
    fused order, exactly as if rerank were off for that one call.
    """
    if not rows:
        return rows
    if not enabled():
        return rows[:top_k]
    if not _ambiguous(rows):
        if trace is not None:
            trace.step(kind="retrieval", name="rerank_skipped", detail={"reason": "unambiguous"})
        return rows[:top_k]

    prompt = get_prompt("rerank")
    system = prompt.render(query=query, excerpts=_excerpt_block(rows))
    try:
        result = complete_json(
            system, "Score every passage now.", _SCHEMA, feature="rerank", prompt_ref=prompt.ref,
        )
        scores = {
            int(s["i"]): int(s["score"]) for s in result.get("scores", [])
            if isinstance(s, dict) and "i" in s and "score" in s
        }
        if not scores:
            raise ValueError("rerank: empty or unparseable scores")
        order = sorted(range(len(rows)), key=lambda i: (-scores.get(i, -1), i))
        reranked = [rows[i] for i in order[:top_k]]
        if trace is not None:
            trace.step(kind="retrieval", name="rerank",
                       detail={"candidates": len(rows), "top_k": top_k})
        return reranked
    except Exception:
        logger.exception("rerank: failed — fused order stands")
        if trace is not None:
            trace.step(kind="retrieval", name="rerank_skipped", ok=False, detail={"reason": "error"})
        return rows[:top_k]
