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
