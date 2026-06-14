"""Inventory reporting — on-hand balances and total valuation."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ..domain import costing
from ..domain.models import StockBalance


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
