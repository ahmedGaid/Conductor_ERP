"""Sales error catalog (SAL-NNN)."""
from __future__ import annotations

from erp.core.errors import AppError


class InvalidTransitionError(AppError):
    code = "SAL-001"
    status_code = 422
    message = "Invalid sales order status transition"


class CreditLimitExceededError(AppError):
    code = "SAL-002"
    status_code = 422
    message = "Customer credit limit would be exceeded"


class EmptyOrderError(AppError):
    code = "SAL-003"
    status_code = 422
    message = "A sales order needs at least one line"


class UnknownItemError(AppError):
    code = "SAL-004"
    status_code = 422
    message = "Order line references an unknown or non-stock item"


class OverpaymentError(AppError):
    code = "SAL-005"
    status_code = 422
    message = "Payment exceeds the outstanding balance"
