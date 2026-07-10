"""Retry policy (Phase 2, T2.2): decide whether a provider exception is worth retrying, and how
long to back off before the next attempt.

Table-driven and dependency-free (mirrors ``errors.classify_exception``'s approach): every
provider SDK (Anthropic, Gemini, Groq/Mistral's httpx) raises its own exception classes, so this
matches on the exception's class name + message instead of importing any of them. Kept separate
from ``errors.classify_exception`` on purpose — that taxonomy answers "which ops bucket does this
failure belong to", this answers a narrower question ("would trying again help"), and the two
don't always agree (a 500 and a 429 are both ``provider_error``-ish but both retryable, while a
401 is also provider-shaped but never worth retrying).
"""
from __future__ import annotations

import random

MAX_RETRIES = 2  # + 1 initial attempt = 3 total, per provider that gets a retry budget
BACKOFF_BASE = 0.5
BACKOFF_CAP = 4.0

# Checked first: a permanent-looking marker wins even if a retryable one also matches (e.g. an
# httpx "ConnectionError" whose message happens to mention "invalid_api_key").
_PERMANENT_MARKERS = (
    "authenticationerror", "permissiondeniederror", "invalidrequesterror",
    "unauthorized", "forbidden", "401", "403",
    "badrequest", "400", "invalid_request", "invalid_api_key",
    "content_policy", "content policy", "safety",
)
_RETRYABLE_MARKERS = (
    "ratelimit", "rate limit", "429", "too many requests",
    "internalservererror", "serviceunavailable", "overloaded",
    "500", "502", "503", "504",
    "connectionerror", "connection reset", "connection aborted",
    "timeout", "timed out",
    "apiconnectionerror", "apistatuserror",
)


def is_retryable(exc: BaseException) -> bool:
    """True if ``exc`` looks transient (a retry may succeed); False for anything structural (a
    retry would only waste the backoff and the user's turn) or unrecognized — unknown failures
    fail fast rather than guess."""
    haystack = f"{exc.__class__.__name__} {exc}".lower()
    if any(marker in haystack for marker in _PERMANENT_MARKERS):
        return False
    return any(marker in haystack for marker in _RETRYABLE_MARKERS)


def backoff_seconds(attempt: int) -> float:
    """Exponential backoff with full jitter, capped at ``BACKOFF_CAP``. ``attempt`` is 0-indexed
    (the attempt that just failed) — attempt 0 waits up to ``BACKOFF_BASE``, attempt 1 up to
    ``2 * BACKOFF_BASE``, etc."""
    ceiling = min(BACKOFF_BASE * (2 ** attempt), BACKOFF_CAP)
    return random.uniform(0, ceiling)
