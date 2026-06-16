"""Purchase request lifecycle — submit/approve threshold, convert to a purchase order, guards."""
from __future__ import annotations

from decimal import Decimal

import pytest

from erp.purchasing.domain.models import POStatus, PRStatus, PurchaseOrder
from erp.purchasing.errors import (
    EmptyRequestError,
    RequestAlreadyConvertedError,
    RequestInvalidTransitionError,
)
from erp.purchasing.services import (
    RequestLineInput,
    approve_request,
    convert_request,
    create_request,
    reject_request,
    submit_request,
)

from .factories import make_item, make_supplier, make_warehouse

pytestmark = pytest.mark.django_db


def _setup():
    make_item()
    return make_supplier(), make_warehouse()


def _req(supplier, wh, qty="10", cost=100_00):
    return create_request(
        supplier=supplier, warehouse_code=wh.code,
        lines=[RequestLineInput(item_sku="WIDGET", quantity=Decimal(qty), unit_cost_minor=cost)],
    )


def test_small_request_auto_approves_on_submit():
    supplier, wh = _setup()
    r = _req(supplier, wh)  # 10 @ 100.00 = 1,000.00 (below threshold)
    assert r.status == PRStatus.DRAFT
    assert r.subtotal_minor == 1000_00
    submit_request(r)
    assert r.status == PRStatus.APPROVED  # auto-approved
    assert r.approved_at is not None


def test_large_request_needs_approval_then_converts():
    supplier, wh = _setup()
    r = _req(supplier, wh, qty="200")  # 200 @ 100.00 = 20,000.00 (above threshold)
    submit_request(r)
    assert r.status == PRStatus.SUBMITTED

    approve_request(r)
    assert r.status == PRStatus.APPROVED

    order = convert_request(r)
    assert isinstance(order, PurchaseOrder)
    assert order.status == POStatus.DRAFT
    assert order.subtotal_minor == r.subtotal_minor
    r.refresh_from_db()
    assert r.status == PRStatus.CONVERTED
    assert r.converted_order_number == order.number


def test_convert_before_approval_rejected():
    supplier, wh = _setup()
    r = _req(supplier, wh, qty="200")
    submit_request(r)
    with pytest.raises(RequestInvalidTransitionError):
        convert_request(r)


def test_double_convert_rejected():
    supplier, wh = _setup()
    r = _req(supplier, wh)  # auto-approves
    submit_request(r)
    convert_request(r)
    with pytest.raises(RequestAlreadyConvertedError):
        convert_request(r)
    assert PurchaseOrder.objects.count() == 1


def test_reject_blocks_conversion():
    supplier, wh = _setup()
    r = _req(supplier, wh, qty="200")
    submit_request(r)
    reject_request(r, reason="Budget frozen")
    assert r.status == PRStatus.REJECTED
    with pytest.raises(RequestInvalidTransitionError):
        convert_request(r)


def test_empty_request_rejected():
    supplier, wh = _setup()
    with pytest.raises(EmptyRequestError):
        create_request(supplier=supplier, warehouse_code=wh.code, lines=[])
