"""Public contract for the sales module — order lifecycle services + event names."""
from __future__ import annotations

from ..events import ORDER_CONFIRMED, ORDER_DELIVERED, ORDER_INVOICED, PAYMENT_RECEIVED
from ..services.orders import (
    OrderLineInput,
    confirm_order,
    create_order,
    deliver_order,
    invoice_order,
    receive_payment,
)

__all__ = [
    "OrderLineInput",
    "create_order",
    "confirm_order",
    "deliver_order",
    "invoice_order",
    "receive_payment",
    "ORDER_CONFIRMED",
    "ORDER_DELIVERED",
    "ORDER_INVOICED",
    "PAYMENT_RECEIVED",
]
