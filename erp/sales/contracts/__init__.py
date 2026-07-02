"""Public contract for the sales module — order lifecycle services + event names.

Other modules (e.g. CRM, when an opportunity is won) drive sales through this contract using
business keys (customer code, SKU strings) only — never sales ORM instances.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass

from django.db.models import Count, Q, Sum

from erp.identity.scoping import scope_queryset

from ..domain.models import SalesOrder
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


# --- scoped read helpers for the AI assistant (session 02 part 2) ------------------------------
# Each returns plain dicts and is narrowed to what ``actor`` may see via ``scope_queryset`` — the
# same enforcement every sales list endpoint uses. The assistant calls these AS the current user,
# so branch/own scope holds without the assistant ever touching the sales ORM directly.

def _scoped_orders(actor):
    return scope_queryset(actor, SalesOrder.objects.all(), "sales.order.view")


def _period_range(period: str) -> tuple[datetime.date, datetime.date, str]:
    today = datetime.date.today()
    if period == "last_month":
        first_this = today.replace(day=1)
        last_prev = first_this - datetime.timedelta(days=1)
        start = last_prev.replace(day=1)
        return start, last_prev, start.strftime("%Y-%m")
    if period == "this_year":
        return today.replace(month=1, day=1), today, str(today.year)
    # default: this_month
    return today.replace(day=1), today, today.strftime("%Y-%m")


def sales_summary(actor, *, period: str = "this_month") -> dict:
    """Net sales value + order count for a period, scoped to the actor."""
    start, end, label = _period_range(period)
    qs = _scoped_orders(actor).filter(order_date__gte=start, order_date__lte=end).exclude(status="cancelled")
    agg = qs.aggregate(total=Sum("subtotal_minor"), n=Count("id"))
    return {
        "period": period, "period_label": label,
        "total_minor": agg["total"] or 0, "order_count": agg["n"] or 0, "currency": "EGP",
    }


def top_customers(actor, *, limit: int = 5) -> list[dict]:
    """Customers by net sales value, best first — scoped to the actor."""
    rows = (
        _scoped_orders(actor).exclude(status="cancelled")
        .values("customer__code", "customer__name")
        .annotate(total=Sum("subtotal_minor")).order_by("-total")[: max(1, min(limit, 20))]
    )
    return [
        {"code": r["customer__code"], "name": r["customer__name"], "total_minor": r["total"] or 0}
        for r in rows
    ]


def overdue_receivables(actor, *, limit: int = 10) -> dict:
    """Customers who still owe money (invoiced > paid), largest first — scoped to the actor."""
    rows = (
        _scoped_orders(actor)
        .values("customer__code", "customer__name")
        .annotate(inv=Sum("invoiced_minor"), paid=Sum("paid_minor"))
    )
    owing = [
        {"code": r["customer__code"], "name": r["customer__name"],
         "outstanding_minor": (r["inv"] or 0) - (r["paid"] or 0)}
        for r in rows
    ]
    owing = sorted((o for o in owing if o["outstanding_minor"] > 0),
                   key=lambda o: -o["outstanding_minor"])
    return {
        "total_outstanding_minor": sum(o["outstanding_minor"] for o in owing),
        "customers": owing[: max(1, min(limit, 25))],
    }


def find_orders(actor, *, query: str, limit: int = 8) -> list[dict]:
    """Find sales orders by number or customer — scoped to the actor."""
    q = (query or "").strip()
    qs = _scoped_orders(actor).select_related("customer")
    if q:
        qs = qs.filter(
            Q(number__icontains=q) | Q(customer__name__icontains=q) | Q(customer__code__icontains=q)
        )
    return [
        {"id": str(o.id), "number": o.number, "customer_name": o.customer.name,
         "status": o.status, "order_date": str(o.order_date), "total_minor": o.subtotal_minor}
        for o in qs.order_by("-order_date")[: max(1, min(limit, 20))]
    ]


__all__ = [
    "OrderLineInput",
    "CustomerInfo",
    "find_customer",
    "sales_summary",
    "top_customers",
    "overdue_receivables",
    "find_orders",
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
