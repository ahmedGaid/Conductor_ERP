"""E-invoicing error catalog (EIN-NNN)."""
from __future__ import annotations

from erp.core.errors import AppError


class InvalidEInvoiceTransitionError(AppError):
    code = "EIN-001"
    status_code = 422
    message = "Invalid e-invoice status transition"


class UnknownEInvoiceError(AppError):
    code = "EIN-002"
    status_code = 404
    message = "E-invoice not found"
