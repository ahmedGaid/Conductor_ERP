"""Accounting error catalog (ACC-NNN). Each is a catalogued, privacy-safe AppError."""
from __future__ import annotations

from erp.core.errors import AppError


class UnbalancedEntryError(AppError):
    code = "ACC-001"
    status_code = 422
    message = "Journal entry is not balanced (total debits must equal total credits)"


class InvalidLineError(AppError):
    code = "ACC-002"
    status_code = 422
    message = "Journal line is invalid"


class ClosedPeriodError(AppError):
    code = "ACC-003"
    status_code = 422
    message = "Cannot post to a closed accounting period"


class NonPostableAccountError(AppError):
    code = "ACC-004"
    status_code = 422
    message = "Account is not postable (group/inactive account)"


class AlreadyPostedError(AppError):
    code = "ACC-005"
    status_code = 409
    message = "Journal entry is already posted"


class NoPeriodError(AppError):
    code = "ACC-006"
    status_code = 422
    message = "No accounting period contains the entry date"
