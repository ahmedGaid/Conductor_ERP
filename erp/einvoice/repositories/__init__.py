"""Data-access boundary for e-invoicing."""
from __future__ import annotations

from erp.core.repository import Repository

from ..domain.models import ETAInvoice


class ETAInvoiceRepository(Repository[ETAInvoice]):
    model = ETAInvoice

    def by_invoice(self, invoice_number: str) -> ETAInvoice | None:
        return self.model._default_manager.filter(invoice_number=invoice_number).first()


invoices = ETAInvoiceRepository()
