"""Public contract for the purchasing module — PO lifecycle services + event names."""
from __future__ import annotations

import datetime
from dataclasses import dataclass

from django.db.models import Count, Q, Sum

from erp.identity.scoping import scope_queryset

from ..domain.models import PurchaseOrder, PurchaseRequest, Supplier
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
from ..services.requests import (
    RequestLineInput,
    approve_request,
)
from ..services.requests import (
    convert_request as _convert_request,
)
from ..services.requests import (
    create_request as _create_request,
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


def _next_supplier_code() -> str:
    """Auto-generate the next free ``S-000NN`` code (used when a caller creates a supplier by name
    only). Numeric max of the ``S-<digits>`` codes — not string order, which mis-ranks mixed-width
    codes like ``S-9003`` above ``S-10000`` — then steps past any code already taken (a prior
    auto-gen, or the same number in a different width)."""
    codes = list(Supplier.objects.filter(code__startswith="S-").values_list("code", flat=True))
    taken = set(codes)
    seq = max((int(c[2:]) for c in codes if c[2:].isdigit()), default=0) + 1
    while f"S-{seq:05d}" in taken:
        seq += 1
    return f"S-{seq:05d}"


def create_supplier(*, name: str, code: str = "", actor=None) -> SupplierInfo:
    """Create a supplier by business key (code auto-assigned when omitted). Code-based, no ORM leak."""
    code = (code or "").strip() or _next_supplier_code()
    supplier = Supplier.objects.create(
        code=code, name=name,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
    )
    return SupplierInfo(code=supplier.code, name=supplier.name, is_active=supplier.is_active)


def supplier_name_exists(name: str) -> bool:
    """True when a supplier with this exact name already exists (import duplicate check). Suppliers
    are company-wide (``list_suppliers`` is unscoped), so this is not actor-narrowed."""
    return Supplier.objects.filter(name__iexact=(name or "").strip()).exists()


def place_request(*, supplier_code: str, warehouse_code: str, lines: list[RequestLineInput],
                  request_date=None, currency: str = "EGP", notes: str = "", actor=None):
    """Create a draft purchase request for a supplier referenced by **code**.

    Returns the created request, or ``None`` when the supplier code is unknown — the caller decides
    how to surface a missing supplier (mirrors ``sales.place_order``).
    """
    supplier = _suppliers.by_code(supplier_code)
    if supplier is None:
        return None
    return _create_request(
        supplier=supplier, warehouse_code=warehouse_code, lines=lines,
        request_date=request_date, currency=currency, notes=notes, actor=actor,
    )


def place_order(*, supplier_code: str, warehouse_code: str, lines: list[POLineInput],
                order_date=None, currency: str = "EGP", notes: str = "", tax_code: str = "",
                actor=None) -> PurchaseOrder | None:
    """Create a DRAFT purchase order for a supplier referenced by **code**. ``None`` if unknown
    (mirrors ``place_request``)."""
    supplier = _suppliers.by_code(supplier_code)
    if supplier is None:
        return None
    return create_order(
        supplier=supplier, warehouse_code=warehouse_code, lines=lines,
        order_date=order_date, currency=currency, notes=notes, tax_code=tax_code, actor=actor,
    )


def convert_purchase_request(number: str, actor=None) -> PurchaseOrder | None:
    """Turn an approved purchase request (referenced by **number**) into a DRAFT purchase order.
    ``None`` if the request no longer exists; raises the usual purchasing errors (not approved,
    already converted) — mirrors ``sales.convert_quotation``."""
    req = PurchaseRequest.objects.filter(number=number).first()
    if req is None:
        return None
    return _convert_request(req, actor=actor)


# --- scoped read helpers for the AI assistant (session 08 tool catalog) -------------------------
# Same shape as the sales read helpers: plain dicts, minor units, narrowed to what ``actor`` may see
# via ``scope_queryset`` — the assistant calls these AS the current user, so branch/own scope holds.
# "Open" = a PO that still owes work or money (not yet paid/returned/cancelled).
_OPEN_STATUSES = ("draft", "confirmed", "partially_received", "received", "billed")


def _scoped_orders(actor):
    return scope_queryset(actor, PurchaseOrder.objects.all(), "purchasing.order.view")


def _scoped_requests(actor):
    return scope_queryset(actor, PurchaseRequest.objects.all(), "purchasing.request.view")


def find_requests(actor, *, query: str, limit: int = 8) -> list[dict]:
    """Find purchase requests by number or supplier — scoped to the actor, most recent first.
    Carries lines + status so the assistant's convert action can build a proposal without a second
    lookup (mirrors ``sales.find_quotations``)."""
    q = (query or "").strip()
    qs = _scoped_requests(actor).select_related("supplier")
    if q:
        qs = qs.filter(
            Q(number__icontains=q) | Q(supplier__name__icontains=q) | Q(supplier__code__icontains=q)
        )
    return [
        {"id": str(r.id), "number": r.number, "supplier_code": r.supplier.code,
         "supplier_name": r.supplier.name, "status": r.status, "subtotal_minor": r.subtotal_minor,
         "converted_order_number": r.converted_order_number,
         "lines": [
             {"item_sku": ln.item_sku, "description": ln.description, "quantity": str(ln.quantity),
              "unit_cost_minor": ln.unit_cost_minor}
             for ln in r.lines.all().order_by("line_no")
         ]}
        for r in qs.order_by("-request_date", "-created_at")[: max(1, min(limit, 20))]
    ]


def find_orders(actor, *, query: str, limit: int = 8) -> list[dict]:
    """Find purchase orders by number or supplier — scoped to the actor, most recent first.
    Carries lines + status so posting actions (receive/bill/pay) can build a proposal without a
    second lookup (mirrors find_requests)."""
    q = (query or "").strip()
    qs = _scoped_orders(actor).select_related("supplier")
    if q:
        qs = qs.filter(
            Q(number__icontains=q) | Q(supplier__name__icontains=q) | Q(supplier__code__icontains=q)
        )
    return [
        {"id": str(o.id), "number": o.number, "supplier_code": o.supplier.code,
         "supplier_name": o.supplier.name, "status": o.status,
         "subtotal_minor": o.subtotal_minor, "received_minor": o.received_minor,
         "billed_minor": o.billed_minor, "paid_minor": o.paid_minor,
         "outstanding_minor": o.outstanding_minor,
         "lines": [
             {"line_no": ln.line_no, "item_sku": ln.item_sku, "quantity": str(ln.quantity),
              "received_qty": str(ln.received_qty), "unit_cost_minor": ln.unit_cost_minor}
             for ln in o.lines.all().order_by("line_no")
         ]}
        for o in qs.order_by("-order_date")[: max(1, min(limit, 20))]
    ]


def get_order(actor, order_id) -> PurchaseOrder | None:
    """One purchase order (the ORM record) scoped to the actor — the loader a gated assistant
    posting action uses to re-resolve a proposal's payload before writing (mirrors
    ``accounting.get_journal_entry``). Deliberately does NOT prefetch ``lines``: ``receive_order``
    mutates each line then re-reads the plain ``order.lines.all()`` expecting the fresh rows, and a
    primed prefetch cache would hand it the pre-receipt snapshot instead. ``None`` if out of scope
    or gone."""
    return _scoped_orders(actor).filter(id=order_id).first()


def get_request(actor, request_id) -> PurchaseRequest | None:
    """One purchase request (the ORM record) scoped to the actor — the loader a gated assistant
    posting action uses to re-resolve a proposal's payload before writing (mirrors ``get_order``).
    ``None`` if out of scope or gone."""
    return _scoped_requests(actor).filter(id=request_id).first()


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
    "create_supplier",
    "supplier_name_exists",
    "place_request",
    "RequestLineInput",
    "find_requests",
    "get_request",
    "approve_request",
    "convert_purchase_request",
    "open_purchase_orders",
    "supplier_balances",
    "purchase_summary",
    "find_orders",
    "get_order",
    "POLineInput",
    "create_order",
    "place_order",
    "confirm_order",
    "receive_order",
    "bill_order",
    "pay_order",
    "PO_CONFIRMED",
    "PO_RECEIVED",
    "PO_BILLED",
    "PO_PAID",
]
