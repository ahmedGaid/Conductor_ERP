"""Event-bus subscribers — the decoupled link from Sales to e-invoicing.

When Sales publishes ``OrderInvoiced`` (enriched with the invoice's business data), e-invoicing
records a draft ETA invoice. Sales has no knowledge of this module; the only coupling is the public
event name + payload. Subscriber failures are isolated by the bus (they never break invoicing).
"""
from __future__ import annotations

import datetime as dt

from erp.core.events import bus
from erp.sales.events import ORDER_INVOICED

from .services import EInvoiceInput, record_invoice


def _on_order_invoiced(event) -> None:
    p = event.payload
    if not p.get("invoice"):
        return
    issue_date = p.get("date")
    if isinstance(issue_date, str):
        issue_date = dt.date.fromisoformat(issue_date)
    record_invoice(EInvoiceInput(
        invoice_number=p["invoice"],
        order_number=p.get("order", ""),
        customer_code=p.get("customer_code", ""),
        customer_name=p.get("customer_name", ""),
        issue_date=issue_date or dt.date.today(),
        currency=p.get("currency", "EGP"),
        tax_code=p.get("tax_code", ""),
        net_minor=p.get("net_minor", 0),
        tax_minor=p.get("tax_minor", 0),
        total_minor=p.get("total_minor", 0),
    ))


def register() -> None:
    bus.subscribe(ORDER_INVOICED, _on_order_invoiced)
