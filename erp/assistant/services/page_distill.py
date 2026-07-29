"""Page-context distillation (ai-reliability T3.8): a compact typed snapshot of the record the
user is currently viewing — status, key amounts, counts, open issues — instead of the bare
"They are viewing X Y" line context.py rendered before this.

Table-driven: ``DISTILLERS`` maps a page-context "type" string (the frontend's
``${module}.${entity}`` from ``collectContext()``) to a function ``(actor, record_id) ->
list[str] | None`` returning a handful of short fact fragments. Unregistered types, a record not
found, or any lookup error all return ``None`` — the caller (``context.py::_page_block``) then
falls back to the plain record line only, so an unmapped or broken page never regresses or crashes
the envelope build (fail-open, same discipline as ``services/rerank.py``).

Every distiller calls into its module's ``contracts`` — never a raw ORM import here — so the same
RBAC/data-scope enforcement the module's own tools use holds for the assistant too.
"""
from __future__ import annotations

import logging
from collections.abc import Callable

from erp.accounting import contracts as accounting
from erp.crm import contracts as crm
from erp.inventory import contracts as inventory
from erp.purchasing import contracts as purchasing
from erp.sales import contracts as sales

logger = logging.getLogger(__name__)

# Distillers are capped in prose length, not tokenized here — envelope.py's Section/degrade_fn
# already enforces the real token budget on the whole `page` section; this is just a sanity bound
# on any one record's contribution (Accept: target <= 150 tokens per record).
_MAX_FACTS = 5


def _egp(minor: int | None) -> str:
    """Integer minor units -> a human EGP string with Western digits (money formats at the edge —
    same convention as ``tools.py::_egp``)."""
    return f"{(minor or 0) / 100:,.2f} EGP"


def _distill_sales_orders(actor, record_id: str) -> list[str] | None:
    order = sales.get_order(actor, record_id)
    if order is None:
        return None
    facts = [f"status {order.get_status_display().lower()}", f"total {_egp(order.subtotal_minor)}"]
    if order.invoiced_minor:
        facts.append(f"invoiced {_egp(order.invoiced_minor)}")
    outstanding = order.invoiced_minor - order.paid_minor
    if outstanding > 0:
        facts.append(f"outstanding {_egp(outstanding)}")
    return facts


def _distill_sales_quotations(actor, record_id: str) -> list[str] | None:
    quote = sales.get_quotation(actor, record_id)
    if quote is None:
        return None
    facts = [f"status {quote.get_status_display().lower()}", f"total {_egp(quote.subtotal_minor)}"]
    if quote.validity_until:
        facts.append(f"valid until {quote.validity_until}")
    return facts


def _distill_sales_customers(actor, record_id: str) -> list[str] | None:
    profile = sales.customer_profile(actor, query=record_id)
    if profile.get("customer") is None:
        return None
    facts = [f"{profile['order_count']} orders"]
    if profile["outstanding_minor"] > 0:
        facts.append(f"outstanding {_egp(profile['outstanding_minor'])}")
    return facts


def _distill_purchasing_orders(actor, record_id: str) -> list[str] | None:
    order = purchasing.get_order(actor, record_id)
    if order is None:
        return None
    facts = [f"status {order.get_status_display().lower()}", f"total {_egp(order.subtotal_minor)}"]
    if order.outstanding_minor > 0:
        facts.append(f"outstanding {_egp(order.outstanding_minor)}")
    return facts


def _distill_purchasing_requests(actor, record_id: str) -> list[str] | None:
    request = purchasing.get_request(actor, record_id)
    if request is None:
        return None
    return [f"status {request.get_status_display().lower()}", f"total {_egp(request.subtotal_minor)}"]


def _distill_purchasing_suppliers(actor, record_id: str) -> list[str] | None:
    supplier = purchasing.find_supplier(record_id)
    if supplier is None:
        return None
    facts = [] if supplier.is_active else ["inactive"]
    open_orders = purchasing.open_purchase_orders(actor, supplier=record_id)
    if open_orders:
        outstanding = sum(o["outstanding_minor"] for o in open_orders)
        facts.append(f"{len(open_orders)} open orders")
        if outstanding > 0:
            facts.append(f"outstanding {_egp(outstanding)}")
    return facts or ["no open orders"]


def _distill_inventory_items(actor, record_id: str) -> list[str] | None:
    item = inventory.find_item(record_id)
    if item is None:
        return None
    facts = [item.type] if item.is_active else [item.type, "inactive"]
    onhand = inventory.stock_on_hand(query=record_id)
    rows = onhand.get("rows") or []
    if rows:
        total_qty = sum(float(r["quantity"]) for r in rows)
        facts.append(f"{total_qty:g} on hand")
        if any(r["below_reorder"] for r in rows):
            facts.append("below reorder point")
    return facts


def _distill_accounting_journals(actor, record_id: str) -> list[str] | None:
    entry = accounting.get_journal_entry(actor, record_id)
    if entry is None:
        return None
    lines = list(entry.lines.all())
    total_debit = sum(ln.debit for ln in lines)
    return [f"status {entry.get_status_display().lower()}", f"total {_egp(total_debit)}",
            f"{len(lines)} lines"]


def _distill_crm_opportunities(actor, record_id: str) -> list[str] | None:
    opp = crm.get_opportunity(actor, record_id)
    if opp is None:
        return None
    facts = [f"stage {opp.stage}", f"amount {_egp(opp.amount_minor)}"]
    if opp.expected_close:
        facts.append(f"expected close {opp.expected_close}")
    return facts


DISTILLERS: dict[str, Callable[..., list[str] | None]] = {
    "sales.orders": _distill_sales_orders,
    "sales.quotations": _distill_sales_quotations,
    "sales.customers": _distill_sales_customers,
    "purchasing.orders": _distill_purchasing_orders,
    "purchasing.requests": _distill_purchasing_requests,
    "purchasing.suppliers": _distill_purchasing_suppliers,
    "inventory.items": _distill_inventory_items,
    "accounting.journals": _distill_accounting_journals,
    "crm.opportunities": _distill_crm_opportunities,
}


def render(actor, record_type: str | None, record_id: str | None) -> str | None:
    """The distilled snapshot for one page record, as a single semicolon-joined fragment ready to
    append to the page block's record line — or ``None`` when the type isn't registered, the
    record can't be found, or the lookup itself errors (fail-open: the caller keeps today's plain
    record line either way)."""
    if not record_type or not record_id:
        return None
    fn = DISTILLERS.get(record_type)
    if fn is None:
        return None
    try:
        facts = fn(actor, record_id)
    except Exception:
        logger.exception("page_distill: %s lookup failed — falling back to the plain record line",
                         record_type)
        return None
    if not facts:
        return None
    return "; ".join(facts[:_MAX_FACTS])
