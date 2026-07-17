"""Draftable customer receipts — PendingPayment stages a payment; applying it calls the existing
``receive_payment`` exactly as the module screen would (same guards, same GL entry)."""
from __future__ import annotations

from decimal import Decimal

import pytest

from erp.sales.domain.models import OrderStatus, PendingPaymentStatus
from erp.sales.errors import OverpaymentError, PendingPaymentStateError
from erp.sales.services import (
    OrderLineInput,
    confirm_order,
    create_order,
    deliver_order,
    invoice_order,
)
from erp.sales.services.pending_payments import (
    apply_pending_payment,
    create_pending_payment,
    discard_pending_payment,
    match_pending_payment,
)

from .factories import DATE, make_books, make_customer, make_item, make_warehouse, stocked

pytestmark = pytest.mark.django_db


def _invoiced_order(amount=1500_00):
    make_books()
    item = make_item()
    wh = make_warehouse()
    stocked(item, wh)
    customer = make_customer()
    order = create_order(
        customer=customer, warehouse_code=wh.code, order_date=DATE,
        lines=[OrderLineInput(item_sku="WIDGET", quantity=Decimal("10"), unit_price_minor=150_00)],
    )
    confirm_order(order)
    deliver_order(order)
    invoice_order(order)
    assert order.invoiced_minor == amount
    return customer, order


def test_apply_matched_payment_reproduces_receive_payment_behavior():
    customer, order = _invoiced_order()
    pending = create_pending_payment(
        order=order, party_code=customer.code, amount_minor=500_00, date=DATE, method="cash",
    )
    assert pending.status == PendingPaymentStatus.PENDING

    applied = apply_pending_payment(pending)

    assert applied.status == PendingPaymentStatus.APPLIED
    assert applied.applied_at is not None
    order.refresh_from_db()
    assert order.status == OrderStatus.INVOICED  # partial — not fully paid yet
    assert order.outstanding_minor == 1000_00


def test_apply_without_a_matched_order_raises():
    _, order = _invoiced_order()
    pending = create_pending_payment(order=None, party_code="CUST1", amount_minor=500_00, date=DATE)

    with pytest.raises(PendingPaymentStateError):
        apply_pending_payment(pending)


def test_match_then_apply_round_trips():
    customer, order = _invoiced_order()
    pending = create_pending_payment(order=None, party_code=customer.code, amount_minor=1500_00, date=DATE)

    matched = match_pending_payment(pending, order)
    assert matched.order_id == order.id

    applied = apply_pending_payment(matched)
    assert applied.status == PendingPaymentStatus.APPLIED
    order.refresh_from_db()
    assert order.status == OrderStatus.PAID


def test_apply_already_applied_raises():
    customer, order = _invoiced_order()
    pending = create_pending_payment(order=order, party_code=customer.code, amount_minor=500_00, date=DATE)
    apply_pending_payment(pending)

    with pytest.raises(PendingPaymentStateError):
        apply_pending_payment(pending)


def test_apply_overpayment_still_raises_the_existing_guard():
    customer, order = _invoiced_order()
    pending = create_pending_payment(order=order, party_code=customer.code, amount_minor=2000_00, date=DATE)

    with pytest.raises(OverpaymentError):
        apply_pending_payment(pending)


def test_discard_marks_discarded_and_blocks_further_actions():
    customer, order = _invoiced_order()
    pending = create_pending_payment(order=order, party_code=customer.code, amount_minor=500_00, date=DATE)

    discarded = discard_pending_payment(pending)

    assert discarded.status == PendingPaymentStatus.DISCARDED
    with pytest.raises(PendingPaymentStateError):
        apply_pending_payment(discarded)
    with pytest.raises(PendingPaymentStateError):
        discard_pending_payment(discarded)
