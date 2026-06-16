"""Purchasing partial receipt (multi-GRN) + supplier returns (debit notes).

A partial receipt accumulates across calls until fully received; only then does the 3-way match
pass. A supplier return ships stock back out (via the inventory contract) and clears the payable
through GRNI — the trial balance stays balanced, GRNI nets to zero, and Inventory GL == stock value.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from erp.accounting.services import general_ledger, trial_balance
from erp.inventory.repositories import balances as balance_repo
from erp.purchasing.domain.models import POStatus
from erp.purchasing.errors import ExcessiveReturnError, InvalidTransitionError, NothingToReturnError
from erp.purchasing.services import (
    POLineInput,
    bill_order,
    confirm_order,
    create_order,
    pay_order,
    receive_order,
    return_order,
)

from .factories import DATE, make_books, make_item, make_supplier, make_warehouse

pytestmark = pytest.mark.django_db


def _po(supplier, warehouse, qty="10", cost=100_00):
    return create_order(
        supplier=supplier, warehouse_code=warehouse.code, order_date=DATE,
        lines=[POLineInput(item_sku="WIDGET", quantity=Decimal(qty), unit_cost_minor=cost)],
    )


def _setup():
    make_books()
    make_item()
    return make_supplier(), make_warehouse()


def test_accumulating_partial_receipts_complete_to_received():
    supplier, wh = _setup()
    order = _po(supplier, wh, qty="10")
    confirm_order(order)

    receive_order(order, received={1: Decimal("6")})
    order.refresh_from_db()
    assert order.status == POStatus.PARTIALLY_RECEIVED
    assert order.lines.get(line_no=1).received_qty == Decimal("6")

    receive_order(order, received={1: Decimal("4")})  # the remaining 4
    order.refresh_from_db()
    assert order.status == POStatus.RECEIVED
    assert order.lines.get(line_no=1).received_qty == Decimal("10")
    assert general_ledger("1200").closing_balance == balance_repo.total_value()
    bill_order(order)  # now the 3-way match passes
    assert order.status == POStatus.BILLED


def test_supplier_return_clears_payable_and_balances():
    supplier, wh = _setup()
    order = _po(supplier, wh, qty="10")  # 10 @ 100 = 1000.00
    confirm_order(order)
    receive_order(order)
    bill_order(order)
    assert general_ledger("2000").closing_balance == 1000_00  # AP

    stock_before = balance_repo.total_value()  # 1000.00
    return_order(order, returned={1: Decimal("3")})  # return 3 @ 100 = 300.00
    order.refresh_from_db()

    assert balance_repo.total_value() == stock_before - 300_00
    assert general_ledger("1200").closing_balance == balance_repo.total_value()
    assert general_ledger("2150").closing_balance == 0          # GRNI nets to zero
    assert general_ledger("2000").closing_balance == 700_00     # AP reduced 1000 - 300
    assert order.returned_minor == 300_00
    assert order.outstanding_minor == 700_00
    assert order.debit_note_number
    assert order.status == POStatus.BILLED  # only partly returned
    assert trial_balance().is_balanced


def test_full_supplier_return_marks_order_returned():
    supplier, wh = _setup()
    order = _po(supplier, wh, qty="10")
    confirm_order(order)
    receive_order(order)
    bill_order(order)

    return_order(order)  # full
    order.refresh_from_db()
    assert order.status == POStatus.RETURNED
    assert general_ledger("2000").closing_balance == 0  # AP fully reversed
    assert balance_repo.total_value() == 0
    assert trial_balance().is_balanced


def test_return_more_than_received_rejected():
    supplier, wh = _setup()
    order = _po(supplier, wh, qty="10")
    confirm_order(order)
    receive_order(order)
    bill_order(order)
    with pytest.raises(ExcessiveReturnError):
        return_order(order, returned={1: Decimal("99")})


def test_return_before_bill_rejected():
    supplier, wh = _setup()
    order = _po(supplier, wh, qty="10")
    confirm_order(order)
    receive_order(order)
    with pytest.raises(InvalidTransitionError):
        return_order(order)


def test_empty_return_rejected():
    supplier, wh = _setup()
    order = _po(supplier, wh, qty="10")
    confirm_order(order)
    receive_order(order)
    bill_order(order)
    with pytest.raises(NothingToReturnError):
        return_order(order, returned={1: Decimal("0")})
