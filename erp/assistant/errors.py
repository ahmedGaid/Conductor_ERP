"""Assistant error catalog. Blame-free: the document or the service is at fault, never the user."""
from __future__ import annotations

from erp.core.errors import AppError


class ExtractionFailedError(AppError):
    """The AI service could not be reached or returned garbage — retryable, not the user's fault."""

    code = "AI-001"
    status_code = 502
    message = "The assistant could not process this document right now"


class AssistantUnavailableError(AppError):
    """The natural-language assistant could not reach the model or parse its reply — retryable."""

    code = "AI-002"
    status_code = 502
    message = "The assistant is unavailable right now"


class AllProvidersDown(AssistantUnavailableError):
    """Every provider in the failover chain is either erroring or breaker-open (T2.3) — same
    blame-free surface as ``AssistantUnavailableError`` (existing callers/UI already handle it
    generically), just a distinct type so tests and ops tooling can tell "one provider hiccuped"
    from "the whole chain is out"."""

    code = "AI-006"


class ActionAlreadyHandledError(AppError):
    """A proposal was confirmed or dismissed already — single-use, never runs twice."""

    code = "AI-003"
    status_code = 409
    message = "This action was already handled"


class ActionForbiddenError(AppError):
    """The caller's role cannot create this document — the calm refusal at confirm time."""

    code = "AI-004"
    status_code = 403
    message = "You do not have permission to create this document"


class ActionFailedError(AppError):
    """Executing a confirmed action failed unexpectedly — the proposal stays reusable."""

    code = "AI-005"
    status_code = 400
    message = "That could not be created just now"


class VerifierFailed(AppError):
    """A post-write invariant pack failed (os-foundations FILE_03) — the atomic write was rolled
    back, so nothing persisted. Blame-free: it's our check that failed, not the user's input.
    ``data["findings"]`` carries the pack verdicts verbatim for the card."""

    code = "AI-008"
    status_code = 422
    message = "The draft could not be saved because a check failed. Nothing was written."


class BudgetExceeded(AppError):
    """A cost/token budget (request, user/day, or org/month — ai-reliability T2.7) is exhausted;
    the call was blocked before any provider was tried. Blame-free and distinct from a provider
    outage: the fix is an admin raising the budget, not retrying."""

    code = "AI-007"
    status_code = 429
    message = "This AI budget has been used up for now — ask an admin to raise it"


# --- error taxonomy (ai-reliability T1.9) -------------------------------------------------------
# Closed set every ``Trace.error_class`` value is mapped into at the tracing seam
# (``services/tracing.py``) — ops aggregation (top error classes, alerts) reasons over a handful
# of buckets, never an unbounded set of raw exception class names.
ERROR_TAXONOMY = (
    "provider_error",
    "timeout",
    "rate_limited",
    "tool_error",
    "validation_failed",
    "guardrail_blocked",
    "context_overflow",
    "cancelled",
    "budget_exceeded",
    "unknown",
)


def classify_exception(exc: BaseException) -> str:
    """Map any exception raised (or swallowed) at an AI call site to one of ``ERROR_TAXONOMY``.

    Matches by type first (this module's own blame-free errors), then by name/message keywords —
    provider SDKs (Anthropic, Gemini, Groq/Mistral's httpx) each raise their own exception classes,
    and this stays dependency-free by never importing them. Falls back to ``"unknown"`` rather than
    leaking a raw class name, so the taxonomy stays closed."""
    name = exc.__class__.__name__
    lname = name.lower()
    text = str(exc).lower()

    if isinstance(exc, GeneratorExit) or "cancelled" in lname:
        return "cancelled"
    if isinstance(exc, ActionForbiddenError):
        return "guardrail_blocked"
    if isinstance(exc, BudgetExceeded):
        return "budget_exceeded"
    if isinstance(exc, ActionFailedError):
        return "tool_error"
    if isinstance(exc, (ExtractionFailedError, AssistantUnavailableError)):
        return "provider_error"
    if "ratelimit" in lname or "rate limit" in text or "429" in text:
        return "rate_limited"
    if "timeout" in lname or "timeout" in text:
        return "timeout"
    if "context" in text and any(k in text for k in ("too long", "maximum", "exceed", "too many tokens")):
        return "context_overflow"
    if isinstance(exc, (ValueError, TypeError)) or "validation" in lname:
        return "validation_failed"
    if any(tok in name for tok in ("API", "HTTP", "Connection", "Provider")):
        return "provider_error"
    return "unknown"
