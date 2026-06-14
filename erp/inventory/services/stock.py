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
from decimal import Decimal

from django.db import transaction

from erp.accounting.contracts import JournalInput, LineInput, post_journal
from erp.audit import services as audit
from erp.core.events import bus

from .. import events
from ..domain import costing
from ..domain.models import Item, ItemType, MovementType, StockBalance, StockMovement, Warehouse
from ..errors import (
    InsufficientStockError,
    InvalidQuantityError,
    NonStockItemError,
    SameWarehouseTransferError,
)

INVENTORY_ACCOUNT = "1200"
COGS_ACCOUNT = "5000"
GRNI_ACCOUNT = "2150"


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
    date=None, reference: str = "", memo: str = "", actor=None,
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
        reference=reference, memo=memo, journal_number=journal_number,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
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
    )
    audit.record(
        module="inventory", action="issue_stock", entity_type="StockMovement",
        entity_id=str(movement.id), actor=actor,
        after={"sku": item.sku, "warehouse": warehouse.code, "qty": str(quantity), "value": value},
    )
    bus.publish(events.STOCK_ISSUED, {"item": item.sku, "warehouse": warehouse.code, "value": value})
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
