"""Pre-execution preview of document grouping (FILE_15 CONFIRMED SCOPE, 2026-07-23) —
``validate.validate_batch``/``revalidate_rows`` must surface the same ``total_mismatch``/
``inconsistent_document``/``missing_group_key`` issues ``engine.py`` would produce at execute time,
plus ``group_meta`` for the review API, all BEFORE anything is written. The API's group-aware
pagination (a page holds whole documents) is covered at the bottom.
"""
from __future__ import annotations

import pytest
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from erp.identity.models import User
from erp.identity.roles import BRANCH_MANAGER
from erp.imports import engine, grouping, validate
from erp.imports.models import ImportBatch, ImportRow
from erp.inventory.domain.models import Item, Warehouse
from erp.sales.domain.models import Customer

pytestmark = pytest.mark.django_db


def _manager(username: str) -> User:
    bm, _ = Group.objects.get_or_create(name=BRANCH_MANAGER)
    u = User.objects.create_user(
        username=username, email=f"{username}@erp.local", password="pw12345!", is_superuser=True,
    )
    u.groups.add(bm)
    return u


def _row(batch, row_number, normalized, *, status=ImportRow.Status.VALID) -> ImportRow:
    return ImportRow.objects.create(batch=batch, row_number=row_number, normalized=normalized, status=status)


def _batch(entity, strategy=ImportBatch.Strategy.CREATE_ONLY) -> ImportBatch:
    return ImportBatch.objects.create(entity=entity, strategy=strategy)


@pytest.fixture()
def sales_world():
    Warehouse.objects.create(code="MAIN", name="Main")
    Item.objects.create(sku="WIDGET", name="Widget", type="stock")
    Customer.objects.create(code="C1", name="Acme Corp")
    Customer.objects.create(code="C2", name="Globex")


def _line(**over):
    base = {"item_ref": "WIDGET", "quantity": "2", "unit_price_minor": 10_00}
    base.update(over)
    return base


def _header(**over):
    base = {
        "doc_number": "INV-1", "customer_ref": "C1", "date": "2026-06-01",
        "currency": "EGP", "warehouse_ref": "MAIN",
    }
    base.update(over)
    return base


def test_total_mismatch_visible_before_execute(sales_world):
    actor = _manager("gp1")
    batch = _batch("sales_invoices")
    _row(batch, 1, {**_header(file_total_minor=999_99), **_line(quantity="1", unit_price_minor=10_00)})

    validate.validate_batch(actor, batch)

    row = batch.rows.get(row_number=1)
    assert row.status == ImportRow.Status.VALID  # a warning never blocks
    issue = next(i for i in row.issues if i["code"] == "total_mismatch")
    assert issue["meta"] == {"file_total_minor": 999_99, "computed_total_minor": 10_00}
    assert row.group_meta["computed_total_minor"] == 10_00
    assert row.group_meta["is_first"] is True
    assert row.group_meta["line_count"] == 1
    assert row.group_meta["header"]["doc_number"] == "INV-1"


def test_inconsistent_document_errors_before_execute(sales_world):
    actor = _manager("gp2")
    batch = _batch("sales_invoices")
    _row(batch, 1, {**_header(customer_ref="C1"), **_line()})
    _row(batch, 2, {**_header(customer_ref="C2"), **_line()})

    validate.validate_batch(actor, batch)

    rows = list(batch.rows.all())
    for row in rows:
        assert row.status == ImportRow.Status.ERROR
        assert any(i["code"] == "inconsistent_document" for i in row.issues)
    assert rows[0].group_meta["group_id"] == rows[1].group_meta["group_id"]


def test_missing_group_key_errors_before_execute(sales_world):
    actor = _manager("gp3")
    batch = _batch("sales_invoices")
    _row(batch, 1, _line())  # no doc_number, nothing to attach to

    validate.validate_batch(actor, batch)

    row = batch.rows.get(row_number=1)
    assert row.status == ImportRow.Status.ERROR
    assert any(i["code"] == "missing_group_key" for i in row.issues)


def test_preview_matches_execute_issue_exactly(sales_world):
    """Guards the FILE_15 promise: preview and execute must never disagree."""
    actor = _manager("gp4")
    batch = _batch("sales_invoices")
    _row(batch, 1, {**_header(file_total_minor=1_00), **_line(quantity="1", unit_price_minor=10_00)})

    validate.validate_batch(actor, batch)
    preview_issue = next(i for i in batch.rows.get(row_number=1).issues if i["code"] == "total_mismatch")

    engine.execute_batch(actor, batch)
    execute_issue = next(i for i in batch.rows.get(row_number=1).issues if i["code"] == "total_mismatch")

    assert preview_issue["meta"] == execute_issue["meta"]


def test_annotate_groups_is_idempotent(sales_world):
    actor = _manager("gp5")
    batch = _batch("sales_invoices")
    _row(batch, 1, {**_header(file_total_minor=999_99), **_line(quantity="1", unit_price_minor=10_00)})

    validate.validate_batch(actor, batch)
    validate.validate_batch(actor, batch)  # re-run, as a re-map would

    row = batch.rows.get(row_number=1)
    codes = [i["code"] for i in row.issues]
    assert codes.count("total_mismatch") == 1


def test_revalidate_rows_reannotates_whole_group_on_edit(sales_world):
    actor = _manager("gp6")
    batch = _batch("sales_invoices")
    _row(batch, 1, {**_header(file_total_minor=999_99), **_line(quantity="1", unit_price_minor=10_00)})
    validate.validate_batch(actor, batch)
    row = batch.rows.get(row_number=1)
    assert any(i["code"] == "total_mismatch" for i in row.issues)

    row.decision = {"edits": {"file_total_minor": 10_00}}
    row.save(update_fields=["decision"])
    validate.revalidate_rows(actor, batch, [row.id])

    row.refresh_from_db()
    assert not any(i["code"] == "total_mismatch" for i in row.issues)
    assert row.group_meta["computed_total_minor"] == 10_00


def test_compute_subtotal_minor_matches_the_real_service(sales_world):
    """The pure preview estimate must stay in lockstep with the module service's own arithmetic —
    the whole point of previewing a number before anything is written."""
    actor = _manager("gp7")
    batch = _batch("sales_invoices")
    _row(batch, 1, {**_header(), **_line(quantity="3", unit_price_minor=17_50, discount_minor=5_00)})

    rows = list(batch.rows.all())
    estimate = grouping.compute_subtotal_minor(rows)

    engine.execute_batch(actor, batch)
    from erp.sales.domain.models import SalesOrder
    order = SalesOrder.objects.get(notes="import:INV-1")
    assert estimate == order.subtotal_minor


def test_ungrouped_entity_gets_no_group_meta():
    """Master adapters (``group_by`` unset) must see zero change — group_meta stays empty."""
    Customer.objects.create(code="C9", name="Zeta Co")
    actor = _manager("gp8")
    batch = _batch("customers")
    _row(batch, 1, {"code": "C10", "name": "Eta Co"})

    validate.validate_batch(actor, batch)

    row = batch.rows.get(row_number=1)
    assert row.group_meta == {}


# --- API: group-aware pagination ------------------------------------------------------------
def _api_manager_client(username: str) -> APIClient:
    user = _manager(username)
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def test_batch_rows_api_paginates_by_whole_document(sales_world):
    actor = _manager("gp9")
    batch = _batch("sales_invoices")
    # INV-1: 2 lines. INV-2: 1 line. INV-3: 1 line.
    _row(batch, 1, {**_header(doc_number="INV-1"), **_line()})
    _row(batch, 2, _line())
    _row(batch, 3, {**_header(doc_number="INV-2", customer_ref="C2"), **_line()})
    _row(batch, 4, {**_header(doc_number="INV-3"), **_line()})
    validate.validate_batch(actor, batch)

    client = APIClient()
    client.force_authenticate(user=actor)
    # page_size=2 "documents" — INV-1 (2 rows) must land whole on page 1, never split.
    res = client.get(f"/api/imports/{batch.pk}/rows?page=1&page_size=2")
    assert res.status_code == 200
    body = res.json()["data"]
    assert body["total"] == 3  # three DOCUMENTS, not four rows
    row_numbers = [r["row_number"] for r in body["rows"]]
    assert row_numbers == [1, 2, 3]  # INV-1's two rows plus INV-2's one row — INV-3 held for page 2

    res2 = client.get(f"/api/imports/{batch.pk}/rows?page=2&page_size=2")
    body2 = res2.json()["data"]
    assert [r["row_number"] for r in body2["rows"]] == [4]


def test_batch_rows_api_filtered_tab_stays_row_based(sales_world):
    """A status filter keeps today's flat row pagination — group-aware paging only applies to the
    unfiltered ("all") view (FILE_15 CONFIRMED SCOPE: "Tab counts stay row-based")."""
    actor = _manager("gp10")
    batch = _batch("sales_invoices")
    _row(batch, 1, {**_header(customer_ref="C1"), **_line()})
    _row(batch, 2, {**_header(doc_number="INV-4", customer_ref="C2"), **_line()})
    validate.validate_batch(actor, batch)

    client = APIClient()
    client.force_authenticate(user=actor)
    res = client.get(f"/api/imports/{batch.pk}/rows?status=valid&page=1&page_size=1")
    body = res.json()["data"]
    assert body["total"] == 2  # ROW count, unchanged meaning
    assert len(body["rows"]) == 1
