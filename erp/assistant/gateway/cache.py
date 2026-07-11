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
