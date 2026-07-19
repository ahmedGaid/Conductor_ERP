"""Exact-match response cache (ai-reliability T2.5): deterministic system tasks stop re-paying
for identical inputs.

Only task classes in ``settings.ASSISTANT_CACHE_TASKS`` may cache (v1: digest, suggest, judge);
the interactive/agentic classes (chat, ask, agent_*, extract) are hard-denied here regardless of
settings — a stale answer in a conversation or an extraction is worse than a re-paid call.
Invalidation is TTL per task (``ASSISTANT_CACHE_TTLS``, seconds; missing/None = no expiry) plus
an explicit ``bump(task)`` hook for data-changing services.

Same philosophy as ``services.tracing``: a cache failure (DB down, bad row) must never break the
AI call it fronts — every function swallows its own errors and degrades to a miss/no-op.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import timedelta

from django.conf import settings
from django.db.models import F
from django.utils import timezone

from .. import models as assistant_models

logger = logging.getLogger(__name__)

# Task classes that must NEVER cache, even if the settings allowlist is misconfigured to include
# one — user-facing conversation turns and document extractions are never safely reusable.
NEVER_CACHE = frozenset({"chat", "ask", "agent", "agent_plan", "agent_answer", "extract"})


def enabled(task: str | None) -> bool:
    """Whether this task class may use the cache: allowlisted in settings AND not hard-denied.
    An untraced call (``task`` None/empty) never caches — there'd be no trace to show the hit."""
    if not task or task in NEVER_CACHE:
        return False
    return task in getattr(settings, "ASSISTANT_CACHE_TASKS", set())


def make_key(task: str, prompt_ref: str, model: str, system: str, user: str, schema: dict,
             media: list | None) -> str:
    """sha256 over the canonicalized full input — any byte of prompt, schema, model, or media
    changing produces a different key. Media bytes enter as their own sha256, not raw."""
    media_hashes = [
        {"media_type": m.get("media_type", ""),
         "sha256": hashlib.sha256(m.get("data") or b"").hexdigest()}
        for m in (media or [])
    ]
    payload = json.dumps(
        {"task": task, "prompt_ref": prompt_ref, "model": model, "system": system,
         "user": user, "schema": schema, "media": media_hashes},
        sort_keys=True, ensure_ascii=False, separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def current_version(task: str) -> int:
    try:
        row = assistant_models.ResponseCacheVersion.objects.filter(task=task).first()
        return row.version if row else 0
    except Exception:
        logger.exception("response cache: current_version failed — treating as 0")
        return 0


def get(task: str, key: str) -> dict | None:
    """The cached response for ``key``, or None on any miss: absent, written under an older
    version (see ``bump``), past its TTL, or a cache-layer error."""
    try:
        row = assistant_models.ResponseCache.objects.filter(
            key=key, input_version=current_version(task)).first()
        if row is None:
            return None
        ttl_s = getattr(settings, "ASSISTANT_CACHE_TTLS", {}).get(task)
        if ttl_s is not None and row.created_at < timezone.now() - timedelta(seconds=ttl_s):
            return None
        assistant_models.ResponseCache.objects.filter(pk=row.pk).update(
            hit_count=F("hit_count") + 1)
        return row.response
    except Exception:
        logger.exception("response cache: get failed — treating as a miss")
        return None


def put(task: str, key: str, response: dict) -> None:
    """Store (or refresh) ``key`` at the task's current version. ``created_at`` and ``hit_count``
    reset on refresh so the TTL counts from this write."""
    try:
        assistant_models.ResponseCache.objects.update_or_create(
            key=key,
            defaults={"task": task, "response": response,
                      "input_version": current_version(task),
                      "created_at": timezone.now(), "hit_count": 0},
        )
    except Exception:
        logger.exception("response cache: put failed — response not cached")


def bump(task: str) -> None:
    """Invalidate every cached response for ``task`` — call from data-changing services when the
    world a cached answer described has changed."""
    try:
        row, _created = assistant_models.ResponseCacheVersion.objects.get_or_create(task=task)
        assistant_models.ResponseCacheVersion.objects.filter(pk=row.pk).update(
            version=F("version") + 1)
    except Exception:
        logger.exception("response cache: bump failed — cache not invalidated")


# --- Semantic cache for knowledge Q&A (ai-reliability T2.8) ---------------------------------------
#
# Near-duplicate questions reuse a verified knowledge answer instead of re-running the router +
# answer model. Independent of the exact-match cache above: keyed by cosine similarity over a
# question embedding, scoped per user (answers are permission-scoped — never shared across users
# in v1), and invalidated by the same task-version mechanism as ``bump``/``current_version``
# (task="knowledge", bumped by ``services.knowledge.ingest_document`` on every successful ingest).

SEMANTIC_CACHE_TASK = "knowledge"


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


def semantic_enabled() -> bool:
    return bool(getattr(settings, "ASSISTANT_SEMANTIC_CACHE", True))


def semantic_lookup(actor, embedding: list[float] | None) -> dict | None:
    """The best near-duplicate answer for this user at the current knowledge version, or None on
    any miss (disabled, no embedding, no row clears the threshold, or a cache-layer error)."""
    if not semantic_enabled() or not embedding:
        return None
    if actor is None or not getattr(actor, "is_authenticated", False):
        return None
    threshold = getattr(settings, "ASSISTANT_SEMANTIC_CACHE_THRESHOLD", 0.95)
    try:
        version = current_version(SEMANTIC_CACHE_TASK)
        rows = assistant_models.SemanticCache.objects.filter(
            user=actor, knowledge_version=version,
        ).order_by("-created_at")[:500]
        best_row, best_score = None, 0.0
        for row in rows:
            score = _cosine(embedding, row.question_embedding)
            if score > best_score:
                best_row, best_score = row, score
        if best_row is None or best_score < threshold:
            return None
        assistant_models.SemanticCache.objects.filter(pk=best_row.pk).update(
            hit_count=F("hit_count") + 1)
        return {"answer": best_row.answer, "citations": best_row.citations}
    except Exception:
        logger.exception("semantic cache: lookup failed — treating as a miss")
        return None


def semantic_put(actor, *, question_text: str, embedding: list[float] | None, answer: str,
                 citations: list) -> None:
    """Store one verified knowledge answer for future near-duplicate reuse. Caps at
    ``ASSISTANT_SEMANTIC_CACHE_CAP`` rows per user, evicting the oldest first — a pgvector index
    in Phase 3 (T3.1) replaces this Python scan + cap; the interface here stays the same."""
    if not semantic_enabled() or not embedding:
        return
    if actor is None or not getattr(actor, "is_authenticated", False):
        return
    try:
        assistant_models.SemanticCache.objects.create(
            user=actor, question_text=question_text[:500], question_embedding=embedding,
            answer=answer, citations=citations,
            knowledge_version=current_version(SEMANTIC_CACHE_TASK),
        )
        cap = getattr(settings, "ASSISTANT_SEMANTIC_CACHE_CAP", 500)
        stale_ids = list(
            assistant_models.SemanticCache.objects.filter(user=actor)
            .order_by("-created_at").values_list("id", flat=True)[cap:]
        )
        if stale_ids:
            assistant_models.SemanticCache.objects.filter(id__in=stale_ids).delete()
    except Exception:
        logger.exception("semantic cache: put failed — response not cached")
