"""Error identification system + base application error.

Every error gets a stable Error Code (catalog entry, e.g. ``WF-001``) and a unique runtime
Error ID (``ERR-YYYY-NNNNNN``) so a customer can report a failure and remote support can
diagnose it without ever seeing business data (privacy-safe diagnostics).
"""
from __future__ import annotations

import datetime as _dt
import itertools

_counter = itertools.count(1)


def new_error_id() -> str:
    """Runtime identifier for a single error occurrence (not persisted across restarts)."""
    year = _dt.datetime.now(tz=_dt.timezone.utc).year
    return f"ERR-{year}-{next(_counter):06d}"


class AppError(Exception):
    """Base for all known, catalogued application errors.

    Subclasses set ``code`` (catalog key) and optionally an HTTP ``status_code``.
    """

    code: str = "GEN-000"
    status_code: int = 400
    message: str = "Application error"

    def __init__(self, message: str | None = None, *, data: dict | None = None) -> None:
        self.message = message or self.message
        self.data = data or {}
        self.error_id = new_error_id()
        super().__init__(self.message)

    def to_dict(self) -> dict:
        return {
            "error_id": self.error_id,
            "code": self.code,
            "message": self.message,
            "data": self.data,
        }


class ValidationError(AppError):
    code = "GEN-001"
    status_code = 400
    message = "Validation failed"


class NotFoundError(AppError):
    code = "GEN-002"
    status_code = 404
    message = "Resource not found"


class ConflictError(AppError):
    code = "GEN-003"
    status_code = 409
    message = "Conflict"


class PermissionError(AppError):  # noqa: A001 - intentional domain name
    code = "GEN-004"
    status_code = 403
    message = "Permission denied"
