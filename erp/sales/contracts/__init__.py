"""Public contract for the sales module — order lifecycle services + event names.

Other modules (e.g. CRM, when an opportunity is won) drive sales through this contract using
business keys (customer code, SKU strings) only — never sales ORM instances.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass

from django.db.models import Count, Q, Sum

from erp.identity.scoping import scope_queryset

from ..domain.models import Customer, OrderStatus, Quotation, SalesOrder
from ..events import ORDER_CONFIRMED, ORDER_DELIVERED, ORDER_INVOICED, PAYMENT_RECEIVED
from ..repositories import customers as _customers
from ..services.orders import (
    OrderLineInput,
    confirm_order,
    create_order,
    deliver_order,
    invoice_order,
    receive_payment,
    update_order_lines,
)
from ..services.quotations import QuoteLineInput, create_quotation
from ..services.quotations import convert_quotation as _convert_quotation


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


def _next_customer_code() -> str:
    """Auto-generate the next free ``C-000NN`` code (used when a caller creates a customer by name
    only). Uses the NUMERIC max of the ``C-<digits>`` codes — not string order, which mis-ranks
    mixed-width codes like ``C-9003`` above ``C-10000`` — then steps past any code already taken (a
    prior auto-gen, or the same number in a different width, e.g. ``C-9003`` vs ``C-09003``)."""
    codes = list(Customer.objects.filter(code__startswith="C-").values_list("code", flat=True))
    taken = set(codes)
    seq = max((int(c[2:]) for c in codes if c[2:].isdigit()), default=0) + 1
    while f"C-{seq:05d}" in taken:
        seq += 1
    return f"C-{seq:05d}"


def create_customer(*, name: str, code: str = "", credit_limit_minor: int = 0, actor=None) -> CustomerInfo:
    """Create a customer by business key (code auto-assigned when omitted). Code-based, no ORM leak."""
    code = (code or "").strip() or _next_customer_code()
    customer = Customer.objects.create(
        code=code, name=name, credit_limit_minor=credit_limit_minor,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
    )
    return CustomerInfo(code=customer.code, name=customer.name, is_active=customer.is_active)


def customer_name_exists(actor, name: str) -> bool:
    """True when the actor can already see a customer with this exact name (import duplicate check).
    Scoped like every sales read, so a user only dedupes against customers in their own data scope."""
    return _scoped_customers(actor).filter(name__iexact=(name or "").strip()).exists()


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


def update_draft_order(*, order_number: str, lines: list[OrderLineInput], actor=None):
    """Replace a **draft** order's lines by order number. ``None`` if the order no longer exists —
    the caller decides how to handle a stale reference (mirrors ``place_order``)."""
    order = SalesOrder.objects.filter(number=order_number).first()
    if order is None:
        return None
    return update_order_lines(order, lines, actor=actor)


def place_quotation(
    *, customer_code: str, warehouse_code: str, lines: list[QuoteLineInput],
    quote_date=None, validity_until=None, currency: str = "EGP", notes: str = "", actor=None,
) -> Quotation | None:
    """Create a DRAFT quotation for a customer referenced by **code**. ``None`` if unknown."""
    customer = _customers.by_code(customer_code)
    if customer is None:
        return None
    return create_quotation(
        customer=customer, warehouse_code=warehouse_code, lines=lines,
        quote_date=quote_date, validity_until=validity_until, currency=currency, notes=notes, actor=actor,
    )


def convert_quotation(number: str, actor=None) -> SalesOrder | None:
    """Turn a quotation (referenced by **number**) into a sales order draft. ``None`` if the
    quotation no longer exists; raises the usual sales errors (not approved, already converted)."""
    quote = Quotation.objects.filter(number=number).first()
    if quote is None:
        return None
    return _convert_quotation(quote, actor=actor)


# --- scoped read helpers for the AI assistant (session 02 part 2) ------------------------------
# Each returns plain dicts and is narrowed to what ``actor`` may see via ``scope_queryset`` — the
# same enforcement every sales list endpoint uses. The assistant calls these AS the current user,
# so branch/own scope holds without the assistant ever touching the sales ORM directly.

def _scoped_orders(actor):
    return scope_queryset(actor, SalesOrder.objects.all(), "sales.order.view")


def get_order(actor, order_id) -> SalesOrder | None:
    """One sales order (the ORM record) scoped to the actor — mirrors
    ``purchasing.contracts.get_order``. Used by the assistant's page-context distiller (T3.8) to
    snapshot the record the user is viewing. ``None`` if out of scope or gone."""
    return _scoped_orders(actor).select_related("customer").filter(id=order_id).first()


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


def find_order(actor, *, query: str) -> dict | None:
    """One sales order's full detail (incl. lines) for the assistant's edit action — scoped, exact
    number match first, else the most recent number/customer match."""
    q = (query or "").strip()
    base = _scoped_orders(actor).select_related("customer")
    order = base.filter(number=q).first() or base.filter(
        Q(number__icontains=q) | Q(customer__name__icontains=q)
    ).order_by("-order_date").first()
    if order is None:
        return None
    return {
        "id": str(order.id), "number": order.number, "status": order.status,
        "customer_code": order.customer.code, "customer_name": order.customer.name,
        "warehouse_code": order.warehouse_code, "currency": order.currency,
        "lines": [
            {"item_sku": ln.item_sku, "description": ln.description, "quantity": str(ln.quantity),
             "unit_price_minor": ln.unit_price_minor}
            for ln in order.lines.all().order_by("line_no")
        ],
    }


def _scoped_quotations(actor):
    return scope_queryset(actor, Quotation.objects.all(), "sales.quotation.view")


def get_quotation(actor, quotation_id) -> Quotation | None:
    """One quotation (the ORM record) scoped to the actor — mirrors ``get_order``. Used by the
    assistant's page-context distiller (T3.8). ``None`` if out of scope or gone."""
    return _scoped_quotations(actor).select_related("customer").filter(id=quotation_id).first()


def find_quotations(actor, *, query: str, limit: int = 8) -> list[dict]:
    """Find quotations by number or customer — scoped to the actor, most recent first. Carries lines
    + status so the assistant's convert action can build a proposal without a second lookup."""
    q = (query or "").strip()
    qs = _scoped_quotations(actor).select_related("customer")
    if q:
        qs = qs.filter(
            Q(number__icontains=q) | Q(customer__name__icontains=q) | Q(customer__code__icontains=q)
        )
    return [
        {"id": str(o.id), "number": o.number, "customer_code": o.customer.code,
         "customer_name": o.customer.name, "status": o.status, "subtotal_minor": o.subtotal_minor,
         "converted_order_number": o.converted_order_number,
         "lines": [
             {"item_sku": ln.item_sku, "description": ln.description, "quantity": str(ln.quantity),
              "unit_price_minor": ln.unit_price_minor}
             for ln in o.lines.all().order_by("line_no")
         ]}
        for o in qs.order_by("-quote_date", "-created_at")[: max(1, min(limit, 20))]
    ]


def _scoped_customers(actor):
    return scope_queryset(actor, Customer.objects.all(), "sales.customer.view")


def find_customers(actor, *, query: str, limit: int = 10) -> list[dict]:
    """Find customers by code or name — scoped to the actor."""
    q = (query or "").strip()
    qs = _scoped_customers(actor)
    if q:
        qs = qs.filter(Q(code__icontains=q) | Q(name__icontains=q))
    return [{"code": c.code, "name": c.name, "is_active": c.is_active} for c in qs[: max(1, min(limit, 20))]]


def customer_profile(actor, *, query: str) -> dict:
    """One customer's snapshot: balance owed + recent orders — scoped to the actor.

    ``query`` matches a customer code exactly first, else the first name/code match. Both the
    customer and their orders run through the actor's scope, so a user who cannot see the customer
    gets an empty profile (the tool layer turns "no permission" into a calm refusal separately).
    """
    q = (query or "").strip()
    base = _scoped_customers(actor)
    customer = base.filter(code=q).first() or base.filter(
        Q(code__icontains=q) | Q(name__icontains=q)
    ).order_by("code").first()
    if customer is None:
        return {"customer": None}

    orders = _scoped_orders(actor).filter(customer=customer).exclude(status="cancelled")
    agg = orders.aggregate(inv=Sum("invoiced_minor"), paid=Sum("paid_minor"), n=Count("id"))
    recent = [
        {"id": str(o.id), "number": o.number, "status": o.status,
         "order_date": str(o.order_date), "total_minor": o.subtotal_minor}
        for o in orders.order_by("-order_date")[:5]
    ]
    return {
        "customer": {"code": customer.code, "name": customer.name},
        "order_count": agg["n"] or 0,
        "outstanding_minor": (agg["inv"] or 0) - (agg["paid"] or 0),
        "recent_orders": recent,
    }


def invoiced_order_count() -> int:
    """Company-wide count of orders that reached at least the Invoiced stage (never scoped —
    a company-wide milestone counter, not a per-user record view)."""
    return SalesOrder.objects.filter(
        status__in=(OrderStatus.INVOICED, OrderStatus.PAID)
    ).count()


__all__ = [
    "OrderLineInput",
    "CustomerInfo",
    "find_customer",
    "create_customer",
    "customer_name_exists",
    "sales_summary",
    "top_customers",
    "overdue_receivables",
    "find_orders",
    "find_order",
    "get_order",
    "get_quotation",
    "find_customers",
    "find_quotations",
    "customer_profile",
    "invoiced_order_count",
    "place_order",
    "update_draft_order",
    "create_order",
    "confirm_order",
    "deliver_order",
    "invoice_order",
    "receive_payment",
    "QuoteLineInput",
    "place_quotation",
    "convert_quotation",
    "ORDER_CONFIRMED",
    "ORDER_DELIVERED",
    "ORDER_INVOICED",
    "PAYMENT_RECEIVED",
]
