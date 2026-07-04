"""Public contract for the purchasing module — PO lifecycle services + event names."""
from __future__ import annotations

import datetime
from dataclasses import dataclass

from django.db.models import Count, Q, Sum

from erp.identity.scoping import scope_queryset

from ..domain.models import PurchaseOrder
from ..events import PO_BILLED, PO_CONFIRMED, PO_PAID, PO_RECEIVED
from ..repositories import suppliers as _suppliers
from ..services.orders import (
    POLineInput,
    bill_order,
    confirm_order,
    create_order,
    pay_order,
    receive_order,
)


@dataclass(frozen=True)
class SupplierInfo:
    code: str
    name: str
    is_active: bool


def find_supplier(code: str) -> SupplierInfo | None:
    s = _suppliers.by_code(code)
    if s is None:
        return None
    return SupplierInfo(code=s.code, name=s.name, is_active=s.is_active)


def list_suppliers() -> list[SupplierInfo]:
    """Light snapshot of all active suppliers (for cross-module lookups/matching)."""
    return [
        SupplierInfo(code=s.code, name=s.name, is_active=s.is_active)
        for s in _suppliers.filter(is_active=True)
    ]


# --- scoped read helpers for the AI assistant (session 08 tool catalog) -------------------------
# Same shape as the sales read helpers: plain dicts, minor units, narrowed to what ``actor`` may see
# via ``scope_queryset`` — the assistant calls these AS the current user, so branch/own scope holds.
# "Open" = a PO that still owes work or money (not yet paid/returned/cancelled).
_OPEN_STATUSES = ("draft", "confirmed", "partially_received", "received", "billed")


def _scoped_orders(actor):
    return scope_queryset(actor, PurchaseOrder.objects.all(), "purchasing.order.view")


def _period_range(period: str) -> tuple[datetime.date, datetime.date, str]:
    today = datetime.date.today()
    if period == "last_month":
        first_this = today.replace(day=1)
        last_prev = first_this - datetime.timedelta(days=1)
        start = last_prev.replace(day=1)
        return start, last_prev, start.strftime("%Y-%m")
    if period == "this_year":
        return today.replace(month=1, day=1), today, str(today.year)
    return today.replace(day=1), today, today.strftime("%Y-%m")


def open_purchase_orders(actor, *, status: str | None = None, supplier: str | None = None,
                         limit: int = 20) -> list[dict]:
    """Purchase orders still in flight (or filtered to one status), scoped to the actor."""
    qs = _scoped_orders(actor).select_related("supplier")
    if status:
        qs = qs.filter(status=status)
    else:
        qs = qs.filter(status__in=_OPEN_STATUSES)
    if supplier:
        qs = qs.filter(Q(supplier__name__icontains=supplier) | Q(supplier__code__icontains=supplier))
    return [
        {"id": str(o.id), "number": o.number, "supplier_name": o.supplier.name,
         "status": o.status, "order_date": str(o.order_date),
         "subtotal_minor": o.subtotal_minor, "outstanding_minor": o.outstanding_minor}
        for o in qs.order_by("-order_date")[: max(1, min(limit, 20))]
    ]


def supplier_balances(actor, *, limit: int = 10) -> dict:
    """Suppliers we still owe (billed > paid), largest first — scoped to the actor."""
    rows = (
        _scoped_orders(actor)
        .values("supplier__code", "supplier__name")
        .annotate(billed=Sum("billed_minor"), paid=Sum("paid_minor"))
    )
    owing = [
        {"code": r["supplier__code"], "name": r["supplier__name"],
         "outstanding_minor": (r["billed"] or 0) - (r["paid"] or 0)}
        for r in rows
    ]
    owing = sorted((o for o in owing if o["outstanding_minor"] > 0),
                   key=lambda o: -o["outstanding_minor"])
    return {
        "total_outstanding_minor": sum(o["outstanding_minor"] for o in owing),
        "suppliers": owing[: max(1, min(limit, 25))],
    }


def purchase_summary(actor, *, period: str = "this_month") -> dict:
    """Purchase value + order count for a period, scoped to the actor."""
    start, end, label = _period_range(period)
    qs = (_scoped_orders(actor).filter(order_date__gte=start, order_date__lte=end)
          .exclude(status="cancelled"))
    agg = qs.aggregate(total=Sum("subtotal_minor"), n=Count("id"))
    return {
        "period": period, "period_label": label,
        "total_minor": agg["total"] or 0, "order_count": agg["n"] or 0, "currency": "EGP",
    }


__all__ = [
    "SupplierInfo",
    "find_supplier",
    "list_suppliers",
    "open_purchase_orders",
    "supplier_balances",
    "purchase_summary",
    "POLineInput",
    "create_order",
    "confirm_order",
    "receive_order",
    "bill_order",
    "pay_order",
    "PO_CONFIRMED",
    "PO_RECEIVED",
    "PO_BILLED",
    "PO_PAID",
]
