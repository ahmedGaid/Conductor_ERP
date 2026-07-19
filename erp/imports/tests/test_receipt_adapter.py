"""``receipts`` import adapter (sales customer receipts) — always creates a PendingPayment, never
posts to the GL. See DESIGN_PENDING_PAYMENTS_AND_STOCK.md."""
from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth.models import Group

from erp.identity.models import User
from erp.identity.roles import BRANCH_MANAGER
from erp.imports import engine
from erp.imports.models import ImportBatch, ImportRow
from erp.sales.domain.models import PendingPayment, PendingPaymentStatus
from erp.sales.services import (
    OrderLineInput,
    confirm_order,
    create_order,
    deliver_order,
    invoice_order,
)
from erp.sales.tests.factories import (
    DATE,
    make_books,
    make_customer,
    make_item,
    make_warehouse,
    stocked,
)

pytestmark = pytest.mark.django_db


def _manager(username="rcpt1") -> User:
    bm, _ = Group.objects.get_or_create(name=BRANCH_MANAGER)
    u = User.objects.create_user(username=username, email=f"{username}@erp.local", password="pw12345!", is_superuser=True)
    u.groups.add(bm)
    return u


def _invoiced_order(customer, wh):
    order = create_order(
        customer=customer, warehouse_code=wh.code, order_date=DATE,
        lines=[OrderLineInput(item_sku="WIDGET", quantity=Decimal("10"), unit_price_minor=150_00)],
    )
    confirm_order(order)
    deliver_order(order)
    invoice_order(order)
    return order


def _row(batch, row_number, normalized):
    return ImportRow.objects.create(batch=batch, row_number=row_number, normalized=normalized, status=ImportRow.Status.VALID)


def test_receipt_with_resolvable_order_creates_a_matched_pending_payment():
    make_books()
    item = make_item()
    wh = make_warehouse()
    stocked(item, wh)
    customer = make_customer(code="CUST1")
    order = _invoiced_order(customer, wh)
    actor = _manager()
    batch = ImportBatch.objects.create(entity="receipts")
    _row(batch, 1, {"customer_ref": "CUST1", "amount_minor": 500_00, "date": "2026-06-20",
                    "method": "cash", "order_ref": order.number})

    report = engine.execute_batch(actor, batch)

    assert report["created"] == 1
    pending = PendingPayment.objects.get()
    assert pending.order_id == order.id
    assert pending.status == PendingPaymentStatus.PENDING
    assert pending.amount_minor == 500_00
    row = batch.rows.get(row_number=1)
    assert row.issues == []  # matched — no warning


def test_receipt_without_a_reference_stays_unmatched_with_a_warning():
    make_books()
    item = make_item()
    wh = make_warehouse()
    stocked(item, wh)
    make_customer(code="CUST2")
    actor = _manager("rcpt2")
    batch = ImportBatch.objects.create(entity="receipts")
    _row(batch, 1, {"customer_ref": "CUST2", "amount_minor": 300_00, "date": "2026-06-20", "method": ""})

    report = engine.execute_batch(actor, batch)

    assert report["created"] == 1
    pending = PendingPayment.objects.get()
    assert pending.order_id is None
    row = batch.rows.get(row_number=1)
    assert any(i["code"] == "payment_unmatched" for i in row.issues)


def test_receipt_never_touches_the_gl_at_import_time():
    make_books()
    item = make_item()
    wh = make_warehouse()
    stocked(item, wh)
    customer = make_customer(code="CUST3")
    order = _invoiced_order(customer, wh)
    actor = _manager("rcpt3")
    batch = ImportBatch.objects.create(entity="receipts")
    _row(batch, 1, {"customer_ref": "CUST3", "amount_minor": 500_00, "date": "2026-06-20", "order_ref": order.number})

    engine.execute_batch(actor, batch)

    order.refresh_from_db()
    assert order.paid_minor == 0  # untouched — applying is a separate, human-triggered step


def test_receipt_method_normalizes_arabic_tokens():
    make_books()
    item = make_item()
    wh = make_warehouse()
    stocked(item, wh)
    customer = make_customer(code="CUST4")
    order = _invoiced_order(customer, wh)
    actor = _manager("rcpt4")
    batch = ImportBatch.objects.create(entity="receipts")
    _row(batch, 1, {"customer_ref": "CUST4", "amount_minor": 100_00, "date": "2026-06-20",
                    "method": "نقدي", "order_ref": order.number})

    engine.execute_batch(actor, batch)

    assert PendingPayment.objects.get().method == "cash"
