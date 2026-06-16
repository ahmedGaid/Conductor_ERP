"""Inventory reporting — on-hand balances, total valuation, and batch/lot traceability."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Min, Sum

from ..domain import costing
from ..domain.models import MovementType, StockBalance, StockMovement


@dataclass
class BalanceRow:
    sku: str
    item_name: str
    warehouse_code: str
    quantity: str
    avg_cost_minor: int
    value_minor: int
    below_reorder: bool


@dataclass
class StockValuation:
    rows: list[BalanceRow]
    total_value_minor: int


def stock_on_hand(*, item_sku: str | None = None, warehouse_code: str | None = None) -> StockValuation:
    qs = StockBalance.objects.select_related("item", "warehouse").order_by(
        "item__sku", "warehouse__code"
    )
    if item_sku:
        qs = qs.filter(item__sku=item_sku)
    if warehouse_code:
        qs = qs.filter(warehouse__code=warehouse_code)

    rows: list[BalanceRow] = []
    total = 0
    for b in qs:
        qty = Decimal(b.quantity)
        rows.append(
            BalanceRow(
                sku=b.item.sku,
                item_name=b.item.name,
                warehouse_code=b.warehouse.code,
                quantity=str(qty),
                avg_cost_minor=costing.average_cost_minor(qty, b.value_minor),
                value_minor=b.value_minor,
                below_reorder=qty < Decimal(b.item.reorder_point),
            )
        )
        total += b.value_minor
    return StockValuation(rows=rows, total_value_minor=total)


@dataclass
class BatchRow:
    batch_no: str
    sku: str
    item_name: str
    warehouse_code: str
    received_quantity: str
    earliest_expiry: str | None


def batches(*, warehouse_code: str | None = None) -> list[BatchRow]:
    """Received batches/lots with their total received quantity and earliest expiry (traceability).

    Issues are weighted-average and not batch-allocated, so this is a receiving/expiry view rather than
    a consumed-balance ledger.
    """
    qs = StockMovement.objects.filter(type=MovementType.RECEIPT).exclude(batch_no="")
    if warehouse_code:
        qs = qs.filter(warehouse__code=warehouse_code)
    agg = (
        qs.values("batch_no", "item__sku", "item__name", "warehouse__code")
        .annotate(qty=Sum("quantity"), expiry=Min("expiry_date"))
        .order_by("expiry", "batch_no")
    )
    return [
        BatchRow(
            batch_no=r["batch_no"], sku=r["item__sku"], item_name=r["item__name"],
            warehouse_code=r["warehouse__code"], received_quantity=str(r["qty"] or Decimal("0")),
            earliest_expiry=str(r["expiry"]) if r["expiry"] else None,
        )
        for r in agg
    ]
