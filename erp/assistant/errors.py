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
