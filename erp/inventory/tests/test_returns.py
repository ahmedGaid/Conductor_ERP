"""Inventory returns — stock back in (customer return) and out (supplier return).

The core invariant must survive both: the Inventory GL account balance always equals total stock
value. return_in reverses an issue's COGS; return_out reverses a receipt's GRNI.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from erp.accounting.services import general_ledger, trial_balance
from erp.inventory.contracts import issue, receive, return_in, return_out
from erp.inventory.errors import InsufficientStockError
from erp.inventory.repositories import balances as balance_repo

from .factories import make_gl, make_item, make_warehouse

import datetime as dt

DATE = dt.date(2026, 6, 15)

pytestmark = pytest.mark.django_db


def _setup():
    make_gl()
    item = make_item()
    wh = make_warehouse()
    receive(item.sku, wh.code, Decimal("20"), 100_00, date=DATE)  # 20 @ 100.00 = 2000.00
    return item, wh


def test_return_in_brings_stock_back_and_keeps_invariant():
    item, wh = _setup()
    issue(item.sku, wh.code, Decimal("12"), date=DATE)  # 8 left @ 100 = 800.00
    assert balance_repo.total_value() == 800_00
    assert general_ledger("5000").closing_balance == 1200_00  # COGS

    # Customer returns 5 — valued at the current weighted-average (100.00) → 500.00 back in.
    return_in(item.sku, wh.code, Decimal("5"), date=DATE)
    assert balance_repo.total_value() == 1300_00
    assert general_ledger("1200").closing_balance == balance_repo.total_value()
    assert general_ledger("5000").closing_balance == 700_00  # COGS reduced 1200 - 500
    assert trial_balance().is_balanced


def test_return_out_ships_stock_back_and_keeps_invariant():
    item, wh = _setup()  # 20 @ 100 = 2000.00, GRNI credited 2000.00
    return_out(item.sku, wh.code, Decimal("5"), date=DATE)  # 15 left @ 100 = 1500.00
    assert balance_repo.total_value() == 1500_00
    assert general_ledger("1200").closing_balance == balance_repo.total_value()
    # return_out debits GRNI, reversing part of the receipt's GRNI credit (2000 - 500 = 1500).
    assert general_ledger("2150").closing_balance == 1500_00
    assert trial_balance().is_balanced


def test_return_out_beyond_on_hand_rejected():
    item, wh = _setup()
    with pytest.raises(InsufficientStockError):
        return_out(item.sku, wh.code, Decimal("50"), date=DATE)
    assert balance_repo.total_value() == 2000_00  # untouched
