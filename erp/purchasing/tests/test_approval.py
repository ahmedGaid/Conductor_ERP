"""Purchasing amount-threshold approval gate at confirm."""
from __future__ import annotations

from decimal import Decimal

import pytest

from erp.purchasing.domain.models import POStatus
from erp.purchasing.errors import ApprovalRequiredError
from erp.purchasing.services import (
    POLineInput,
    approve_order,
    confirm_order,
    create_order,
)

from .factories import make_books, make_item, make_supplier, make_warehouse

pytestmark = pytest.mark.django_db


def _setup():
    make_books()
    make_item()
    return make_supplier(), make_warehouse()


def test_large_po_blocks_confirm_until_approved():
    supplier, wh = _setup()
    # 200 @ 100.00 = 20,000.00 > 10,000.00 threshold.
    order = create_order(
        supplier=supplier, warehouse_code=wh.code,
        lines=[POLineInput(item_sku="WIDGET", quantity=Decimal("200"), unit_cost_minor=100_00)],
    )
    with pytest.raises(ApprovalRequiredError):
        confirm_order(order)
    order.refresh_from_db()
    assert order.status == POStatus.DRAFT

    approve_order(order)
    confirm_order(order)
    order.refresh_from_db()
    assert order.status == POStatus.CONFIRMED
    assert order.approved is True


def test_small_po_confirms_without_approval():
    supplier, wh = _setup()
    order = create_order(
        supplier=supplier, warehouse_code=wh.code,
        lines=[POLineInput(item_sku="WIDGET", quantity=Decimal("10"), unit_cost_minor=100_00)],
    )  # 1,000.00 < threshold
    confirm_order(order)
    assert order.status == POStatus.CONFIRMED
    assert order.approved is False
