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
