"""Public contract for the inventory module.

Other modules (Sales, Purchasing, ...) use these **code-based** helpers and react to the stock
events on the bus. They pass SKU / warehouse-code strings — never inventory ORM instances — so they
stay decoupled from inventory's internals.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..events import STOCK_ISSUED, STOCK_RECEIVED, STOCK_TRANSFERRED
from ..repositories import items as _items
from ..repositories import warehouses as _warehouses
from ..services.stock import (
    issue_stock,
    receive_stock,
    return_in_stock,
    return_out_stock,
    transfer_stock,
)
from ..errors import UnknownItemError, UnknownWarehouseError


@dataclass(frozen=True)
class ItemInfo:
    sku: str
    name: str
    type: str
    is_active: bool


def find_item(sku: str) -> ItemInfo | None:
    item = _items.by_sku(sku)
    if item is None:
        return None
    return ItemInfo(sku=item.sku, name=item.name, type=item.type, is_active=item.is_active)


def _resolve(sku: str, warehouse_code: str):
    item = _items.by_sku(sku)
    if item is None:
        raise UnknownItemError(data={"sku": sku})
    warehouse = _warehouses.by_code(warehouse_code)
    if warehouse is None:
        raise UnknownWarehouseError(data={"warehouse": warehouse_code})
    return item, warehouse


def issue(sku: str, warehouse_code: str, quantity, *, date=None, reference: str = "",
          memo: str = "", actor=None):
    """Issue stock by SKU + warehouse code (resolves internally). Posts COGS/Inventory."""
    item, warehouse = _resolve(sku, warehouse_code)
    return issue_stock(
        item=item, warehouse=warehouse, quantity=quantity, date=date,
        reference=reference, memo=memo, actor=actor,
    )


def receive(sku: str, warehouse_code: str, quantity, unit_cost_minor: int, *, date=None,
            reference: str = "", memo: str = "", actor=None):
    item, warehouse = _resolve(sku, warehouse_code)
    return receive_stock(
        item=item, warehouse=warehouse, quantity=quantity, unit_cost_minor=unit_cost_minor,
        date=date, reference=reference, memo=memo, actor=actor,
    )


def return_in(sku: str, warehouse_code: str, quantity, *, date=None, reference: str = "",
              memo: str = "", actor=None):
    """Customer return — stock back in at weighted-average cost. Posts Dr Inventory / Cr COGS."""
    item, warehouse = _resolve(sku, warehouse_code)
    return return_in_stock(
        item=item, warehouse=warehouse, quantity=quantity, date=date,
        reference=reference, memo=memo, actor=actor,
    )


def return_out(sku: str, warehouse_code: str, quantity, *, date=None, reference: str = "",
               memo: str = "", actor=None):
    """Supplier return — stock out at weighted-average cost. Posts Dr GRNI / Cr Inventory."""
    item, warehouse = _resolve(sku, warehouse_code)
    return return_out_stock(
        item=item, warehouse=warehouse, quantity=quantity, date=date,
        reference=reference, memo=memo, actor=actor,
    )


__all__ = [
    "ItemInfo",
    "find_item",
    "issue",
    "receive",
    "return_in",
    "return_out",
    # legacy instance-based services (used within tests/other inventory callers)
    "issue_stock",
    "receive_stock",
    "return_in_stock",
    "return_out_stock",
    "transfer_stock",
    "STOCK_RECEIVED",
    "STOCK_ISSUED",
    "STOCK_TRANSFERRED",
]
