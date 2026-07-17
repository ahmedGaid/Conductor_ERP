"""Document adapters: sales_invoices + purchase_invoices, and the engine's group-by support they
exercise (FILE_15 Task A/B, PARTIAL scope — quotations/orders/purchase_orders adapters deferred).

Flat-Excel reality: one row per LINE, header fields (customer, date, …) repeated or filled only on
the group's first row (the merged-cell export pattern). These tests build ``ImportRow`` fixtures
directly with the shape ``analyze``/``normalize_row`` would have produced — same convention
``test_engine.py`` already uses — so they exercise ``engine.execute_batch``/``rollback_batch``
without needing a real uploaded file.
"""
from __future__ import annotations

import datetime as dt

import pytest
from django.contrib.auth.models import Group

from erp.identity.models import User
from erp.identity.roles import BRANCH_MANAGER
from erp.imports import engine
from erp.imports.models import ImportBatch, ImportRow
from erp.inventory.domain.models import Item, Warehouse
from erp.purchasing.domain.models import PurchaseOrder, Supplier
from erp.sales.domain.models import Customer, SalesOrder

pytestmark = pytest.mark.django_db


# --- helpers ---------------------------------------------------------------------------------
def _manager(username: str) -> User:
    """A superuser: satisfies ``require_role`` (bypasses the check outright) AND
    ``scope_queryset``'s ``is_superadmin`` (ALL scope) — these tests read pre-existing
    customers/suppliers a plain ``BRANCH_MANAGER`` group membership has no RBAC ``RolePermission``
    row for, so it would default to ``DataScope.OWN`` and see none of them."""
    bm, _ = Group.objects.get_or_create(name=BRANCH_MANAGER)
    u = User.objects.create_user(
        username=username, email=f"{username}@erp.local", password="pw12345!", is_superuser=True,
    )
    u.groups.add(bm)
    return u


def _row(batch, row_number, normalized, *, status=ImportRow.Status.VALID) -> ImportRow:
    return ImportRow.objects.create(
        batch=batch, row_number=row_number, normalized=normalized, status=status,
    )


def _batch(entity, strategy=ImportBatch.Strategy.CREATE_ONLY) -> ImportBatch:
    return ImportBatch.objects.create(entity=entity, strategy=strategy)


# --- sales fixtures ----------------------------------------------------------------------------
@pytest.fixture()
def sales_world():
    Warehouse.objects.create(code="MAIN", name="Main")
    Item.objects.create(sku="WIDGET", name="Widget", type="stock")
    Customer.objects.create(code="C1", name="Acme Corp")
    Customer.objects.create(code="C2", name="Globex")


def _sales_line(**over):
    base = {
        "item_ref": "WIDGET", "quantity": "2", "unit_price_minor": 10_00, "discount_minor": 0,
    }
    base.update(over)
    return base


def _sales_header(**over):
    base = {
        "doc_number": "INV-1", "customer_ref": "C1", "date": "2026-06-01",
        "currency": "EGP", "warehouse_ref": "MAIN",
    }
    base.update(over)
    return base


# --- bullet 1: groups build right; drafts created; lines exact; totals computed -----------------
def test_group_by_builds_documents_and_computes_totals(sales_world):
    actor = _manager("si1")
    batch = _batch("sales_invoices")
    # INV-1: header on row 1, row 2 is a merged-cell continuation (blank header fields).
    _row(batch, 1, {**_sales_header(doc_number="INV-1"), **_sales_line(quantity="2")})
    _row(batch, 2, _sales_line(item_ref="WIDGET", quantity="3"))
    # INV-2: its own header, one line.
    _row(batch, 3, {**_sales_header(doc_number="INV-2", customer_ref="C2"), **_sales_line(quantity="1")})

    report = engine.execute_batch(actor, batch)

    assert report["created"] == 3  # three rows imported (report counts rows, not documents)
    assert SalesOrder.objects.count() == 2  # ...but only two documents were written
    orders = {o.notes: o for o in SalesOrder.objects.all()}
    assert set(orders) == {"import:INV-1", "import:INV-2"}

    inv1 = orders["import:INV-1"]
    assert inv1.customer.code == "C1"
    assert inv1.status == "draft"
    lines = list(inv1.lines.order_by("line_no"))
    assert [str(l.quantity) for l in lines] == ["2.0000", "3.0000"]
    assert inv1.subtotal_minor == 2 * 10_00 + 3 * 10_00

    inv2 = orders["import:INV-2"]
    assert inv2.customer.code == "C2"
    assert inv2.subtotal_minor == 1 * 10_00

    assert set(batch.rows.values_list("status", flat=True)) == {ImportRow.Status.IMPORTED}


def test_total_mismatch_produces_a_warning_not_an_error(sales_world):
    actor = _manager("si2")
    batch = _batch("sales_invoices")
    _row(batch, 1, {
        **_sales_header(doc_number="INV-3", file_total_minor=999_99),
        **_sales_line(quantity="1", unit_price_minor=10_00),
    })

    report = engine.execute_batch(actor, batch)

    assert report["created"] == 1  # the mismatch never blocks the import
    row = batch.rows.get(row_number=1)
    assert row.status == ImportRow.Status.IMPORTED
    codes = [i["code"] for i in row.issues]
    assert "total_mismatch" in codes
    issue = next(i for i in row.issues if i["code"] == "total_mismatch")
    assert issue["meta"] == {"file_total_minor": 999_99, "computed_total_minor": 10_00}


def test_inconsistent_customer_within_one_invoice_number_errors_the_whole_group(sales_world):
    actor = _manager("si3")
    batch = _batch("sales_invoices")
    _row(batch, 1, {**_sales_header(doc_number="INV-4", customer_ref="C1"), **_sales_line()})
    _row(batch, 2, {**_sales_header(doc_number="INV-4", customer_ref="C2"), **_sales_line()})

    report = engine.execute_batch(actor, batch)

    assert report["created"] == 0
    assert not SalesOrder.objects.exists()
    for row in batch.rows.all():
        assert row.status == ImportRow.Status.ERROR
        assert any(i["code"] == "inconsistent_document" for i in row.issues)


def test_group_atomicity_on_write_failure_only_errors_that_document(sales_world):
    Item.objects.create(sku="SVC1", name="Consulting", type="service")  # rejected by create_order
    actor = _manager("si4")
    batch = _batch("sales_invoices")
    _row(batch, 1, {**_sales_header(doc_number="INV-5"), **_sales_line(item_ref="WIDGET")})
    _row(batch, 2, {**_sales_header(doc_number="INV-6", customer_ref="C2"), **_sales_line(item_ref="SVC1")})

    report = engine.execute_batch(actor, batch)

    assert report["created"] == 1
    assert SalesOrder.objects.filter(notes="import:INV-5").exists()
    assert not SalesOrder.objects.filter(notes="import:INV-6").exists()
    bad_row = batch.rows.get(row_number=2)
    assert bad_row.status == ImportRow.Status.ERROR
    assert any(i["code"] == "group_write_failed" for i in bad_row.issues)


def test_existing_invoice_number_skipped_under_skip_existing_strategy(sales_world):
    customer = Customer.objects.get(code="C1")
    SalesOrder.objects.create(
        number="SO-2026-000001", customer=customer, order_date=dt.date(2026, 1, 1),
        warehouse_code="MAIN", notes="import:INV-9",
    )
    actor = _manager("si5")
    batch = _batch("sales_invoices", strategy=ImportBatch.Strategy.SKIP_EXISTING)
    _row(batch, 1, {**_sales_header(doc_number="INV-9"), **_sales_line()})

    report = engine.execute_batch(actor, batch)

    assert report["created"] == 0
    assert report["skipped"] == 1
    assert SalesOrder.objects.filter(notes="import:INV-9").count() == 1


def test_orphan_blank_group_key_row_errors_as_missing_group_key(sales_world):
    actor = _manager("si6")
    batch = _batch("sales_invoices")
    _row(batch, 1, _sales_line())  # no doc_number, no header data, nothing to attach to

    report = engine.execute_batch(actor, batch)

    assert report["created"] == 0
    row = batch.rows.get(row_number=1)
    assert row.status == ImportRow.Status.ERROR
    assert any(i["code"] == "missing_group_key" for i in row.issues)


def test_rollback_deletes_the_drafts(sales_world):
    actor = _manager("si7")
    batch = _batch("sales_invoices")
    _row(batch, 1, {**_sales_header(doc_number="INV-7"), **_sales_line(quantity="1")})
    _row(batch, 2, _sales_line(item_ref="WIDGET", quantity="1"))  # 2nd line, same document
    engine.execute_batch(actor, batch)
    assert SalesOrder.objects.filter(notes="import:INV-7").exists()

    result = engine.rollback_batch(actor, batch)

    assert result == {"reverted": 1, "skipped": 0, "cannot": []}  # one DOCUMENT, not two rows
    assert not SalesOrder.objects.filter(notes="import:INV-7").exists()
    assert set(batch.rows.values_list("status", flat=True)) == {ImportRow.Status.REVERTED}


# --- bullet 3: purchase invoice path, supplier-side ---------------------------------------------
def test_purchase_invoice_path_creates_draft_purchase_order_supplier_side():
    Warehouse.objects.create(code="MAIN", name="Main")
    Item.objects.create(sku="WIDGET", name="Widget", type="stock")
    Supplier.objects.create(code="S1", name="Globex Supplies")
    actor = _manager("pi1")
    batch = _batch("purchase_invoices")
    header = {
        "doc_number": "BILL-1", "supplier_ref": "S1", "date": "2026-06-01",
        "currency": "EGP", "warehouse_ref": "MAIN",
    }
    line = {"item_ref": "WIDGET", "quantity": "5", "unit_price_minor": 8_00}
    _row(batch, 1, {**header, **line})
    _row(batch, 2, {"item_ref": "WIDGET", "quantity": "1", "unit_price_minor": 8_00})

    report = engine.execute_batch(actor, batch)

    assert report["created"] == 2  # two rows imported (report counts rows, not documents)
    assert PurchaseOrder.objects.count() == 1
    order = PurchaseOrder.objects.get(notes="import:BILL-1")
    assert order.supplier.code == "S1"
    assert order.status == "draft"
    lines = list(order.lines.order_by("line_no"))
    assert [str(l.quantity) for l in lines] == ["5.0000", "1.0000"]
    assert order.subtotal_minor == 6 * 8_00
