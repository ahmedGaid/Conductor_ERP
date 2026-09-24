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


class LicenseCompanyMismatchError(AppError):
    code = "EIN-003"
    status_code = 403
    message = "This license was issued for a different company — e-invoice submission is refused"
