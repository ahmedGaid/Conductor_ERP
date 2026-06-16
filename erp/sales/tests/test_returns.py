"""Sales partial delivery + customer returns (credit notes).

Partial delivery issues stock in multiple shipments until the order is fully delivered. A return
brings stock back (via the inventory contract) and credits AR through a Sales Returns contra-revenue
account — the trial balance stays balanced and the Inventory GL keeps matching stock value.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from erp.accounting.services import general_ledger, trial_balance
from erp.inventory.repositories import balances as balance_repo
from erp.sales.domain.models import OrderStatus
from erp.sales.errors import ExcessiveReturnError, InvalidTransitionError, NothingToReturnError
from erp.sales.services import (
    OrderLineInput,
    confirm_order,
    create_order,
    deliver_order,
    invoice_order,
    return_order,
)

from .factories import DATE, make_books, make_customer, make_item, make_warehouse, stocked

pytestmark = pytest.mark.django_db


def _order(customer, warehouse, qty="10", price=150_00):
    return create_order(
        customer=customer, warehouse_code=warehouse.code, order_date=DATE,
        lines=[OrderLineInput(item_sku="WIDGET", quantity=Decimal(qty), unit_price_minor=price)],
    )


def _setup():
    make_books()
    item = make_item()
    wh = make_warehouse()
    stocked(item, wh)  # 20 @ 100.00
    return make_customer(), wh


def test_partial_delivery_then_complete():
    customer, wh = _setup()
    order = _order(customer, wh)  # 10 ordered
    confirm_order(order)

    deliver_order(order, delivered={1: Decimal("4")})
    order.refresh_from_db()
    assert order.status == OrderStatus.PARTIALLY_DELIVERED
    assert balance_repo.total_value() == 1600_00  # 20-4=16 @ 100
    assert order.lines.get(line_no=1).delivered_qty == Decimal("4")

    deliver_order(order)  # deliver the remaining 6
    order.refresh_from_db()
    assert order.status == OrderStatus.DELIVERED
    assert order.lines.get(line_no=1).delivered_qty == Decimal("10")
    assert general_ledger("1200").closing_balance == balance_repo.total_value()


def test_return_credits_ar_brings_stock_back_books_balanced():
    customer, wh = _setup()
    order = _order(customer, wh)
    confirm_order(order)
    deliver_order(order)
    invoice_order(order)
    assert general_ledger("1100").closing_balance == 1500_00  # AR

    stock_before = balance_repo.total_value()  # 10 left @ 100 = 1000.00
    return_order(order, returned={1: Decimal("4")})  # 4 units back
    order.refresh_from_db()

    # Stock back in at avg 100.00 → +400.00; Inventory GL still matches stock value.
    assert balance_repo.total_value() == stock_before + 400_00
    assert general_ledger("1200").closing_balance == balance_repo.total_value()
    # AR reduced by the selling value of 4 @ 150.00 = 600.00; Sales Returns (contra-revenue,
    # credit-normal) is debited 600.00, so its signed balance reads negative against revenue.
    assert general_ledger("1100").closing_balance == 900_00
    assert general_ledger("4090").closing_balance == -600_00
    assert order.returned_minor == 600_00
    assert order.outstanding_minor == 900_00
    assert order.credit_note_number
    assert order.status == OrderStatus.INVOICED  # only partly returned
    assert trial_balance().is_balanced


def test_full_return_marks_order_returned():
    customer, wh = _setup()
    order = _order(customer, wh)
    confirm_order(order)
    deliver_order(order)
    invoice_order(order)

    return_order(order)  # full return
    order.refresh_from_db()
    assert order.status == OrderStatus.RETURNED
    assert general_ledger("1100").closing_balance == 0  # AR fully reversed
    assert trial_balance().is_balanced


def test_return_more_than_delivered_rejected():
    customer, wh = _setup()
    order = _order(customer, wh)
    confirm_order(order)
    deliver_order(order)
    invoice_order(order)
    with pytest.raises(ExcessiveReturnError):
        return_order(order, returned={1: Decimal("99")})


def test_return_before_invoice_rejected():
    customer, wh = _setup()
    order = _order(customer, wh)
    confirm_order(order)
    deliver_order(order)
    with pytest.raises(InvalidTransitionError):
        return_order(order)


def test_empty_return_rejected():
    customer, wh = _setup()
    order = _order(customer, wh)
    confirm_order(order)
    deliver_order(order)
    invoice_order(order)
    with pytest.raises(NothingToReturnError):
        return_order(order, returned={1: Decimal("0")})
