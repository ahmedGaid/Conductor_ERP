"""Arabic/English display names for triggerable events and their condition fields.

The event bus and WEBHOOK_EVENT_CATALOG deal in raw names (e.g. "purchasing.RequestSubmitted");
this module is the only place those names are mapped to what a non-technical user actually
sees. Nothing outside erp/workflow (and the API views that expose these maps) should render a
raw event name or payload field key to an end user — see spec Section 6.
"""
from __future__ import annotations

from erp.purchasing.events import PR_SUBMITTED, PO_APPROVED
from erp.sales.events import ORDER_CONFIRMED

TRIGGER_DISPLAY: dict[str, dict[str, str]] = {
    PR_SUBMITTED: {"ar": "عند إرسال طلب شراء", "en": "When a purchase request is submitted"},
    PO_APPROVED: {"ar": "عند الموافقة على أمر شراء", "en": "When a purchase order is approved"},
    ORDER_CONFIRMED: {"ar": "عند تأكيد طلب بيع", "en": "When a sales order is confirmed"},
}

TRIGGER_FIELDS: dict[str, list[dict]] = {
    PR_SUBMITTED: [
        {"field": "amount_minor", "label": {"ar": "الإجمالي", "en": "Total amount"}},
    ],
    PO_APPROVED: [
        {"field": "amount_minor", "label": {"ar": "الإجمالي", "en": "Total amount"}},
    ],
    ORDER_CONFIRMED: [
        {"field": "amount_minor", "label": {"ar": "الإجمالي", "en": "Total amount"}},
    ],
}
