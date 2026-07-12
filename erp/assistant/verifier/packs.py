"""The six invariant packs (os-foundations FILE_02).

Each pack is a pure read-only function ``(scope) -> Finding``. Money comparisons are integer
minor-unit equality — never float, never Decimal tolerance. A pack handed a scope without the record
kind it checks returns ``ok=True`` "not applicable" (a sales-order confirm shouldn't fail
``journal_balanced``). Records are resolved from the scope's ``links`` (and, for stock, ``payload``).
"""
from __future__ import annotations

from django.db.models import Q, Sum

from erp.accounting.domain.models import JournalEntry
from erp.accounting.repositories import PeriodRepository
from erp.accounting.services import reports
from erp.inventory.domain.models import StockBalance, StockTransfer
from erp.sales.domain.models import SalesOrder

from . import Finding, pack

# link ``type`` -> (model, number-field) for the document-numbering pack. Only documents with a
# per-year ``_next_number`` sequence qualify; stock transfers carry a derived code, not a sequence.
_SEQ_MODELS = {
    "order": (SalesOrder, "number"),
    "journalEntry": (JournalEntry, "number"),
}


def _link_values(scope: dict, *types: str) -> list:
    """The ``value`` of every scope link whose ``type`` is one of ``types``."""
    return [ln.get("value") for ln in (scope.get("links") or ()) if ln.get("type") in types]


def _na(name: str) -> Finding:
    return Finding(name, True, "Not applicable to this action.", {"applicable": False})


@pack("trial_balance")
def trial_balance(scope: dict) -> Finding:
    """Whole-system: total posted debits == total posted credits (one aggregate query)."""
    tb = reports.trial_balance()
    ok = tb.total_debit == tb.total_credit
    return Finding(
        "trial_balance", ok,
        "The books balance: debits equal credits." if ok
        else "The books are out of balance: total debits and credits differ.",
        {"total_debit": tb.total_debit, "total_credit": tb.total_credit},
    )


@pack("journal_balanced")
def journal_balanced(scope: dict) -> Finding:
    """The touched journal entry's debit sum equals its credit sum."""
    ids = _link_values(scope, "journalEntry")
    if not ids:
        return _na("journal_balanced")
    entries = list(JournalEntry.objects.filter(id__in=ids))
    if not entries:
        return _na("journal_balanced")
    for entry in entries:
        agg = entry.lines.aggregate(debit=Sum("debit"), credit=Sum("credit"))
        debit, credit = agg["debit"] or 0, agg["credit"] or 0
        if debit != credit:
            return Finding("journal_balanced", False,
                           f"Journal entry {entry.number} does not balance.",
                           {"entry": entry.number, "debit": debit, "credit": credit})
    return Finding("journal_balanced", True, "The journal entry balances.",
                   {"entries": [e.number for e in entries]})


@pack("period_open")
def period_open(scope: dict) -> Finding:
    """The touched document's date falls in an open fiscal period."""
    dated: list[tuple[str, object]] = []
    for entry in JournalEntry.objects.filter(id__in=_link_values(scope, "journalEntry")):
        dated.append((entry.number, entry.date))
    for order in SalesOrder.objects.filter(id__in=_link_values(scope, "order")):
        dated.append((order.number, order.order_date))
    if not dated:
        return _na("period_open")
    repo = PeriodRepository()
    for label, on_date in dated:
        period = repo.containing(on_date)
        if period is None:
            return Finding("period_open", False,
                           f"{label} has no accounting period for its date.",
                           {"document": label, "date": str(on_date)})
        if not period.is_open:
            return Finding("period_open", False,
                           f"{label} falls in a closed period ({period.code}).",
                           {"document": label, "period": period.code, "date": str(on_date)})
    return Finding("period_open", True, "Every touched date falls in an open period.",
                   {"documents": [label for label, _ in dated]})


@pack("doc_totals")
def doc_totals(scope: dict) -> Finding:
    """The touched document's header total equals the sum of its line totals (minor units)."""
    ids = _link_values(scope, "order")
    if not ids:
        return _na("doc_totals")
    orders = list(SalesOrder.objects.filter(id__in=ids).prefetch_related("lines"))
    if not orders:
        return _na("doc_totals")
    for order in orders:
        line_sum = sum(ln.line_total_minor for ln in order.lines.all())
        if order.subtotal_minor != line_sum:
            return Finding("doc_totals", False,
                           f"Order {order.number}'s total does not match its lines.",
                           {"document": order.number, "header": order.subtotal_minor,
                            "lines": line_sum})
    return Finding("doc_totals", True, "Document totals match their lines.",
                   {"documents": [o.number for o in orders]})


@pack("stock_non_negative")
def stock_non_negative(scope: dict) -> Finding:
    """No StockBalance row for the touched item/warehouse goes below zero."""
    q = Q()
    touched = False
    for tid in _link_values(scope, "stockTransfer"):
        transfer = StockTransfer.objects.filter(id=tid).select_related(
            "item", "source", "destination").first()
        if transfer:
            touched = True
            q |= Q(item=transfer.item, warehouse__in=[transfer.source, transfer.destination])
    payload = scope.get("payload") or {}
    sku = payload.get("item_sku")
    if sku:
        touched = True
        codes = [c for c in (payload.get("source_code"), payload.get("destination_code"),
                             payload.get("warehouse")) if c]
        q |= Q(item__sku=sku, warehouse__code__in=codes) if codes else Q(item__sku=sku)
    if not touched:
        return _na("stock_non_negative")
    rows = list(StockBalance.objects.filter(q).select_related("item", "warehouse"))
    for row in rows:
        if row.quantity < 0:
            return Finding("stock_non_negative", False,
                           "An item's on-hand quantity is below zero.",
                           {"item": row.item.sku, "warehouse": row.warehouse.code,
                            "quantity": str(row.quantity)})
    return Finding("stock_non_negative", True, "No item goes below zero on hand.",
                   {"checked": len(rows)})


@pack("sequence_unbroken")
def sequence_unbroken(scope: dict) -> Finding:
    """The touched document's number sequence (per prefix, per year) has no gaps."""
    docs: list[tuple[type, str, str]] = []
    for ltype, (model, field) in _SEQ_MODELS.items():
        for value in _link_values(scope, ltype):
            rec = model.objects.filter(pk=value).first()
            if rec:
                docs.append((model, field, getattr(rec, field)))
    if not docs:
        return _na("sequence_unbroken")
    for model, field, number in docs:
        head, sep, _ = number.rpartition("-")
        if not sep:
            continue  # no prefix to reason about
        prefix = head + "-"
        seqs = []
        for other in model.objects.filter(**{f"{field}__startswith": prefix}).values_list(
                field, flat=True):
            tail = other.rpartition("-")[2]
            if tail.isdigit():
                seqs.append(int(tail))
        if not seqs:
            continue
        missing = sorted(set(range(min(seqs), max(seqs) + 1)) - set(seqs))
        if missing:
            return Finding("sequence_unbroken", False,
                           f"The {prefix} numbering has a gap.",
                           {"prefix": prefix, "missing": missing[:10]})
    return Finding("sequence_unbroken", True, "Document numbering has no gaps.",
                   {"documents": [n for _, _, n in docs]})
