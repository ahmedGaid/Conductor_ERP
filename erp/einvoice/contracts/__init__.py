"""Public contract for the e-invoicing module.

E-invoicing is driven by the ``sales.OrderInvoiced`` event (see handlers.py), so other modules
rarely call it directly. This surface exposes the record entry point + event names for any caller
that wants to record/submit an invoice explicitly.
"""
from __future__ import annotations

from ..events import (
    EINVOICE_RECORDED,
    EINVOICE_REJECTED,
    EINVOICE_SUBMITTED,
    EINVOICE_VALIDATED,
)
from ..services.issue import EInvoiceInput, poll_invoice, record_invoice, submit_invoice

__all__ = [
    "EInvoiceInput",
    "record_invoice",
    "submit_invoice",
    "poll_invoice",
    "EINVOICE_RECORDED",
    "EINVOICE_SUBMITTED",
    "EINVOICE_VALIDATED",
    "EINVOICE_REJECTED",
]
