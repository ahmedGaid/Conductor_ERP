"""Purchase order lifecycle — procure-to-pay, GRNI clearing, 3-way match."""
from __future__ import annotations

from decimal import Decimal

import pytest

from erp.accounting.services import general_ledger, trial_balance
from erp.inventory.repositories import balances as balance_repo
from erp.purchasing.domain.models import POStatus
from erp.purchasing.errors import OverpaymentError, ThreeWayMatchError
from erp.purchasing.services import (
    POLineInput,
    bill_order,
    confirm_order,
    create_order,
    pay_order,
    receive_order,
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


def test_full_procure_to_pay_clears_grni_and_balances():
    supplier, wh = _setup()
    order = _po(supplier, wh)
    assert order.subtotal_minor == 1000_00

    confirm_order(order)
    receive_order(order)
    assert order.status == POStatus.RECEIVED
    # Receipt raised stock and posted Dr Inventory / Cr GRNI
    assert balance_repo.total_value() == 1000_00
    assert general_ledger("1200").closing_balance == 1000_00   # Inventory
    assert general_ledger("2150").closing_balance == 1000_00   # GRNI (liability, credit)

    bill_order(order)
    assert order.status == POStatus.BILLED
    assert order.bill_number
    # Bill cleared GRNI into AP
    assert general_ledger("2150").closing_balance == 0
    assert general_ledger("2000").closing_balance == 1000_00   # AP

    pay_order(order, 1000_00)
    assert order.status == POStatus.PAID
    assert general_ledger("2000").closing_balance == 0          # AP settled
    assert trial_balance().is_balanced


def test_inventory_gl_matches_stock_value_after_receipt():
    supplier, wh = _setup()
    order = _po(supplier, wh)
    confirm_order(order)
    receive_order(order)
    assert general_ledger("1200").closing_balance == balance_repo.total_value()


def test_three_way_match_blocks_bill_on_partial_receipt():
    supplier, wh = _setup()
    order = _po(supplier, wh, qty="10")
    confirm_order(order)
    # Receive only 6 of 10 ordered.
    receive_order(order, received={1: Decimal("6")})
    with pytest.raises(ThreeWayMatchError):
        bill_order(order)
    order.refresh_from_db()
    assert order.status == POStatus.RECEIVED
    # GRNI reflects only what was received; no AP booked yet.
    assert general_ledger("2150").closing_balance == 600_00
    assert general_ledger("2000").closing_balance == 0


def test_overpayment_rejected():
    supplier, wh = _setup()
    order = _po(supplier, wh)
    confirm_order(order)
    receive_order(order)
    bill_order(order)
    with pytest.raises(OverpaymentError):
        pay_order(order, 2000_00)


def test_partial_then_full_payment():
    supplier, wh = _setup()
    order = _po(supplier, wh)
    confirm_order(order)
    receive_order(order)
    bill_order(order)
    pay_order(order, 400_00)
    assert order.status == POStatus.BILLED
    assert order.outstanding_minor == 600_00
    pay_order(order, 600_00)
    assert order.status == POStatus.PAID
