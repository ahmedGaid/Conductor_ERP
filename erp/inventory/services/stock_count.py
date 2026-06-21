"""Physical stock-count workflow.

A count snapshots the current system quantities for a warehouse, the user enters counted quantities,
then posting reconciles each line to its counted quantity via ``adjust_stock`` — so every variance
becomes a balanced GL adjustment and the Inventory-GL == stock-value invariant is preserved.
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.db import transaction

from ..domain.models import (
    CountStatus,
    Item,
    StockBalance,
    StockCount,
    StockCountLine,
    Warehouse,
)
from ..errors import CountStateError, InvalidCountError, UnknownItemError
from ..repositories import items as _items
from .stock import adjust_stock


@transaction.atomic
def create_count(*, warehouse: Warehouse, item_skus: list[str] | None = None,
                 count_date=None, reference: str = "", memo: str = "", actor=None) -> StockCount:
    """Snapshot system quantities into a new count. Without a SKU list, every item with a balance in
    the warehouse is included."""
    count = StockCount.objects.create(
        warehouse=warehouse, count_date=count_date or dt.date.today(),
        reference=reference, memo=memo, status=CountStatus.COUNTING,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
        branch=actor.branch if getattr(actor, "is_authenticated", False) else None,
        department=actor.department if getattr(actor, "is_authenticated", False) else None,
        team=actor.team if getattr(actor, "is_authenticated", False) else None,
    )
    if item_skus:
        for sku in item_skus:
            item = _items.by_sku(sku)
            if item is None:
                raise UnknownItemError(data={"sku": sku})
            balance = StockBalance.objects.filter(item=item, warehouse=warehouse).first()
            StockCountLine.objects.create(
                count=count, item=item,
                system_quantity=Decimal(balance.quantity) if balance else Decimal("0"),
            )
    else:
        balances = StockBalance.objects.filter(warehouse=warehouse).select_related("item").order_by("item__sku")
        for balance in balances:
            StockCountLine.objects.create(
                count=count, item=balance.item, system_quantity=Decimal(balance.quantity),
            )
    return count


@transaction.atomic
def set_counted(line: StockCountLine, counted_quantity) -> StockCountLine:
    """Record the counted quantity for a line (only while the count is still being counted)."""
    if line.count.status != CountStatus.COUNTING:
        raise CountStateError(data={"count": str(line.count_id), "status": line.count.status})
    counted = Decimal(counted_quantity)
    if counted < 0:
        raise InvalidCountError(data={"counted": str(counted)})
    line.counted_quantity = counted
    line.save(update_fields=["counted_quantity"])
    return line


@transaction.atomic
def post_count(count: StockCount, actor=None) -> StockCount:
    """Post every counted line's variance as a stock adjustment, then lock the count."""
    if count.status != CountStatus.COUNTING:
        raise CountStateError(data={"count": str(count.id), "status": count.status})
    for line in count.lines.select_related("item").order_by("item__sku"):
        if line.counted_quantity is None:
            continue  # uncounted ⇒ no change assumed
        movement = adjust_stock(
            item=line.item, warehouse=count.warehouse, counted_quantity=line.counted_quantity,
            date=count.count_date, reference=count.reference or f"COUNT-{count.id}",
            memo=f"Stock count {count.count_date}", actor=actor,
        )
        if movement is not None:
            line.variance_quantity = movement.quantity
            line.variance_value_minor = movement.value_minor
            line.movement = movement
            line.save(update_fields=["variance_quantity", "variance_value_minor", "movement"])
    count.status = CountStatus.POSTED
    count.save(update_fields=["status"])
    return count


@transaction.atomic
def cancel_count(count: StockCount) -> StockCount:
    if count.status != CountStatus.COUNTING:
        raise CountStateError(data={"count": str(count.id), "status": count.status})
    count.status = CountStatus.CANCELLED
    count.save(update_fields=["status"])
    return count
