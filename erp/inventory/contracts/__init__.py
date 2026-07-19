"""Public contract for the inventory module.

Other modules (Sales, Purchasing, ...) use these **code-based** helpers and react to the stock
events on the bus. They pass SKU / warehouse-code strings — never inventory ORM instances — so they
stay decoupled from inventory's internals.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass

from django.db import models

from erp.audit import services as audit

from ..domain.models import StockMovement
from ..errors import UnknownItemError, UnknownWarehouseError
from ..events import STOCK_ISSUED, STOCK_RECEIVED, STOCK_TRANSFERRED
from ..repositories import items as _items
from ..repositories import warehouses as _warehouses
from ..services import reports as _reports
from ..services import stock_count as _stock_count
from ..services.stock import (
    create_transfer_draft,
    issue_stock,
    receive_stock,
    return_in_stock,
    return_out_stock,
    transfer_stock,
)


@dataclass(frozen=True)
class ItemInfo:
    sku: str
    name: str
    type: str
    is_active: bool
    reorder_point: str = "0"


def find_item(sku: str) -> ItemInfo | None:
    item = _items.by_sku(sku)
    if item is None:
        return None
    return ItemInfo(sku=item.sku, name=item.name, type=item.type, is_active=item.is_active,
                    reorder_point=str(item.reorder_point))


def list_items(item_type: str = "stock") -> list[ItemInfo]:
    """Light snapshot of active items of one type (for cross-module lookups/matching)."""
    return [
        ItemInfo(sku=i.sku, name=i.name, type=i.type, is_active=i.is_active,
                reorder_point=str(i.reorder_point))
        for i in _items.filter(type=item_type, is_active=True)
    ]


def create_item(*, sku: str, name: str, uom: str = "unit", reorder_point=0, actor=None) -> ItemInfo:
    """Create a stock item by SKU (its natural key). Code-based, no ORM leak — mirrors
    ``sales.create_customer`` / ``purchasing.create_supplier`` for the assistant's import path."""
    from ..domain.models import Item

    item = Item.objects.create(
        sku=(sku or "").strip(), name=name, uom=(uom or "unit").strip() or "unit",
        reorder_point=reorder_point or 0,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
    )
    return ItemInfo(sku=item.sku, name=item.name, type=item.type, is_active=item.is_active)


def item_sku_exists(sku: str) -> bool:
    """True when an item with this exact SKU already exists (import duplicate check)."""
    return _items.by_sku((sku or "").strip()) is not None


@dataclass(frozen=True)
class WarehouseInfo:
    code: str
    name: str
    is_active: bool


def find_warehouse(code: str) -> WarehouseInfo | None:
    """One warehouse by exact code (active or not) — lets callers tell 'missing' from 'inactive'."""
    wh = _warehouses.by_code((code or "").strip())
    if wh is None:
        return None
    return WarehouseInfo(code=wh.code, name=wh.name, is_active=wh.is_active)


def default_warehouse_code() -> str | None:
    """The first active warehouse's code — a sensible default when a caller omits one."""
    from ..domain.models import Warehouse

    wh = Warehouse.objects.filter(is_active=True).order_by("code").first()
    return wh.code if wh is not None else None


def low_stock(*, limit: int = 20) -> list[dict]:
    """Items whose on-hand quantity is at/below their reorder point (the AI assistant's read tool).

    Inventory balances are company-wide (not user-scoped), so this reads the on-hand report directly.
    """
    rows = [r for r in _reports.stock_on_hand().rows if r.below_reorder]
    return [
        {"sku": r.sku, "name": r.item_name, "warehouse_code": r.warehouse_code, "quantity": r.quantity}
        for r in rows[: max(1, min(limit, 50))]
    ]


def _match_sku(query: str) -> str | None:
    """Resolve a free-text query to a single SKU: exact SKU wins, else first name/SKU match."""
    q = (query or "").strip()
    if not q:
        return None
    exact = _items.by_sku(q)
    if exact is not None:
        return exact.sku
    from ..domain.models import Item

    hit = Item.objects.filter(models.Q(sku__icontains=q) | models.Q(name__icontains=q)).order_by("sku").first()
    return hit.sku if hit is not None else None


def stock_on_hand(*, query: str | None = None, warehouse: str | None = None,
                  limit: int = 20) -> dict:
    """On-hand balances for an item (resolved from ``query``) across warehouses (the AI read tool).

    Inventory balances are company-wide (not user-scoped), matching ``low_stock``.
    """
    sku = _match_sku(query) if query else None
    if query and sku is None:
        return {"item": None, "rows": []}
    report = _reports.stock_on_hand(item_sku=sku, warehouse_code=(warehouse or None))
    rows = report.rows[: max(1, min(limit, 50))]
    return {
        "item": sku,
        "total_value_minor": report.total_value_minor,
        "rows": [
            {"sku": r.sku, "name": r.item_name, "warehouse_code": r.warehouse_code,
             "quantity": r.quantity, "value_minor": r.value_minor, "below_reorder": r.below_reorder}
            for r in rows
        ],
    }


def stock_movements(*, query: str, limit: int = 15) -> dict:
    """Recent stock movements (receipts/issues/transfers) for one item, newest first."""
    sku = _match_sku(query)
    if sku is None:
        return {"item": None, "movements": []}
    qs = (StockMovement.objects.filter(item__sku=sku).select_related("item", "warehouse")
          .order_by("-date", "-created_at")[: max(1, min(limit, 30))])
    return {
        "item": sku,
        "movements": [
            {"sku": m.item.sku, "name": m.item.name, "type": m.type,
             "date": str(m.date), "quantity": str(m.quantity),
             "warehouse_code": m.warehouse.code, "reference": m.reference}
            for m in qs
        ],
    }


def expiring_batches(*, days: int = 30) -> dict:
    """Received batches whose earliest expiry falls within ``days`` from today (soonest first)."""
    horizon = datetime.date.today() + datetime.timedelta(days=max(1, min(days, 3650)))
    rows = [
        b for b in _reports.batches()
        if b.earliest_expiry and b.earliest_expiry <= str(horizon)
    ]
    return {
        "within_days": days,
        "batches": [
            {"batch_no": b.batch_no, "sku": b.sku, "name": b.item_name,
             "warehouse_code": b.warehouse_code, "quantity": b.received_quantity,
             "expiry_date": b.earliest_expiry}
            for b in rows
        ],
    }


@dataclass(frozen=True)
class StockTransferInfo:
    id: str
    code: str
    sku: str
    item_name: str
    source_code: str
    destination_code: str
    quantity: str


def create_stock_transfer_draft(*, item_sku: str, source_code: str, destination_code: str,
                                quantity, date=None, reference: str = "", memo: str = "",
                                actor=None) -> StockTransferInfo:
    """Draft a planned move of ``item_sku`` from ``source_code`` to ``destination_code`` — no
    balance moves until a future post step. Raises on an unknown item/warehouse."""
    item = _items.by_sku((item_sku or "").strip())
    if item is None:
        raise UnknownItemError(data={"sku": item_sku})
    source = _warehouses.by_code((source_code or "").strip())
    if source is None:
        raise UnknownWarehouseError(data={"warehouse": source_code})
    destination = _warehouses.by_code((destination_code or "").strip())
    if destination is None:
        raise UnknownWarehouseError(data={"warehouse": destination_code})
    transfer = create_transfer_draft(
        item=item, source=source, destination=destination, quantity=quantity,
        date=date, reference=reference, memo=memo, actor=actor,
    )
    return StockTransferInfo(
        id=str(transfer.id), code=f"XFER-{str(transfer.id)[:8].upper()}",
        sku=item.sku, item_name=item.name,
        source_code=source.code, destination_code=destination.code,
        quantity=str(transfer.quantity),
    )


@dataclass(frozen=True)
class StockCountInfo:
    id: str
    code: str
    warehouse_code: str
    line_count: int


def create_stock_count_draft(*, warehouse_code: str, item_skus: list[str] | None = None,
                             count_date=None, reference: str = "", memo: str = "",
                             actor=None) -> StockCountInfo:
    """Open a draft (``counting``) stock count for a warehouse, snapshotting system quantities for
    every item given (or every item with a balance there, when ``item_skus`` is empty)."""
    warehouse = _warehouses.by_code((warehouse_code or "").strip())
    if warehouse is None:
        raise UnknownWarehouseError(data={"warehouse": warehouse_code})
    count = _stock_count.create_count(
        warehouse=warehouse, item_skus=item_skus, count_date=count_date,
        reference=reference, memo=memo, actor=actor,
    )
    return StockCountInfo(
        id=str(count.id), code=f"COUNT-{str(count.id)[:8].upper()}",
        warehouse_code=warehouse.code, line_count=count.lines.count(),
    )


@dataclass(frozen=True)
class ReorderPointUpdate:
    sku: str
    name: str
    previous_reorder_point: str
    reorder_point: str


def set_reorder_point(*, sku: str, reorder_point, actor=None) -> ReorderPointUpdate:
    """Update an item's reorder point (master-data edit, no stock movement)."""
    item = _items.by_sku((sku or "").strip())
    if item is None:
        raise UnknownItemError(data={"sku": sku})
    previous = item.reorder_point
    item.reorder_point = reorder_point
    item.save(update_fields=["reorder_point"])
    audit.record(
        module="inventory", action="set_reorder_point", entity_type="Item",
        entity_id=str(item.id), actor=actor,
        before={"reorder_point": str(previous)}, after={"reorder_point": str(item.reorder_point)},
    )
    return ReorderPointUpdate(
        sku=item.sku, name=item.name,
        previous_reorder_point=str(previous), reorder_point=str(item.reorder_point),
    )


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
            reference: str = "", memo: str = "", batch_no: str = "", expiry_date=None, actor=None):
    item, warehouse = _resolve(sku, warehouse_code)
    return receive_stock(
        item=item, warehouse=warehouse, quantity=quantity, unit_cost_minor=unit_cost_minor,
        date=date, reference=reference, memo=memo, batch_no=batch_no, expiry_date=expiry_date,
        actor=actor,
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
    "WarehouseInfo",
    "find_item",
    "find_warehouse",
    "list_items",
    "create_item",
    "item_sku_exists",
    "default_warehouse_code",
    "low_stock",
    "stock_on_hand",
    "stock_movements",
    "expiring_batches",
    "issue",
    "receive",
    "return_in",
    "return_out",
    "StockTransferInfo",
    "create_stock_transfer_draft",
    "StockCountInfo",
    "create_stock_count_draft",
    "ReorderPointUpdate",
    "set_reorder_point",
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
