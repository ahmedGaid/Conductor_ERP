"""Sales quotation lifecycle — submit/approve threshold, convert to a sales order, guards."""
from __future__ import annotations

from decimal import Decimal

import pytest

from erp.sales.domain.models import OrderStatus, QuotationStatus, SalesOrder
from erp.sales.errors import (
    EmptyQuotationError,
    QuotationAlreadyConvertedError,
    QuotationInvalidTransitionError,
)
from erp.sales.services import (
    QuoteLineInput,
    approve_quotation,
    convert_quotation,
    create_quotation,
    reject_quotation,
    submit_quotation,
)

from .factories import make_customer, make_item, make_warehouse

pytestmark = pytest.mark.django_db


def _setup():
    make_item()
    return make_customer(), make_warehouse()


def _quote(customer, wh, qty="10", price=150_00):
    return create_quotation(
        customer=customer, warehouse_code=wh.code,
        lines=[QuoteLineInput(item_sku="WIDGET", quantity=Decimal(qty), unit_price_minor=price)],
    )


def test_small_quotation_auto_approves_on_submit():
    customer, wh = _setup()
    q = _quote(customer, wh)  # 10 @ 150.00 = 1,500.00 (below 10,000 threshold)
    assert q.status == QuotationStatus.DRAFT
    assert q.subtotal_minor == 1500_00
    submit_quotation(q)
    assert q.status == QuotationStatus.APPROVED  # auto-approved
    assert q.approved_at is not None


def test_large_quotation_needs_approval_then_converts():
    customer, wh = _setup()
    q = _quote(customer, wh, qty="100")  # 100 @ 150.00 = 15,000.00 (above threshold)
    submit_quotation(q)
    assert q.status == QuotationStatus.SUBMITTED  # awaits approval

    approve_quotation(q)
    assert q.status == QuotationStatus.APPROVED

    order = convert_quotation(q)
    assert isinstance(order, SalesOrder)
    assert order.status == OrderStatus.DRAFT
    assert order.subtotal_minor == q.subtotal_minor
    q.refresh_from_db()
    assert q.status == QuotationStatus.CONVERTED
    assert q.converted_order_number == order.number


def test_convert_before_approval_rejected():
    customer, wh = _setup()
    q = _quote(customer, wh, qty="100")
    submit_quotation(q)  # submitted, not approved
    with pytest.raises(QuotationInvalidTransitionError):
        convert_quotation(q)


def test_double_convert_rejected():
    customer, wh = _setup()
    q = _quote(customer, wh)  # auto-approves
    submit_quotation(q)
    convert_quotation(q)
    with pytest.raises(QuotationAlreadyConvertedError):
        convert_quotation(q)
    # Exactly one order exists from the single conversion.
    assert SalesOrder.objects.count() == 1


def test_reject_blocks_conversion():
    customer, wh = _setup()
    q = _quote(customer, wh, qty="100")
    submit_quotation(q)
    reject_quotation(q, reason="Customer changed mind")
    assert q.status == QuotationStatus.REJECTED
    with pytest.raises(QuotationInvalidTransitionError):
        convert_quotation(q)


def test_empty_quotation_rejected():
    customer, wh = _setup()
    with pytest.raises(EmptyQuotationError):
        create_quotation(customer=customer, warehouse_code=wh.code, lines=[])
