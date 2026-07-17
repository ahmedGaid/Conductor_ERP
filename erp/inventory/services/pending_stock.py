"""Draftable inventory opening balances — the human-in-the-loop staging step ``receive_stock`` has
no form for (it posts Dr Inventory / Cr GRNI immediately, which is wrong for an opening and would
double-count the Inventory control account ``account_opening`` already books). An import (or,
later, the AI assistant) creates a ``PendingStockEntry`` instead of posting; a human applies it,
at which point this posts Dr Inventory / Cr the entry's own ``suspense_account`` and updates
``StockBalance`` with the same weighted-average math ``receive_stock`` uses — no second inventory
write path, no GRNI leg. See DESIGN_PENDING_PAYMENTS_AND_STOCK.md sub-project 2.
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from erp.accounting.contracts import JournalInput, LineInput, post_journal
from erp.audit import services as audit

from ..domain import costing
from ..domain.models import (
    Item,
    MovementType,
    PendingStockEntry,
    PendingStockEntryStatus,
    StockBalance,
    StockMovement,
    Warehouse,
)
from ..errors import PendingStockEntryStateError
from .stock import INVENTORY_ACCOUNT


def create_pending_stock_opening(
    *, item: Item, warehouse: Warehouse, quantity: Decimal, unit_cost_minor: int, date: dt.date,
    suspense_account: str, batch_ref: str = "", actor=None,
) -> PendingStockEntry:
    return PendingStockEntry.objects.create(
        item=item, warehouse=warehouse, quantity=quantity, unit_cost_minor=unit_cost_minor,
        date=date, suspense_account=suspense_account, batch_ref=batch_ref,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
        branch=actor.branch if getattr(actor, "is_authenticated", False) else None,
        department=actor.department if getattr(actor, "is_authenticated", False) else None,
        team=actor.team if getattr(actor, "is_authenticated", False) else None,
    )


@transaction.atomic
def apply_pending_stock_opening(pending: PendingStockEntry, actor=None) -> PendingStockEntry:
    if pending.status != PendingStockEntryStatus.PENDING:
        raise PendingStockEntryStateError(f"pending stock entry is {pending.status!r}, not pending")

    value = costing.receipt_value(pending.quantity, pending.unit_cost_minor)
    balance, _ = StockBalance.objects.select_for_update().get_or_create(
        item=pending.item, warehouse=pending.warehouse,
    )
    balance.quantity = Decimal(balance.quantity) + pending.quantity
    balance.value_minor += value
    balance.save(update_fields=["quantity", "value_minor"])

    journal_number = ""
    if value != 0:
        entry = post_journal(
            JournalInput(
                date=pending.date,
                source="inventory-opening",
                reference=pending.batch_ref,
                memo=f"Opening balance {pending.item.sku}",
                lines=[
                    LineInput(account_code=INVENTORY_ACCOUNT, debit=value),
                    LineInput(account_code=pending.suspense_account, credit=value),
                ],
            ),
            actor=actor,
        )
        journal_number = entry.number

    movement = StockMovement.objects.create(
        item=pending.item, warehouse=pending.warehouse, type=MovementType.OPENING, date=pending.date,
        quantity=pending.quantity, unit_cost_minor=pending.unit_cost_minor, value_minor=value,
        reference=pending.batch_ref, memo=f"Opening balance {pending.item.sku}",
        journal_number=journal_number,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
        branch=actor.branch if getattr(actor, "is_authenticated", False) else None,
        department=actor.department if getattr(actor, "is_authenticated", False) else None,
        team=actor.team if getattr(actor, "is_authenticated", False) else None,
    )
    pending.status = PendingStockEntryStatus.APPLIED
    pending.applied_by = actor if getattr(actor, "is_authenticated", False) else None
    pending.applied_at = timezone.now()
    pending.save(update_fields=["status", "applied_by", "applied_at", "updated_at"])

    audit.record(
        module="inventory", action="apply_pending_stock_opening", entity_type="StockMovement",
        entity_id=str(movement.id), actor=actor,
        after={"sku": pending.item.sku, "warehouse": pending.warehouse.code,
               "qty": str(pending.quantity), "value": value},
    )
    return pending


def discard_pending_stock_opening(pending: PendingStockEntry, actor=None) -> PendingStockEntry:
    if pending.status != PendingStockEntryStatus.PENDING:
        raise PendingStockEntryStateError(f"pending stock entry is {pending.status!r}, not pending")
    pending.status = PendingStockEntryStatus.DISCARDED
    pending.save(update_fields=["status", "updated_at"])
    return pending
