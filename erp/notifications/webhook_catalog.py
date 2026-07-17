"""Catalog of domain event names a webhook subscription may pick from.

Every event any module publishes on ``erp.core.events.bus`` is a candidate — webhooks observe, they
never emit. Names are the same strings each module's own ``events.py`` defines; kept together here
purely so the API can serve one list and a subscription's ``event_names`` can be validated against it.
"""
from __future__ import annotations

from erp.accounting.events import JOURNAL_POSTED, PERIOD_CLOSED
from erp.crm.events import (
    LEAD_CONVERTED,
    OPPORTUNITY_LOST,
    OPPORTUNITY_WON,
    TICKET_ESCALATED,
    TICKET_OPENED,
    TICKET_RESOLVED,
)
from erp.einvoice.events import (
    EINVOICE_RECORDED,
    EINVOICE_REJECTED,
    EINVOICE_SUBMITTED,
    EINVOICE_VALIDATED,
)
from erp.inventory.events import STOCK_ISSUED, STOCK_RECEIVED, STOCK_TRANSFERRED
from erp.purchasing.events import (
    PO_APPROVED,
    PO_BILLED,
    PO_CONFIRMED,
    PO_PAID,
    PO_RECEIVED,
    PO_RETURNED,
    PR_APPROVED,
    PR_CONVERTED,
    PR_REJECTED,
    PR_SUBMITTED,
)
from erp.sales.events import (
    ORDER_APPROVED,
    ORDER_CONFIRMED,
    ORDER_DELIVERED,
    ORDER_INVOICED,
    ORDER_RETURNED,
    PAYMENT_RECEIVED,
    QUOTATION_APPROVED,
    QUOTATION_CONVERTED,
    QUOTATION_REJECTED,
    QUOTATION_SUBMITTED,
)

WEBHOOK_EVENT_CATALOG: list[str] = sorted({
    JOURNAL_POSTED, PERIOD_CLOSED,
    LEAD_CONVERTED, OPPORTUNITY_WON, OPPORTUNITY_LOST,
    TICKET_OPENED, TICKET_RESOLVED, TICKET_ESCALATED,
    EINVOICE_RECORDED, EINVOICE_SUBMITTED, EINVOICE_VALIDATED, EINVOICE_REJECTED,
    STOCK_RECEIVED, STOCK_ISSUED, STOCK_TRANSFERRED,
    PO_APPROVED, PO_CONFIRMED, PO_RECEIVED, PO_BILLED, PO_PAID, PO_RETURNED,
    PR_SUBMITTED, PR_APPROVED, PR_REJECTED, PR_CONVERTED,
    ORDER_APPROVED, ORDER_CONFIRMED, ORDER_DELIVERED, ORDER_INVOICED, ORDER_RETURNED,
    PAYMENT_RECEIVED,
    QUOTATION_SUBMITTED, QUOTATION_APPROVED, QUOTATION_REJECTED, QUOTATION_CONVERTED,
})
