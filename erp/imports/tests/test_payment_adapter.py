"""``payments`` import adapter (purchasing supplier payments) — mirrors test_receipt_adapter.py."""
from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth.models import Group

from erp.identity.models import User
from erp.identity.roles import BRANCH_MANAGER
from erp.imports import engine
from erp.imports.models import ImportBatch, ImportRow
from erp.purchasing.domain.models import PendingPayment, PendingPaymentStatus
from erp.purchasing.services import POLineInput, bill_order, confirm_order, create_order, receive_order

from erp.purchasing.tests.factories import DATE, make_books, make_item, make_supplier, make_warehouse

pytestmark = pytest.mark.django_db


def _manager(username="pay1") -> User:
    bm, _ = Group.objects.get_or_create(name=BRANCH_MANAGER)
    u = User.objects.create_user(username=username, email=f"{username}@erp.local", password="pw12345!", is_superuser=True)
    u.groups.add(bm)
    return u


def _billed_order(supplier, wh):
    order = create_order(
        supplier=supplier, warehouse_code=wh.code, order_date=DATE,
        lines=[POLineInput(item_sku="WIDGET", quantity=Decimal("10"), unit_cost_minor=100_00)],
    )
    confirm_order(order)
    receive_order(order)
    bill_order(order)
    return order


def _row(batch, row_number, normalized):
    return ImportRow.objects.create(batch=batch, row_number=row_number, normalized=normalized, status=ImportRow.Status.VALID)


def test_payment_with_resolvable_order_creates_a_matched_pending_payment():
    make_books()
    make_item()
    wh = make_warehouse()
    supplier = make_supplier(code="SUP1")
    order = _billed_order(supplier, wh)
    actor = _manager()
    batch = ImportBatch.objects.create(entity="payments")
    _row(batch, 1, {"supplier_ref": "SUP1", "amount_minor": 400_00, "date": "2026-06-20",
                    "method": "transfer", "order_ref": order.number})

    report = engine.execute_batch(actor, batch)

    assert report["created"] == 1
    pending = PendingPayment.objects.get()
    assert pending.order_id == order.id
    assert pending.status == PendingPaymentStatus.PENDING


def test_payment_without_a_reference_stays_unmatched_with_a_warning():
    make_books()
    make_item()
    wh = make_warehouse()
    make_supplier(code="SUP2")
    actor = _manager("pay2")
    batch = ImportBatch.objects.create(entity="payments")
    _row(batch, 1, {"supplier_ref": "SUP2", "amount_minor": 200_00, "date": "2026-06-20"})

    report = engine.execute_batch(actor, batch)

    assert report["created"] == 1
    pending = PendingPayment.objects.get()
    assert pending.order_id is None
    row = batch.rows.get(row_number=1)
    assert any(i["code"] == "payment_unmatched" for i in row.issues)


def test_payment_never_touches_the_gl_at_import_time():
    make_books()
    make_item()
    wh = make_warehouse()
    supplier = make_supplier(code="SUP3")
    order = _billed_order(supplier, wh)
    actor = _manager("pay3")
    batch = ImportBatch.objects.create(entity="payments")
    _row(batch, 1, {"supplier_ref": "SUP3", "amount_minor": 400_00, "date": "2026-06-20", "order_ref": order.number})

    engine.execute_batch(actor, batch)

    order.refresh_from_db()
    assert order.paid_minor == 0
