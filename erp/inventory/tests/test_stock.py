"""Stock services — weighted-average balances, GL integration, reconciliation, guards."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from erp.accounting.domain.models import EntryStatus, JournalEntry
from erp.accounting.services import general_ledger
from erp.inventory.domain import costing
from erp.inventory.domain.models import StockMovement
from erp.inventory.errors import InsufficientStockError, SameWarehouseTransferError
from erp.inventory.repositories import balances as balance_repo
from erp.inventory.services import issue_stock, receive_stock, stock_on_hand, transfer_stock

from .factories import make_gl, make_item, make_warehouse

pytestmark = pytest.mark.django_db

DATE = dt.date(2026, 6, 15)


def _setup():
    make_gl()
    return make_item(), make_warehouse()


def test_receive_updates_balance_and_posts_gl():
    item, wh = _setup()
    mv = receive_stock(item=item, warehouse=wh, quantity=Decimal("10"), unit_cost_minor=100_00, date=DATE)
    bal = balance_repo.for_pair(item, wh)
    assert bal.quantity == Decimal("10")
    assert bal.value_minor == 1000_00
    assert mv.journal_number  # GL posted
    # Dr Inventory / Cr GRNI, balanced
    entry = JournalEntry.objects.get(number=mv.journal_number)
    assert entry.status == EntryStatus.POSTED
    assert sum(line_total(entry, "debit")) == sum(line_total(entry, "credit")) == 1000_00


def line_total(entry, side):
    return [getattr(line, side) for line in entry.lines.all()]


def test_weighted_average_across_receipts_and_issue():
    item, wh = _setup()
    receive_stock(item=item, warehouse=wh, quantity=Decimal("10"), unit_cost_minor=100_00, date=DATE)
    receive_stock(item=item, warehouse=wh, quantity=Decimal("10"), unit_cost_minor=200_00, date=DATE)
    bal = balance_repo.for_pair(item, wh)
    assert bal.quantity == Decimal("20")
    assert bal.value_minor == 3000_00
    assert costing.average_cost_minor(bal.quantity, bal.value_minor) == 150_00  # weighted avg

    issue_stock(item=item, warehouse=wh, quantity=Decimal("5"), date=DATE)
    bal = balance_repo.for_pair(item, wh)
    assert bal.quantity == Decimal("15")
    assert bal.value_minor == 2250_00  # 3000 - (3000*5/20)=750


def test_issue_beyond_on_hand_is_rejected_and_writes_nothing():
    item, wh = _setup()
    receive_stock(item=item, warehouse=wh, quantity=Decimal("3"), unit_cost_minor=100_00, date=DATE)
    movements_before = StockMovement.objects.count()
    with pytest.raises(InsufficientStockError):
        issue_stock(item=item, warehouse=wh, quantity=Decimal("5"), date=DATE)
    assert StockMovement.objects.count() == movements_before
    assert balance_repo.for_pair(item, wh).quantity == Decimal("3")


def test_inventory_gl_balance_equals_total_stock_value():
    """The core cross-module invariant: GL Inventory account == total stock value."""
    item, wh = _setup()
    receive_stock(item=item, warehouse=wh, quantity=Decimal("10"), unit_cost_minor=100_00, date=DATE)
    receive_stock(item=item, warehouse=wh, quantity=Decimal("4"), unit_cost_minor=250_00, date=DATE)
    issue_stock(item=item, warehouse=wh, quantity=Decimal("6"), date=DATE)

    stock_value = balance_repo.total_value()
    inventory_gl = general_ledger("1200").closing_balance
    assert inventory_gl == stock_value


def test_issue_posts_cogs():
    item, wh = _setup()
    receive_stock(item=item, warehouse=wh, quantity=Decimal("10"), unit_cost_minor=100_00, date=DATE)
    issue_stock(item=item, warehouse=wh, quantity=Decimal("4"), date=DATE)
    # COGS (expense, debit-normal) holds the issued cost.
    assert general_ledger("5000").closing_balance == 400_00


def test_transfer_moves_value_without_gl():
    item, src = _setup()
    dst = make_warehouse(code="WH2", name="Second")
    receive_stock(item=item, warehouse=src, quantity=Decimal("10"), unit_cost_minor=100_00, date=DATE)
    gl_entries_before = JournalEntry.objects.count()

    transfer_stock(item=item, source=src, destination=dst, quantity=Decimal("4"), date=DATE)
    assert balance_repo.for_pair(item, src).quantity == Decimal("6")
    assert balance_repo.for_pair(item, dst).quantity == Decimal("4")
    assert balance_repo.for_pair(item, dst).value_minor == 400_00
    # total value conserved, no new GL entry for a transfer
    assert balance_repo.total_value() == 1000_00
    assert JournalEntry.objects.count() == gl_entries_before


def test_transfer_same_warehouse_rejected():
    item, wh = _setup()
    receive_stock(item=item, warehouse=wh, quantity=Decimal("5"), unit_cost_minor=100_00, date=DATE)
    with pytest.raises(SameWarehouseTransferError):
        transfer_stock(item=item, source=wh, destination=wh, quantity=Decimal("1"), date=DATE)


def test_stock_on_hand_report():
    item, wh = _setup()
    receive_stock(item=item, warehouse=wh, quantity=Decimal("10"), unit_cost_minor=100_00, date=DATE)
    report = stock_on_hand()
    assert report.total_value_minor == 1000_00
    assert report.rows[0].sku == item.sku
    assert report.rows[0].avg_cost_minor == 100_00
