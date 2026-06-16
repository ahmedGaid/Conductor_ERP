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


class NothingToReturnError(AppError):
    code = "SAL-006"
    status_code = 422
    message = "A return needs at least one line with a positive quantity"


class ExcessiveReturnError(AppError):
    code = "SAL-007"
    status_code = 422
    message = "Cannot return more than was delivered and not already returned"


class ExcessiveDeliveryError(AppError):
    code = "SAL-008"
    status_code = 422
    message = "Cannot deliver more than the outstanding ordered quantity"


class ApprovalRequiredError(AppError):
    code = "SAL-009"
    status_code = 422
    message = "This order exceeds the approval threshold and must be approved before confirmation"


class InvalidDiscountError(AppError):
    code = "SAL-013"
    status_code = 422
    message = "A line discount cannot be negative or exceed the line's gross amount"


class UnknownTaxCodeError(AppError):
    code = "SAL-014"
    status_code = 422
    message = "The order references an unknown or inactive tax code"


class QuotationInvalidTransitionError(AppError):
    code = "SAL-010"
    status_code = 422
    message = "Invalid quotation status transition"


class EmptyQuotationError(AppError):
    code = "SAL-011"
    status_code = 422
    message = "A quotation needs at least one line"


class QuotationAlreadyConvertedError(AppError):
    code = "SAL-012"
    status_code = 422
    message = "This quotation has already been converted to an order"
