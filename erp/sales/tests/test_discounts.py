"""Sales line discounts (net method) + the amount-threshold approval gate at confirm."""
from __future__ import annotations

from decimal import Decimal

import pytest

from erp.accounting.services import general_ledger, trial_balance
from erp.sales.domain.models import OrderStatus
from erp.sales.errors import ApprovalRequiredError, InvalidDiscountError
from erp.sales.services import (
    OrderLineInput,
    approve_order,
    confirm_order,
    create_order,
    deliver_order,
    invoice_order,
    return_order,
)

from .factories import DATE, make_books, make_customer, make_item, make_warehouse, stocked

pytestmark = pytest.mark.django_db


def _setup(credit_limit_minor=0):
    make_books()
    item = make_item()
    wh = make_warehouse()
    stocked(item, wh)  # 20 @ 100.00
    return make_customer(credit_limit_minor=credit_limit_minor), wh


def test_line_discount_reduces_line_total_and_subtotal():
    customer, wh = _setup()
    order = create_order(
        customer=customer, warehouse_code=wh.code, order_date=DATE,
        lines=[OrderLineInput(item_sku="WIDGET", quantity=Decimal("10"), unit_price_minor=150_00,
                              discount_minor=300_00)],  # gross 1500.00 - 300.00
    )
    line = order.lines.get(line_no=1)
    assert line.discount_minor == 300_00
    assert line.line_total_minor == 1200_00
    assert order.subtotal_minor == 1200_00


def test_invoice_posts_net_revenue_and_books_balance():
    customer, wh = _setup()
    order = create_order(
        customer=customer, warehouse_code=wh.code, order_date=DATE,
        lines=[OrderLineInput(item_sku="WIDGET", quantity=Decimal("10"), unit_price_minor=150_00,
                              discount_minor=300_00)],
    )
    confirm_order(order)
    deliver_order(order)
    invoice_order(order)
    assert general_ledger("1100").closing_balance == 1200_00  # AR = net
    assert general_ledger("4000").closing_balance == 1200_00  # Revenue = net
    assert trial_balance().is_balanced


def test_return_credits_net_unit_value_with_discount():
    customer, wh = _setup()
    order = create_order(
        customer=customer, warehouse_code=wh.code, order_date=DATE,
        lines=[OrderLineInput(item_sku="WIDGET", quantity=Decimal("10"), unit_price_minor=150_00,
                              discount_minor=300_00)],  # net 1200.00 over 10 units = 120.00/unit
    )
    confirm_order(order)
    deliver_order(order)
    invoice_order(order)
    return_order(order, returned={1: Decimal("4")})  # 4 * 120.00 = 480.00 credited
    order.refresh_from_db()
    assert order.returned_minor == 480_00
    assert order.outstanding_minor == 720_00  # 1200 - 480
    assert trial_balance().is_balanced


def test_negative_or_excess_discount_rejected():
    customer, wh = _setup()
    with pytest.raises(InvalidDiscountError):
        create_order(
            customer=customer, warehouse_code=wh.code, order_date=DATE,
            lines=[OrderLineInput(item_sku="WIDGET", quantity=Decimal("1"), unit_price_minor=100_00,
                                  discount_minor=200_00)],  # discount > gross
        )


def test_large_order_blocks_confirm_until_approved():
    customer, wh = _setup()
    # 100 @ 150.00 = 15,000.00 > 10,000.00 threshold.
    order = create_order(
        customer=customer, warehouse_code=wh.code, order_date=DATE,
        lines=[OrderLineInput(item_sku="WIDGET", quantity=Decimal("100"), unit_price_minor=150_00)],
    )
    with pytest.raises(ApprovalRequiredError):
        confirm_order(order)
    order.refresh_from_db()
    assert order.status == OrderStatus.DRAFT

    approve_order(order)
    confirm_order(order)
    order.refresh_from_db()
    assert order.status == OrderStatus.CONFIRMED
    assert order.approved is True


def test_small_order_confirms_without_approval():
    customer, wh = _setup()
    order = create_order(
        customer=customer, warehouse_code=wh.code, order_date=DATE,
        lines=[OrderLineInput(item_sku="WIDGET", quantity=Decimal("10"), unit_price_minor=150_00)],
    )  # 1,500.00 < threshold
    confirm_order(order)
    assert order.status == OrderStatus.CONFIRMED
    assert order.approved is False
