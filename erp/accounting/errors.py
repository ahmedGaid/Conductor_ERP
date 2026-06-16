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


class InvalidAssetError(AppError):
    code = "ACC-007"
    status_code = 422
    message = "Fixed asset is invalid (cost, salvage and useful life must be sensible)"


class AssetStateError(AppError):
    code = "ACC-008"
    status_code = 409
    message = "Fixed asset is not in a state that allows this action"


class UnknownCostCenterError(AppError):
    code = "ACC-009"
    status_code = 422
    message = "Journal line references an unknown or inactive cost center"


class NotACashAccountError(AppError):
    code = "ACC-010"
    status_code = 422
    message = "Bank reconciliation requires a cash/bank account"


class BankMatchError(AppError):
    code = "ACC-011"
    status_code = 422
    message = "Cannot match this statement line to that ledger line"


class NotReconciledError(AppError):
    code = "ACC-012"
    status_code = 422
    message = "Statement does not tie out to the cash ledger yet"


class InvalidBudgetError(AppError):
    code = "ACC-013"
    status_code = 422
    message = "Budget is invalid (unknown fiscal year or account)"
