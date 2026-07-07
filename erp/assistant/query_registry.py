"""Bounded structured-query registry — the assistant's ``query_data`` escape hatch (session 08 E).

The hand-written tool catalog (``tools.py``) answers the ~20 questions someone built a tool for;
this is the "ask anything about the data" fallback. It is **not** free-text-to-SQL (DECISIONS.md
still bans that): the model never writes SQL and never names a raw column. It fills a fixed grammar —
pick a whitelisted **entity**, optional **filters**, **group_by**, and one **aggregate** (``list``
returns the rows themselves, projected through the entity's whitelisted columns) — and the
server validates every part against this registry before touching the ORM. Only the entities, fields,
columns, and metrics listed here are reachable; anything off-registry is refused with the same calm
sentence as any other tool.

Enforcement mirrors the catalog: each entity carries its *view* permission, the query is gated on it
(``has_permission`` → calm refusal), and record-scoped entities additionally run through
``scope_queryset`` **as the actor**, so branch/own scope holds exactly as it does on the module's own
list endpoint. There is no ``eval``, no string-built SQL, no field outside the registry — the grammar
*is* the safety boundary.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from django.db.models import Avg, Count, Max, Min, Q, Sum

from erp.accounting.domain.models import Account, JournalEntry
from erp.crm.domain.models import Campaign, Lead, Opportunity, Ticket
from erp.einvoice.domain.models import ETAInvoice
from erp.identity import access
from erp.identity.scoping import scope_queryset
from erp.inventory.domain.models import Item, StockBalance, StockMovement, Warehouse
from erp.purchasing.domain.models import PurchaseOrder, PurchaseRequest, Supplier
from erp.sales.domain.models import Customer, Quotation, SalesOrder


def _egp(minor: int | None) -> str:
    """Integer minor units → a human EGP string (money formats at the edge — matches tools.py)."""
    return f"{(minor or 0) / 100:,.2f} EGP"


# --- calm, blame-free refusals (never a stack trace, never "invalid") ----------------------------

_DENIED = "This information is outside what your role can access."
_OFF_REGISTRY = "I can't look up that kind of record yet."
_BAD_FIELD = "I can't work with those records by that field."
_BAD_OP = "That kind of comparison isn't supported for that field."
_BAD_METRIC = "I can't total that field."
_BAD_VALUE = "I couldn't read that filter value."


class _Refused(Exception):
    """Raised inside filter building; carries the calm sentence to hand back to the model."""


# --- grammar primitives --------------------------------------------------------------------------

# op name -> the Django lookup suffix it maps to (never string-built SQL).
_LOOKUP = {"eq": "", "gt": "__gt", "lt": "__lt", "gte": "__gte", "lte": "__lte",
           "contains": "__icontains", "between": "__range"}
_ORDER_OPS = {"gt", "lt", "gte", "lte", "between"}  # need an orderable (non-bool) field
_AGG = {"count": Count, "sum": Sum, "avg": Avg, "min": Min, "max": Max}


@dataclass(frozen=True)
class _Field:
    """A filterable field: its ORM path plus a type used only to coerce the model's text value."""
    path: str
    type: str  # "str" | "int" | "decimal" | "date" | "bool"


@dataclass(frozen=True)
class _Group:
    """A group-by dimension. ``cite_type``/``label_path`` make grouped rows click-through records."""
    path: str
    cite_type: str | None = None
    label_path: str | None = None


@dataclass(frozen=True)
class _Metric:
    """An aggregatable numeric field. ``money`` marks minor-unit money for edge formatting."""
    path: str
    money: bool = False


@dataclass(frozen=True)
class _Column:
    """A list-mode column: its ORM path; ``money`` marks minor-unit money for edge formatting."""
    path: str
    money: bool = False


@dataclass(frozen=True)
class _Cite:
    """How a listed row becomes a click-through citation — only types the client can render
    (see ``AskCitation`` in ``apps/web/src/api/assistant.ts``); entities without one cite nothing."""
    type: str
    path: str
    label_path: str | None = None


@dataclass(frozen=True)
class _Entity:
    model: type
    permission: str
    scoped: bool          # record-scoped (run scope_queryset) vs company-wide (gate only)
    label: str            # human name for the router grammar
    filters: dict = field(default_factory=dict)
    groups: dict = field(default_factory=dict)
    metrics: dict = field(default_factory=dict)
    columns: dict = field(default_factory=dict)  # display name → _Column (the list-mode projection)
    order: tuple = ("-created_at",)              # default list ordering (newest first)
    cite: _Cite | None = None


# --- the allow-list: only what is listed here is ever reachable ----------------------------------

REGISTRY: dict[str, _Entity] = {
    "item": _Entity(
        Item, "inventory.item.view", scoped=False, label="stock items",
        filters={"type": _Field("type", "str"), "uom": _Field("uom", "str"),
                 "is_active": _Field("is_active", "bool"),
                 "category": _Field("category__name", "str"),
                 "sku": _Field("sku", "str"), "name": _Field("name", "str")},
        groups={"type": _Group("type"), "uom": _Group("uom"),
                "is_active": _Group("is_active"), "category": _Group("category__name")},
        metrics={},
        columns={"sku": _Column("sku"), "name": _Column("name"), "type": _Column("type"),
                 "uom": _Column("uom"), "category": _Column("category__name"),
                 "is_active": _Column("is_active")},
        order=("sku",), cite=_Cite("item", "sku", "name"),
    ),
    "customer": _Entity(
        Customer, "sales.customer.view", scoped=True, label="customers",
        filters={"is_active": _Field("is_active", "bool"),
                 "code": _Field("code", "str"), "name": _Field("name", "str")},
        groups={"is_active": _Group("is_active")},
        metrics={},
        columns={"code": _Column("code"), "name": _Column("name"),
                 "is_active": _Column("is_active"),
                 "credit_limit": _Column("credit_limit_minor", money=True)},
        order=("code",), cite=_Cite("customer", "code", "name"),
    ),
    "sales_order": _Entity(
        SalesOrder, "sales.order.view", scoped=True, label="sales orders",
        filters={"status": _Field("status", "str"), "order_date": _Field("order_date", "date"),
                 "customer_code": _Field("customer__code", "str"),
                 "customer_name": _Field("customer__name", "str"),
                 "number": _Field("number", "str")},
        groups={"status": _Group("status"),
                "customer": _Group("customer__code", "customer", "customer__name")},
        metrics={"subtotal": _Metric("subtotal_minor", money=True),
                 "invoiced": _Metric("invoiced_minor", money=True),
                 "paid": _Metric("paid_minor", money=True)},
        columns={"number": _Column("number"), "customer": _Column("customer__name"),
                 "status": _Column("status"), "order_date": _Column("order_date"),
                 "subtotal": _Column("subtotal_minor", money=True),
                 "invoiced": _Column("invoiced_minor", money=True),
                 "paid": _Column("paid_minor", money=True)},
        order=("-order_date", "-created_at"), cite=_Cite("order", "id", "number"),
    ),
    "purchase_order": _Entity(
        PurchaseOrder, "purchasing.order.view", scoped=True, label="purchase orders",
        filters={"status": _Field("status", "str"), "order_date": _Field("order_date", "date"),
                 "supplier_code": _Field("supplier__code", "str"),
                 "supplier_name": _Field("supplier__name", "str"),
                 "number": _Field("number", "str")},
        groups={"status": _Group("status"),
                "supplier": _Group("supplier__code", "supplier", "supplier__name")},
        metrics={"subtotal": _Metric("subtotal_minor", money=True),
                 "billed": _Metric("billed_minor", money=True),
                 "paid": _Metric("paid_minor", money=True)},
        columns={"number": _Column("number"), "supplier": _Column("supplier__name"),
                 "status": _Column("status"), "order_date": _Column("order_date"),
                 "subtotal": _Column("subtotal_minor", money=True),
                 "billed": _Column("billed_minor", money=True),
                 "paid": _Column("paid_minor", money=True)},
        order=("-order_date", "-created_at"), cite=_Cite("purchaseOrder", "number"),
    ),
    "supplier": _Entity(
        Supplier, "purchasing.order.view", scoped=True, label="suppliers",
        filters={"is_active": _Field("is_active", "bool"),
                 "code": _Field("code", "str"), "name": _Field("name", "str")},
        groups={"is_active": _Group("is_active")},
        metrics={},
        columns={"code": _Column("code"), "name": _Column("name"),
                 "is_active": _Column("is_active")},
        order=("code",), cite=_Cite("supplier", "code", "name"),
    ),
    "journal": _Entity(
        JournalEntry, "accounting.journal.view", scoped=True, label="journal entries",
        filters={"status": _Field("status", "str"), "date": _Field("date", "date"),
                 "source": _Field("source", "str"), "party_type": _Field("party_type", "str"),
                 "party_code": _Field("party_code", "str"), "number": _Field("number", "str")},
        groups={"status": _Group("status"), "source": _Group("source"),
                "party_type": _Group("party_type")},
        metrics={},
        columns={"number": _Column("number"), "date": _Column("date"),
                 "status": _Column("status"), "source": _Column("source"),
                 "party_type": _Column("party_type"), "party_code": _Column("party_code")},
        order=("-date", "-created_at"), cite=_Cite("journal", "number"),
    ),
    # --- list-mode expansion (query-data-list-mode plan, 2026-07-07) -----------------------------
    "quotation": _Entity(
        Quotation, "sales.quotation.view", scoped=True, label="quotations",
        filters={"status": _Field("status", "str"), "quote_date": _Field("quote_date", "date"),
                 "customer_code": _Field("customer__code", "str"),
                 "customer_name": _Field("customer__name", "str"),
                 "number": _Field("number", "str")},
        groups={"status": _Group("status"),
                "customer": _Group("customer__code", "customer", "customer__name")},
        metrics={"subtotal": _Metric("subtotal_minor", money=True)},
        columns={"number": _Column("number"), "customer": _Column("customer__name"),
                 "status": _Column("status"), "quote_date": _Column("quote_date"),
                 "subtotal": _Column("subtotal_minor", money=True)},
        order=("-quote_date", "-created_at"),
    ),
    "purchase_request": _Entity(
        PurchaseRequest, "purchasing.request.view", scoped=True, label="purchase requests",
        filters={"status": _Field("status", "str"), "request_date": _Field("request_date", "date"),
                 "supplier_code": _Field("supplier__code", "str"),
                 "supplier_name": _Field("supplier__name", "str"),
                 "number": _Field("number", "str")},
        groups={"status": _Group("status"),
                "supplier": _Group("supplier__code", "supplier", "supplier__name")},
        metrics={"subtotal": _Metric("subtotal_minor", money=True)},
        columns={"number": _Column("number"), "supplier": _Column("supplier__name"),
                 "status": _Column("status"), "request_date": _Column("request_date"),
                 "subtotal": _Column("subtotal_minor", money=True)},
        order=("-request_date", "-created_at"),
    ),
    "warehouse": _Entity(
        Warehouse, "inventory.warehouse.view", scoped=False, label="warehouses",
        filters={"is_active": _Field("is_active", "bool"),
                 "code": _Field("code", "str"), "name": _Field("name", "str")},
        groups={"is_active": _Group("is_active")},
        metrics={},
        columns={"code": _Column("code"), "name": _Column("name"),
                 "is_active": _Column("is_active")},
        order=("code",),
    ),
    "stock_movement": _Entity(
        StockMovement, "inventory.stock_movement.view", scoped=True, label="stock movements",
        filters={"type": _Field("type", "str"), "date": _Field("date", "date"),
                 "item_sku": _Field("item__sku", "str"), "item_name": _Field("item__name", "str"),
                 "warehouse": _Field("warehouse__code", "str"),
                 "reference": _Field("reference", "str"), "batch_no": _Field("batch_no", "str")},
        groups={"type": _Group("type"), "warehouse": _Group("warehouse__code"),
                "item": _Group("item__sku", "item", "item__name")},
        metrics={"value": _Metric("value_minor", money=True), "quantity": _Metric("quantity")},
        columns={"date": _Column("date"), "type": _Column("type"),
                 "item": _Column("item__sku"), "item_name": _Column("item__name"),
                 "warehouse": _Column("warehouse__code"), "quantity": _Column("quantity"),
                 "value": _Column("value_minor", money=True), "reference": _Column("reference")},
        order=("-date", "-created_at"), cite=_Cite("item", "item__sku", "item__name"),
    ),
    # On-hand balances have no branch stamp (plain running totals per item+warehouse), so the
    # entity is company-wide and gates on the same view permission as its items.
    "stock_balance": _Entity(
        StockBalance, "inventory.item.view", scoped=False, label="stock on hand",
        filters={"item_sku": _Field("item__sku", "str"), "item_name": _Field("item__name", "str"),
                 "warehouse": _Field("warehouse__code", "str"),
                 "quantity": _Field("quantity", "decimal")},
        groups={"warehouse": _Group("warehouse__code"),
                "item": _Group("item__sku", "item", "item__name")},
        metrics={"value": _Metric("value_minor", money=True), "quantity": _Metric("quantity")},
        columns={"item": _Column("item__sku"), "item_name": _Column("item__name"),
                 "warehouse": _Column("warehouse__code"), "quantity": _Column("quantity"),
                 "value": _Column("value_minor", money=True)},
        order=("item__sku",), cite=_Cite("item", "item__sku", "item__name"),
    ),
    "lead": _Entity(
        Lead, "crm.lead.view", scoped=True, label="leads",
        filters={"status": _Field("status", "str"), "source": _Field("source", "str"),
                 "name": _Field("name", "str"), "company": _Field("company", "str"),
                 "owner": _Field("owner", "str"), "campaign": _Field("campaign_code", "str"),
                 "code": _Field("code", "str")},
        groups={"status": _Group("status"), "source": _Group("source")},
        metrics={},
        columns={"code": _Column("code"), "name": _Column("name"), "company": _Column("company"),
                 "status": _Column("status"), "source": _Column("source"),
                 "owner": _Column("owner")},
    ),
    "opportunity": _Entity(
        Opportunity, "crm.opportunity.view", scoped=True, label="sales opportunities",
        filters={"stage": _Field("stage", "str"), "name": _Field("name", "str"),
                 "customer_code": _Field("customer_code", "str"),
                 "expected_close": _Field("expected_close", "date"),
                 "campaign": _Field("campaign_code", "str"), "number": _Field("number", "str")},
        groups={"stage": _Group("stage")},
        metrics={"amount": _Metric("amount_minor", money=True)},
        columns={"number": _Column("number"), "name": _Column("name"),
                 "stage": _Column("stage"), "amount": _Column("amount_minor", money=True),
                 "probability": _Column("probability"),
                 "expected_close": _Column("expected_close"),
                 "customer_code": _Column("customer_code")},
    ),
    "ticket": _Entity(
        Ticket, "crm.ticket.view", scoped=True, label="support tickets",
        filters={"status": _Field("status", "str"), "priority": _Field("priority", "str"),
                 "subject": _Field("subject", "str"), "customer_code": _Field("customer_code", "str"),
                 "owner": _Field("owner", "str"), "number": _Field("number", "str")},
        groups={"status": _Group("status"), "priority": _Group("priority")},
        metrics={},
        columns={"number": _Column("number"), "subject": _Column("subject"),
                 "priority": _Column("priority"), "status": _Column("status"),
                 "customer_code": _Column("customer_code"), "owner": _Column("owner")},
        order=("-opened_at",),
    ),
    "campaign": _Entity(
        Campaign, "crm.campaign.view", scoped=True, label="marketing campaigns",
        filters={"status": _Field("status", "str"), "channel": _Field("channel", "str"),
                 "name": _Field("name", "str"), "code": _Field("code", "str")},
        groups={"status": _Group("status"), "channel": _Group("channel")},
        metrics={"cost": _Metric("cost_minor", money=True)},
        columns={"code": _Column("code"), "name": _Column("name"),
                 "channel": _Column("channel"), "status": _Column("status"),
                 "start_date": _Column("start_date"), "end_date": _Column("end_date"),
                 "cost": _Column("cost_minor", money=True)},
    ),
    # Chart-of-accounts nodes are org-wide reference data (masters), like the module's own list.
    "account": _Entity(
        Account, "accounting.account.view", scoped=False, label="GL accounts",
        filters={"type": _Field("type", "str"), "is_active": _Field("is_active", "bool"),
                 "is_postable": _Field("is_postable", "bool"), "is_cash": _Field("is_cash", "bool"),
                 "code": _Field("code", "str"), "name": _Field("name", "str")},
        groups={"type": _Group("type"), "is_active": _Group("is_active")},
        metrics={},
        columns={"code": _Column("code"), "name": _Column("name"), "type": _Column("type"),
                 "is_postable": _Column("is_postable"), "is_active": _Column("is_active")},
        order=("code",),
    ),
    "einvoice": _Entity(
        ETAInvoice, "einvoice.invoice.view", scoped=True, label="e-invoices (ETA)",
        filters={"status": _Field("status", "str"), "issue_date": _Field("issue_date", "date"),
                 "customer_code": _Field("customer_code", "str"),
                 "customer_name": _Field("customer_name", "str"),
                 "invoice_number": _Field("invoice_number", "str")},
        groups={"status": _Group("status")},
        metrics={"total": _Metric("total_minor", money=True),
                 "net": _Metric("net_minor", money=True), "tax": _Metric("tax_minor", money=True)},
        columns={"invoice_number": _Column("invoice_number"),
                 "customer_name": _Column("customer_name"), "status": _Column("status"),
                 "issue_date": _Column("issue_date"),
                 "total": _Column("total_minor", money=True)},
        order=("-issue_date", "-created_at"),
    ),
}


def _coerce(ftype: str, raw) -> object:
    """Text value from the model → a typed Python value. Raises ValueError on garbage (→ calm error)."""
    s = str(raw).strip()
    if ftype == "int":
        return int(s)
    if ftype == "decimal":
        try:
            return Decimal(s)
        except InvalidOperation as exc:
            raise ValueError(str(exc)) from exc
    if ftype == "date":
        return datetime.date.fromisoformat(s)
    if ftype == "bool":
        return s.lower() in ("1", "true", "yes")
    return s


def _build_filters(spec: _Entity, filters: list) -> Q | None:
    """Validate each {field, op, value} against the registry and AND them into a single Q.

    Every failure raises ``_Refused`` with a calm sentence — an unknown field, an op the field's type
    can't take, or an unparseable value never reaches the ORM.
    """
    q: Q | None = None
    for raw_filter in filters:
        if not isinstance(raw_filter, dict):
            raise _Refused(_BAD_FIELD)
        name = str(raw_filter.get("field", "")).strip()
        op = str(raw_filter.get("op", "")).strip().lower()
        value = raw_filter.get("value")

        fld = spec.filters.get(name)
        if fld is None:
            raise _Refused(_BAD_FIELD)
        if op not in _LOOKUP:
            raise _Refused(_BAD_OP)
        if op == "contains" and fld.type != "str":
            raise _Refused(_BAD_OP)
        if op in _ORDER_OPS and fld.type == "bool":
            raise _Refused(_BAD_OP)

        try:
            if op == "between":
                parts = str(value).split(",")
                if len(parts) != 2:
                    raise ValueError("between needs two values")
                coerced = [_coerce(fld.type, parts[0]), _coerce(fld.type, parts[1])]
            else:
                coerced = _coerce(fld.type, value)
        except (ValueError, TypeError) as exc:
            raise _Refused(_BAD_VALUE) from exc

        cond = Q(**{fld.path + _LOOKUP[op]: coerced})
        q = cond if q is None else (q & cond)
    return q


def run_query(actor, *, entity: str = None, filters: list = None, group_by: list = None,
              aggregate: str = None, metric: str = None, limit: int = 20) -> dict:
    """Run one validated structured query as ``actor``. Returns data, or ``{"error": <calm>}``.

    Read-only. The entity, every filter field, every group-by field and the metric are all checked
    against ``REGISTRY`` before the ORM is touched; the permission is enforced first, and scoped
    entities run through ``scope_queryset`` so branch/own scope holds. ``aggregate="list"`` (also
    the default when neither aggregate nor group_by is given — "show me…" means rows, not a count)
    returns the actual rows, projected through the entity's whitelisted columns.
    """
    spec = REGISTRY.get((entity or "").strip())
    if spec is None:
        return {"error": _OFF_REGISTRY}
    if not access.has_permission(actor, spec.permission):
        return {"error": _DENIED}

    qs = spec.model.objects.all()
    if spec.scoped:
        qs = scope_queryset(actor, qs, spec.permission)

    try:
        where = _build_filters(spec, filters or [])
    except _Refused as exc:
        return {"error": str(exc)}
    if where is not None:
        qs = qs.filter(where)

    groups = [g for g in (group_by or []) if g][:2]  # 0–2 dimensions
    for name in groups:
        if name not in spec.groups:
            return {"error": _BAD_FIELD}

    limit = max(1, min(int(limit or 20), 50))

    agg = (aggregate or "").strip().lower()
    if agg == "list" or (not agg and not groups):
        return _listed(spec, qs, limit)
    if agg not in _AGG:
        agg = "count"
    if agg == "count":
        agg_expr, money = Count("id"), False
    else:
        mspec = spec.metrics.get((metric or "").strip())
        if mspec is None:
            return {"error": _BAD_METRIC}
        agg_expr, money = _AGG[agg](mspec.path), mspec.money

    if groups:
        return _grouped(spec, qs, groups, agg, agg_expr, money, metric, limit)
    total = (qs.aggregate(value=agg_expr).get("value")) or 0
    out = {"entity": entity, "aggregate": agg, "metric": (metric if agg != "count" else None),
           "value": _egp(total) if money else total, "citations": []}
    if money:
        out["value_minor"] = total
    return out


def _plain(value):
    """ORM value → JSON-safe primitive (results ride through ``json.dumps`` in the planner loop):
    dates → ISO strings, Decimal quantities → trimmed strings. Money never reaches here raw —
    money columns format through ``_egp`` with a ``*_minor`` twin."""
    if isinstance(value, datetime.datetime):
        return value.isoformat(sep=" ", timespec="minutes")
    if isinstance(value, datetime.date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return f"{value.normalize():f}"
    return value


def _listed(spec, qs, limit) -> dict:
    """List branch: the actual rows, projected through the entity's whitelisted columns only,
    in the entity's default order. Money formats at the edge (``_egp`` + ``*_minor`` twin) and each
    row becomes a click-through citation when the client can render its record type."""
    value_paths = [c.path for c in spec.columns.values()]
    if spec.cite is not None:
        value_paths.append(spec.cite.path)
        if spec.cite.label_path:
            value_paths.append(spec.cite.label_path)
    total = qs.count()
    raw_rows = list(qs.order_by(*spec.order).values(*dict.fromkeys(value_paths))[:limit])

    rows: list[dict] = []
    citations: list[dict] = []
    for r in raw_rows:
        row: dict = {}
        for name, col in spec.columns.items():
            if col.money:
                row[name] = _egp(r[col.path])
                row[name + "_minor"] = r[col.path]
            else:
                row[name] = _plain(r[col.path])
        rows.append(row)
        if spec.cite is not None:
            val = r[spec.cite.path]
            if val not in (None, ""):
                label = r.get(spec.cite.label_path) if spec.cite.label_path else None
                citations.append({"type": spec.cite.type, "value": str(val),
                                  "label": label or str(val)})
    return {"entity": spec.label, "mode": "list", "total_matching": total,
            "rows": rows, "citations": citations}


def _grouped(spec, qs, groups, agg, agg_expr, money, metric, limit) -> dict:
    """Group-by branch: ``.values(dims).annotate(value=agg)`` ordered by the aggregate, then format
    money and build click-through citations for a dimension that maps to real records."""
    value_paths: list[str] = []
    for name in groups:
        g = spec.groups[name]
        value_paths.append(g.path)
        if g.label_path:
            value_paths.append(g.label_path)
    # dict.fromkeys de-dupes while preserving order (a label may equal another dim's path).
    raw_rows = list(qs.values(*dict.fromkeys(value_paths)).annotate(value=agg_expr)
                    .order_by("-value")[:limit])

    cite_group = next((spec.groups[n] for n in groups if spec.groups[n].cite_type), None)
    rows: list[dict] = []
    citations: list[dict] = []
    for r in raw_rows:
        row = {name: r[spec.groups[name].path] for name in groups}
        row["value"] = _egp(r["value"]) if money else r["value"]
        if money:
            row["value_minor"] = r["value"]
        rows.append(row)
        if cite_group is not None:
            val = r[cite_group.path]
            if val not in (None, ""):
                label = r.get(cite_group.label_path) if cite_group.label_path else None
                citations.append({"type": cite_group.cite_type, "value": val,
                                  "label": label or str(val)})
    return {"entity": spec.label, "aggregate": agg, "group_by": groups,
            "metric": (metric if agg != "count" else None), "rows": rows, "citations": citations}


def query_grammar_text() -> str:
    """Compact description of the queryable entities + their fields, for the router prompt so the
    model knows what it may pass to ``query_data`` (kept stable and small; one line per entity)."""
    lines: list[str] = []
    for name, spec in REGISTRY.items():
        totals = ", ".join(spec.metrics) or "none (count only)"
        lines.append(
            f"- {name} ({spec.label}): filter by {', '.join(spec.filters)}; "
            f"group by {', '.join(spec.groups)}; totals {totals}; "
            f"list columns {', '.join(spec.columns)}"
        )
    return "\n".join(lines)
