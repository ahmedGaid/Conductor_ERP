"""Circuit breaker (Phase 2, T2.3): a provider that keeps failing gets skipped for a cooldown
instead of being retried on every request — a slow/down provider stops adding latency (and burning
its retry budget) to every call while it recovers on its own.

Per-provider, not per-model (a provider outage takes every model behind it down together). State
lives in Django's cache framework (no new dependency) — degrades gracefully to "always closed" (the
breaker never opens, calls just keep trying the provider) if the configured backend can't count
atomically; the default backend with no ``CACHES`` setting (``LocMemCache``, today's dev/prod) can.
"""
from __future__ import annotations

import time

from django.core.cache import cache

FAILURE_THRESHOLD = 5  # consecutive retryable failures inside the window that opens the breaker
FAILURE_WINDOW_S = 60  # the failure count resets this long after the first failure in a streak
COOLDOWN_S = 30  # how long a breaker stays fully open before allowing one half-open probe

_FAILURES_KEY = "assistant:breaker:{}:failures"
_OPENED_KEY = "assistant:breaker:{}:opened_at"


def record_failure(provider: str) -> None:
    """Count one retryable failure toward opening ``provider``'s breaker. Only the caller (T2.3
    integration in ``gateway/core.py``) decides an exception is failure-worthy — a permanent error
    (401/403/…) never reaches here, since retrying it would never help and a bad key isn't an
    outage."""
    key = _FAILURES_KEY.format(provider)
    try:
        if cache.add(key, 1, timeout=FAILURE_WINDOW_S):
            count = 1
        else:
            count = cache.incr(key)
    except (ValueError, NotImplementedError):
        return  # backend can't count atomically (e.g. DummyCache) — degrade to always-closed
    if count >= FAILURE_THRESHOLD:
        cache.set(_OPENED_KEY.format(provider), time.time(), timeout=None)


def record_success(provider: str) -> None:
    """A working call closes the breaker and clears the failure streak."""
    cache.delete(_FAILURES_KEY.format(provider))
    cache.delete(_OPENED_KEY.format(provider))


def state(provider: str) -> str:
    """``"closed"`` (default, try it) · ``"open"`` (skip it) · ``"half_open"`` (cooldown elapsed —
    the chain-walk in ``core.py`` gets exactly one probe attempt; ``record_success`` /
    ``record_failure`` afterwards decide whether it re-closes or re-opens)."""
    opened_at = cache.get(_OPENED_KEY.format(provider))
    if opened_at is None:
        return "closed"
    if time.time() - opened_at >= COOLDOWN_S:
        return "half_open"
    return "open"


def is_open(provider: str) -> bool:
    return state(provider) == "open"
