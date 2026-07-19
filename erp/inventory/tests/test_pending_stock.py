"""Draftable inventory opening balances — ``PendingStockEntry`` stages an opening quantity+cost;
applying it posts Dr Inventory / Cr a dedicated opening-suspense account (never GRNI, which would
misstate an opening as a goods-received-not-invoiced liability) and updates ``StockBalance`` with
the same weighted-average math ``receive_stock`` uses. See DESIGN_PENDING_PAYMENTS_AND_STOCK.md
sub-project 2."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from erp.accounting.domain.models import EntryStatus, JournalEntry
from erp.inventory.domain.models import MovementType, PendingStockEntryStatus, StockMovement
from erp.inventory.errors import PendingStockEntryStateError
from erp.inventory.repositories import balances as balance_repo
from erp.inventory.services.pending_stock import (
    apply_pending_stock_opening,
    create_pending_stock_opening,
    discard_pending_stock_opening,
)

from .factories import make_gl, make_item, make_warehouse

pytestmark = pytest.mark.django_db

DATE = dt.date(2026, 1, 1)


def _setup():
    make_gl()
    return make_item(), make_warehouse()


def test_apply_posts_to_suspense_not_grni_and_updates_balance():
    item, wh = _setup()
    pending = create_pending_stock_opening(
        item=item, warehouse=wh, quantity=Decimal("10"), unit_cost_minor=100_00,
        date=DATE, suspense_account="3110",
    )
    assert pending.status == PendingStockEntryStatus.PENDING

    applied = apply_pending_stock_opening(pending)

    assert applied.status == PendingStockEntryStatus.APPLIED
    assert applied.applied_at is not None
    bal = balance_repo.for_pair(item, wh)
    assert bal.quantity == Decimal("10")
    assert bal.value_minor == 1000_00

    movement = StockMovement.objects.get(item=item, warehouse=wh)
    assert movement.type == MovementType.OPENING
    assert movement.journal_number

    entry = JournalEntry.objects.get(number=movement.journal_number)
    assert entry.status == EntryStatus.POSTED
    lines = {line.account.code: (line.debit, line.credit) for line in entry.lines.all()}
    assert lines == {"1200": (1000_00, 0), "3110": (0, 1000_00)}  # Dr Inventory / Cr suspense
    assert "2150" not in lines  # never GRNI


def test_apply_already_applied_raises():
    item, wh = _setup()
    pending = create_pending_stock_opening(
        item=item, warehouse=wh, quantity=Decimal("5"), unit_cost_minor=100_00,
        date=DATE, suspense_account="3110",
    )
    apply_pending_stock_opening(pending)

    with pytest.raises(PendingStockEntryStateError):
        apply_pending_stock_opening(pending)


def test_discard_is_a_clean_no_op_and_blocks_further_actions():
    item, wh = _setup()
    pending = create_pending_stock_opening(
        item=item, warehouse=wh, quantity=Decimal("5"), unit_cost_minor=100_00,
        date=DATE, suspense_account="3110",
    )

    discarded = discard_pending_stock_opening(pending)

    assert discarded.status == PendingStockEntryStatus.DISCARDED
    assert balance_repo.for_pair(item, wh) is None  # nothing ever touched
    with pytest.raises(PendingStockEntryStateError):
        apply_pending_stock_opening(discarded)
    with pytest.raises(PendingStockEntryStateError):
        discard_pending_stock_opening(discarded)
