"""Event-bus subscribers — the decoupled link that turns domain events into notifications.

Sales publishes ``OrderInvoiced`` and CRM publishes ``TicketEscalated``; this module subscribes to
those event **names** and dispatches a notification through the appropriate channel adapter. Neither
Sales nor CRM knows notifications exist — the only coupling is the public event name + payload, and
the bus isolates any failure here from the publisher.
"""
from __future__ import annotations

from erp.core.events import bus
from erp.crm.events import TICKET_ESCALATED
from erp.sales.events import ORDER_INVOICED

from .domain.models import NotificationChannel
from .services import dispatch


def _on_order_invoiced(event) -> None:
    p = event.payload
    if not p.get("invoice"):
        return
    name = p.get("customer_name") or p.get("customer_code") or "customer"
    code = p.get("customer_code") or "customer"
    dispatch(
        channel=NotificationChannel.EMAIL,
        recipient=f"{code}@customer.conductor.local",
        subject=f"Invoice {p['invoice']}",
        body=f"Dear {name}, your invoice {p['invoice']} has been issued.",
        reference=str(p["invoice"]),
        event_name=ORDER_INVOICED,
    )


def _on_ticket_escalated(event) -> None:
    p = event.payload
    if not p.get("ticket"):
        return
    customer = p.get("customer") or "support"
    dispatch(
        channel=NotificationChannel.WHATSAPP,
        recipient=str(customer),
        subject=f"Ticket {p['ticket']} escalated",
        body=f"Support ticket {p['ticket']} breached its SLA and was escalated to "
             f"{p.get('priority', 'higher')} priority.",
        reference=str(p["ticket"]),
        event_name=TICKET_ESCALATED,
    )


def register() -> None:
    bus.subscribe(ORDER_INVOICED, _on_order_invoiced)
    bus.subscribe(TICKET_ESCALATED, _on_ticket_escalated)
