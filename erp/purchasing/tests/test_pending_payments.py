"""Draftable supplier payments — mirrors erp/sales/tests/test_pending_payments.py exactly."""
from __future__ import annotations

from decimal import Decimal

import pytest

from erp.purchasing.domain.models import PendingPaymentStatus, POStatus
from erp.purchasing.errors import OverpaymentError, PendingPaymentStateError
from erp.purchasing.services import POLineInput, bill_order, confirm_order, create_order, receive_order
from erp.purchasing.services.pending_payments import (
    apply_pending_payment,
    create_pending_payment,
    discard_pending_payment,
    match_pending_payment,
)

from .factories import DATE, make_books, make_item, make_supplier, make_warehouse

pytestmark = pytest.mark.django_db


def _billed_order(amount=1000_00):
    make_books()
    make_item()
    wh = make_warehouse()
    supplier = make_supplier()
    order = create_order(
        supplier=supplier, warehouse_code=wh.code, order_date=DATE,
        lines=[POLineInput(item_sku="WIDGET", quantity=Decimal("10"), unit_cost_minor=100_00)],
    )
    confirm_order(order)
    receive_order(order)
    bill_order(order)
    assert order.billed_minor == amount
    return supplier, order


def test_apply_matched_payment_reproduces_pay_order_behavior():
    supplier, order = _billed_order()
    pending = create_pending_payment(
        order=order, party_code=supplier.code, amount_minor=400_00, date=DATE, method="transfer",
    )

    applied = apply_pending_payment(pending)

    assert applied.status == PendingPaymentStatus.APPLIED
    order.refresh_from_db()
    assert order.status == POStatus.BILLED  # partial
    assert order.outstanding_minor == 600_00


def test_apply_without_a_matched_order_raises():
    _, order = _billed_order()
    pending = create_pending_payment(order=None, party_code="SUP1", amount_minor=400_00, date=DATE)

    with pytest.raises(PendingPaymentStateError):
        apply_pending_payment(pending)


def test_match_then_apply_round_trips():
    supplier, order = _billed_order()
    pending = create_pending_payment(order=None, party_code=supplier.code, amount_minor=1000_00, date=DATE)

    matched = match_pending_payment(pending, order)
    applied = apply_pending_payment(matched)

    assert applied.status == PendingPaymentStatus.APPLIED
    order.refresh_from_db()
    assert order.status == POStatus.PAID


def test_apply_already_applied_raises():
    supplier, order = _billed_order()
    pending = create_pending_payment(order=order, party_code=supplier.code, amount_minor=400_00, date=DATE)
    apply_pending_payment(pending)

    with pytest.raises(PendingPaymentStateError):
        apply_pending_payment(pending)


def test_apply_overpayment_still_raises_the_existing_guard():
    supplier, order = _billed_order()
    pending = create_pending_payment(order=order, party_code=supplier.code, amount_minor=5000_00, date=DATE)

    with pytest.raises(OverpaymentError):
        apply_pending_payment(pending)


def test_discard_marks_discarded_and_blocks_further_actions():
    supplier, order = _billed_order()
    pending = create_pending_payment(order=order, party_code=supplier.code, amount_minor=400_00, date=DATE)

    discarded = discard_pending_payment(pending)

    assert discarded.status == PendingPaymentStatus.DISCARDED
    with pytest.raises(PendingPaymentStateError):
        apply_pending_payment(discarded)
