"""Sales order lifecycle — the cross-module order-to-cash flow."""
from __future__ import annotations

from decimal import Decimal

import pytest

from erp.accounting.services import general_ledger, trial_balance
from erp.inventory.errors import InsufficientStockError
from erp.inventory.repositories import balances as balance_repo
from erp.sales.domain.models import OrderStatus
from erp.sales.errors import CreditLimitExceededError, OverpaymentError
from erp.sales.services import (
    OrderLineInput,
    confirm_order,
    create_order,
    deliver_order,
    invoice_order,
    receive_payment,
)

from .factories import DATE, make_books, make_customer, make_item, make_warehouse, stocked

pytestmark = pytest.mark.django_db


def _order(customer, warehouse, qty="10", price=150_00):
    return create_order(
        customer=customer, warehouse_code=warehouse.code, order_date=DATE,
        lines=[OrderLineInput(item_sku="WIDGET", quantity=Decimal(qty), unit_price_minor=price)],
    )


def _setup(credit_limit_minor=0):
    make_books()
    item = make_item()
    wh = make_warehouse()
    stocked(item, wh)  # 20 @ 100.00
    return make_customer(credit_limit_minor=credit_limit_minor), wh


def test_full_order_to_cash_flow_keeps_books_balanced():
    customer, wh = _setup()
    order = _order(customer, wh)
    assert order.status == OrderStatus.DRAFT
    assert order.subtotal_minor == 1500_00

    confirm_order(order)
    assert order.status == OrderStatus.CONFIRMED

    deliver_order(order)
    assert order.status == OrderStatus.DELIVERED
    # Stock reduced 20 -> 10; COGS posted at avg cost (100.00 * 10 = 1000.00)
    assert balance_repo.total_value() == 1000_00
    assert general_ledger("5000").closing_balance == 1000_00

    invoice_order(order)
    assert order.status == OrderStatus.INVOICED
    assert order.invoice_number
    assert general_ledger("1100").closing_balance == 1500_00  # AR
    assert general_ledger("4000").closing_balance == 1500_00  # Revenue

    receive_payment(order, 1500_00)
    assert order.status == OrderStatus.PAID
    assert order.outstanding_minor == 0
    assert general_ledger("1100").closing_balance == 0  # AR settled

    assert trial_balance().is_balanced


def test_inventory_gl_matches_stock_value_after_delivery():
    customer, wh = _setup()
    order = _order(customer, wh)
    confirm_order(order)
    deliver_order(order)
    assert general_ledger("1200").closing_balance == balance_repo.total_value()


def test_credit_limit_blocks_confirm():
    customer, wh = _setup(credit_limit_minor=1000_00)  # order is 1500.00
    order = _order(customer, wh)
    with pytest.raises(CreditLimitExceededError):
        confirm_order(order)
    order.refresh_from_db()
    assert order.status == OrderStatus.DRAFT


def test_delivery_beyond_stock_is_rejected():
    customer, wh = _setup()
    order = _order(customer, wh, qty="50")  # only 20 on hand
    confirm_order(order)
    with pytest.raises(InsufficientStockError):
        deliver_order(order)
    order.refresh_from_db()
    assert order.status == OrderStatus.CONFIRMED
    assert balance_repo.total_value() == 2000_00  # untouched


def test_partial_payment_then_full():
    customer, wh = _setup()
    order = _order(customer, wh)
    confirm_order(order)
    deliver_order(order)
    invoice_order(order)

    receive_payment(order, 500_00)
    assert order.status == OrderStatus.INVOICED
    assert order.outstanding_minor == 1000_00

    receive_payment(order, 1000_00)
    assert order.status == OrderStatus.PAID


def test_overpayment_rejected():
    customer, wh = _setup()
    order = _order(customer, wh)
    confirm_order(order)
    deliver_order(order)
    invoice_order(order)
    with pytest.raises(OverpaymentError):
        receive_payment(order, 2000_00)


def test_unknown_item_rejected_on_create():
    from erp.sales.errors import UnknownItemError

    customer, wh = _setup()
    with pytest.raises(UnknownItemError):
        create_order(
            customer=customer, warehouse_code=wh.code, order_date=DATE,
            lines=[OrderLineInput(item_sku="NOPE", quantity=Decimal("1"), unit_price_minor=100)],
        )
