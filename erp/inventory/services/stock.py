"""Stock movement services — the inventory invariant point.

Receive / issue / transfer update the weighted-average `StockBalance` and (for receipts and issues)
post the matching journal to the General Ledger **through the accounting public contract** — never by
importing accounting's ORM. Each operation is atomic: balance + movement + GL commit together.

GL postings:
- receipt: Dr Inventory  / Cr Goods-Received-Not-Invoiced (a payable cleared by Purchasing later)
- issue:   Dr COGS       / Cr Inventory
- transfer: no GL (value stays within the Inventory account)

Invariant (proven by tests): the Inventory GL account balance always equals total stock value.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction

from erp.accounting.contracts import JournalInput, LineInput, post_journal
from erp.audit import services as audit
from erp.core.events import bus

from .. import events
from ..domain import costing
from ..domain.models import Item, ItemType, MovementType, StockBalance, StockMovement, Warehouse
from ..errors import (
    InsufficientStockError,
    InvalidCountError,
    InvalidQuantityError,
    NonStockItemError,
    SameWarehouseTransferError,
)

INVENTORY_ACCOUNT = "1200"
COGS_ACCOUNT = "5000"
GRNI_ACCOUNT = "2150"
ADJUSTMENT_ACCOUNT = "5900"  # Inventory Adjustment (count variances)


@dataclass
class GLPosting:
    debit_account: str
    credit_account: str
    amount_minor: int
    memo: str


def _require_stock_item(item: Item) -> None:
    if item.type != ItemType.STOCK:
        raise NonStockItemError(data={"sku": item.sku})


def _require_positive(quantity: Decimal) -> None:
    if quantity is None or Decimal(quantity) <= 0:
        raise InvalidQuantityError()


def _get_balance(item: Item, warehouse: Warehouse) -> StockBalance:
    balance, _ = StockBalance.objects.select_for_update().get_or_create(
        item=item, warehouse=warehouse
    )
    return balance


def _post_gl(posting: GLPosting, date, actor, reference) -> str:
    if posting.amount_minor == 0:
        return ""
    entry = post_journal(
        JournalInput(
            date=date,
            source="inventory",
            reference=reference,
            memo=posting.memo,
            lines=[
                LineInput(account_code=posting.debit_account, debit=posting.amount_minor),
                LineInput(account_code=posting.credit_account, credit=posting.amount_minor),
            ],
        ),
        actor=actor,
    )
    return entry.number


@transaction.atomic
def receive_stock(
    *, item: Item, warehouse: Warehouse, quantity, unit_cost_minor: int,
    date=None, reference: str = "", memo: str = "", batch_no: str = "", expiry_date=None, actor=None,
) -> StockMovement:
    _require_stock_item(item)
    _require_positive(quantity)
    quantity = Decimal(quantity)
    date = date or dt.date.today()
    value = costing.receipt_value(quantity, unit_cost_minor)

    balance = _get_balance(item, warehouse)
    balance.quantity = Decimal(balance.quantity) + quantity
    balance.value_minor += value
    balance.save(update_fields=["quantity", "value_minor"])

    journal_number = _post_gl(
        GLPosting(INVENTORY_ACCOUNT, GRNI_ACCOUNT, value, memo or f"Receipt {item.sku}"),
        date, actor, reference,
    )
    movement = StockMovement.objects.create(
        item=item, warehouse=warehouse, type=MovementType.RECEIPT, date=date,
        quantity=quantity, unit_cost_minor=unit_cost_minor, value_minor=value,
        reference=reference, memo=memo, batch_no=batch_no, expiry_date=expiry_date,
        journal_number=journal_number,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
        branch=actor.branch if getattr(actor, "is_authenticated", False) else None,
    )
    audit.record(
        module="inventory", action="receive_stock", entity_type="StockMovement",
        entity_id=str(movement.id), actor=actor,
        after={"sku": item.sku, "warehouse": warehouse.code, "qty": str(quantity), "value": value},
    )
    bus.publish(events.STOCK_RECEIVED, {"item": item.sku, "warehouse": warehouse.code, "value": value})
    return movement


@transaction.atomic
def issue_stock(
    *, item: Item, warehouse: Warehouse, quantity,
    date=None, reference: str = "", memo: str = "", actor=None,
) -> StockMovement:
    _require_stock_item(item)
    _require_positive(quantity)
    quantity = Decimal(quantity)
    date = date or dt.date.today()

    balance = _get_balance(item, warehouse)
    if quantity > Decimal(balance.quantity):
        raise InsufficientStockError(
            data={"sku": item.sku, "on_hand": str(balance.quantity), "requested": str(quantity)}
        )
    value = costing.issue_value(Decimal(balance.quantity), balance.value_minor, quantity)
    balance.quantity = Decimal(balance.quantity) - quantity
    balance.value_minor -= value
    balance.save(update_fields=["quantity", "value_minor"])

    journal_number = _post_gl(
        GLPosting(COGS_ACCOUNT, INVENTORY_ACCOUNT, value, memo or f"Issue {item.sku}"),
        date, actor, reference,
    )
    movement = StockMovement.objects.create(
        item=item, warehouse=warehouse, type=MovementType.ISSUE, date=date,
        quantity=quantity, value_minor=value, reference=reference, memo=memo,
        journal_number=journal_number,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
        branch=actor.branch if getattr(actor, "is_authenticated", False) else None,
    )
    audit.record(
        module="inventory", action="issue_stock", entity_type="StockMovement",
        entity_id=str(movement.id), actor=actor,
        after={"sku": item.sku, "warehouse": warehouse.code, "qty": str(quantity), "value": value},
    )
    bus.publish(events.STOCK_ISSUED, {"item": item.sku, "warehouse": warehouse.code, "value": value})
    return movement


@transaction.atomic
def return_in_stock(
    *, item: Item, warehouse: Warehouse, quantity,
    date=None, reference: str = "", memo: str = "", actor=None,
) -> StockMovement:
    """Customer return — goods come back into stock (the exact reverse of an issue).

    Valued at the current weighted-average unit cost of the item/warehouse, so the Inventory GL
    keeps matching stock value. GL: Dr Inventory / Cr COGS (reversing the cost of the sale). If the
    warehouse currently holds none of the item the average is unknown and the return is valued at 0.
    """
    _require_stock_item(item)
    _require_positive(quantity)
    quantity = Decimal(quantity)
    date = date or dt.date.today()

    balance = _get_balance(item, warehouse)
    on_hand = Decimal(balance.quantity)
    if on_hand > 0:
        unit = Decimal(balance.value_minor) / on_hand
        value = int((quantity * unit).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    else:
        value = 0
    balance.quantity = on_hand + quantity
    balance.value_minor += value
    balance.save(update_fields=["quantity", "value_minor"])

    journal_number = _post_gl(
        GLPosting(INVENTORY_ACCOUNT, COGS_ACCOUNT, value, memo or f"Return in {item.sku}"),
        date, actor, reference,
    )
    movement = StockMovement.objects.create(
        item=item, warehouse=warehouse, type=MovementType.RETURN_IN, date=date,
        quantity=quantity, value_minor=value, reference=reference, memo=memo,
        journal_number=journal_number,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
        branch=actor.branch if getattr(actor, "is_authenticated", False) else None,
    )
    audit.record(
        module="inventory", action="return_in_stock", entity_type="StockMovement",
        entity_id=str(movement.id), actor=actor,
        after={"sku": item.sku, "warehouse": warehouse.code, "qty": str(quantity), "value": value},
    )
    bus.publish(events.STOCK_RECEIVED, {"item": item.sku, "warehouse": warehouse.code, "value": value})
    return movement


@transaction.atomic
def return_out_stock(
    *, item: Item, warehouse: Warehouse, quantity,
    date=None, reference: str = "", memo: str = "", actor=None,
) -> StockMovement:
    """Supplier return — goods leave stock (the exact reverse of a receipt).

    Valued at weighted average. GL: Dr GRNI / Cr Inventory (the Purchasing module then clears GRNI
    against AP, so the net of a billed receipt + return is nil). Rejects returning more than on hand.
    """
    _require_stock_item(item)
    _require_positive(quantity)
    quantity = Decimal(quantity)
    date = date or dt.date.today()

    balance = _get_balance(item, warehouse)
    if quantity > Decimal(balance.quantity):
        raise InsufficientStockError(
            data={"sku": item.sku, "on_hand": str(balance.quantity), "requested": str(quantity)}
        )
    value = costing.issue_value(Decimal(balance.quantity), balance.value_minor, quantity)
    balance.quantity = Decimal(balance.quantity) - quantity
    balance.value_minor -= value
    balance.save(update_fields=["quantity", "value_minor"])

    journal_number = _post_gl(
        GLPosting(GRNI_ACCOUNT, INVENTORY_ACCOUNT, value, memo or f"Return out {item.sku}"),
        date, actor, reference,
    )
    movement = StockMovement.objects.create(
        item=item, warehouse=warehouse, type=MovementType.RETURN_OUT, date=date,
        quantity=quantity, value_minor=value, reference=reference, memo=memo,
        journal_number=journal_number,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
        branch=actor.branch if getattr(actor, "is_authenticated", False) else None,
    )
    audit.record(
        module="inventory", action="return_out_stock", entity_type="StockMovement",
        entity_id=str(movement.id), actor=actor,
        after={"sku": item.sku, "warehouse": warehouse.code, "qty": str(quantity), "value": value},
    )
    bus.publish(events.STOCK_ISSUED, {"item": item.sku, "warehouse": warehouse.code, "value": value})
    return movement


@transaction.atomic
def adjust_stock(
    *, item: Item, warehouse: Warehouse, counted_quantity,
    date=None, reference: str = "", memo: str = "", unit_cost_minor: int | None = None, actor=None,
) -> StockMovement | None:
    """Adjust on-hand to a counted quantity, posting the value variance to the GL.

    Shortage (counted < on-hand): value removed at weighted average → Dr Inventory Adjustment /
    Cr Inventory. Overage (counted > on-hand): valued at the current weighted-average unit cost (or a
    supplied ``unit_cost_minor`` when the warehouse holds none) → Dr Inventory / Cr Inventory
    Adjustment. The Inventory GL and the stock value move by the same amount, so the invariant holds.
    Returns ``None`` when there is no variance.
    """
    _require_stock_item(item)
    counted = Decimal(counted_quantity)
    if counted < 0:
        raise InvalidCountError(data={"sku": item.sku, "counted": str(counted)})
    date = date or dt.date.today()

    balance = _get_balance(item, warehouse)
    on_hand = Decimal(balance.quantity)
    variance = counted - on_hand
    if variance == 0:
        return None

    if variance < 0:  # shortage — remove cost at weighted average
        shortage = -variance
        value = costing.issue_value(on_hand, balance.value_minor, shortage)
        balance.quantity = on_hand - shortage
        balance.value_minor -= value
        posting = GLPosting(ADJUSTMENT_ACCOUNT, INVENTORY_ACCOUNT, value,
                            memo or f"Count shortage {item.sku}")
        signed_value = -value
    else:  # overage — value at current average, else the supplied cost, else zero
        if on_hand > 0:
            unit = Decimal(balance.value_minor) / on_hand
            value = int((variance * unit).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        elif unit_cost_minor is not None:
            value = costing.receipt_value(variance, unit_cost_minor)
        else:
            value = 0
        balance.quantity = on_hand + variance
        balance.value_minor += value
        posting = GLPosting(INVENTORY_ACCOUNT, ADJUSTMENT_ACCOUNT, value,
                            memo or f"Count overage {item.sku}")
        signed_value = value
    balance.save(update_fields=["quantity", "value_minor"])

    journal_number = _post_gl(posting, date, actor, reference)
    movement = StockMovement.objects.create(
        item=item, warehouse=warehouse, type=MovementType.ADJUSTMENT, date=date,
        quantity=variance, value_minor=signed_value, reference=reference, memo=memo,
        journal_number=journal_number,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
        branch=actor.branch if getattr(actor, "is_authenticated", False) else None,
    )
    audit.record(
        module="inventory", action="adjust_stock", entity_type="StockMovement",
        entity_id=str(movement.id), actor=actor,
        after={"sku": item.sku, "warehouse": warehouse.code,
               "variance": str(variance), "value": signed_value},
    )
    event = events.STOCK_RECEIVED if variance > 0 else events.STOCK_ISSUED
    bus.publish(event, {"item": item.sku, "warehouse": warehouse.code, "value": abs(signed_value)})
    return movement


@transaction.atomic
def transfer_stock(
    *, item: Item, source: Warehouse, destination: Warehouse, quantity,
    date=None, reference: str = "", memo: str = "", actor=None,
) -> StockMovement:
    _require_stock_item(item)
    _require_positive(quantity)
    if source.id == destination.id:
        raise SameWarehouseTransferError()
    quantity = Decimal(quantity)
    date = date or dt.date.today()

    src = _get_balance(item, source)
    if quantity > Decimal(src.quantity):
        raise InsufficientStockError(
            data={"sku": item.sku, "on_hand": str(src.quantity), "requested": str(quantity)}
        )
    value = costing.issue_value(Decimal(src.quantity), src.value_minor, quantity)
    src.quantity = Decimal(src.quantity) - quantity
    src.value_minor -= value
    src.save(update_fields=["quantity", "value_minor"])

    dst = _get_balance(item, destination)
    dst.quantity = Decimal(dst.quantity) + quantity
    dst.value_minor += value
    dst.save(update_fields=["quantity", "value_minor"])

    movement = StockMovement.objects.create(
        item=item, warehouse=source, dest_warehouse=destination, type=MovementType.TRANSFER,
        date=date, quantity=quantity, value_minor=value, reference=reference, memo=memo,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
        branch=actor.branch if getattr(actor, "is_authenticated", False) else None,
    )
    audit.record(
        module="inventory", action="transfer_stock", entity_type="StockMovement",
        entity_id=str(movement.id), actor=actor,
        after={"sku": item.sku, "from": source.code, "to": destination.code, "qty": str(quantity)},
    )
    bus.publish(
        events.STOCK_TRANSFERRED,
        {"item": item.sku, "from": source.code, "to": destination.code, "value": value},
    )
    return movement
