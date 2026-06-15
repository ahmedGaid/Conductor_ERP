"""Public contract for the sales module — order lifecycle services + event names.

Other modules (e.g. CRM, when an opportunity is won) drive sales through this contract using
business keys (customer code, SKU strings) only — never sales ORM instances.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..events import ORDER_CONFIRMED, ORDER_DELIVERED, ORDER_INVOICED, PAYMENT_RECEIVED
from ..repositories import customers as _customers
from ..services.orders import (
    OrderLineInput,
    confirm_order,
    create_order,
    deliver_order,
    invoice_order,
    receive_payment,
)


@dataclass(frozen=True)
class CustomerInfo:
    code: str
    name: str
    is_active: bool


def find_customer(code: str) -> CustomerInfo | None:
    """Look up a customer by code without exposing the sales ORM."""
    customer = _customers.by_code(code)
    if customer is None:
        return None
    return CustomerInfo(code=customer.code, name=customer.name, is_active=customer.is_active)


def place_order(
    *, customer_code: str, warehouse_code: str, lines: list[OrderLineInput],
    order_date=None, currency: str = "EGP", notes: str = "", actor=None,
):
    """Create a sales order for a customer referenced by **code**.

    Returns the created order, or ``None`` if the customer code is unknown — the caller decides how
    to handle a missing customer (CRM, for instance, wins the opportunity without an order).
    """
    customer = _customers.by_code(customer_code)
    if customer is None:
        return None
    return create_order(
        customer=customer, warehouse_code=warehouse_code, lines=lines,
        order_date=order_date, currency=currency, notes=notes, actor=actor,
    )


__all__ = [
    "OrderLineInput",
    "CustomerInfo",
    "find_customer",
    "place_order",
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
