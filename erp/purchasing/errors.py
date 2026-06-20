"""Purchasing error catalog (PUR-NNN)."""
from __future__ import annotations

from erp.core.errors import AppError


class InvalidTransitionError(AppError):
    code = "PUR-001"
    status_code = 422
    message = "Invalid purchase order status transition"


class ThreeWayMatchError(AppError):
    code = "PUR-002"
    status_code = 422
    message = "3-way match failed: received quantity does not match the order"


class EmptyOrderError(AppError):
    code = "PUR-003"
    status_code = 422
    message = "A purchase order needs at least one line"


class UnknownItemError(AppError):
    code = "PUR-004"
    status_code = 422
    message = "Order line references an unknown or non-stock item"


class OverpaymentError(AppError):
    code = "PUR-005"
    status_code = 422
    message = "Payment exceeds the outstanding balance"


class NothingToReturnError(AppError):
    code = "PUR-006"
    status_code = 422
    message = "A return needs at least one line with a positive quantity"


class ExcessiveReturnError(AppError):
    code = "PUR-007"
    status_code = 422
    message = "Cannot return more than was received and not already returned"


class ExcessiveReceiptError(AppError):
    code = "PUR-008"
    status_code = 422
    message = "Cannot receive more than the outstanding ordered quantity"


class ApprovalRequiredError(AppError):
    code = "PUR-009"
    status_code = 422
    message = "This order exceeds the approval threshold and must be approved before confirmation"


class RequestInvalidTransitionError(AppError):
    code = "PUR-010"
    status_code = 422
    message = "Invalid purchase request status transition"


class EmptyRequestError(AppError):
    code = "PUR-011"
    status_code = 422
    message = "A purchase request needs at least one line"


class RequestAlreadyConvertedError(AppError):
    code = "PUR-012"
    status_code = 422
    message = "This purchase request has already been converted to an order"


class UnknownTaxCodeError(AppError):
    code = "PUR-013"
    status_code = 422
    message = "Order references an unknown tax code"


class ApprovalLimitExceededError(AppError):
    code = "PUR-014"
    status_code = 422
    message = "This amount exceeds your approval limit for this document"
