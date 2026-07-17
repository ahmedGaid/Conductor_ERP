"""``inventory_opening`` import adapter — always stages a ``PendingStockEntry``, never posts to the
GL or touches ``StockBalance`` at import time (drafts-only). See DESIGN_PENDING_PAYMENTS_AND_STOCK.md
sub-project 2 and ``erp/inventory/tests/test_pending_stock.py`` for the apply-side behavior."""
from __future__ import annotations

import pytest
from django.contrib.auth.models import Group

from erp.identity.models import User
from erp.identity.roles import BRANCH_MANAGER
from erp.imports import engine
from erp.imports.models import ImportBatch, ImportRow
from erp.inventory.domain.models import PendingStockEntry, PendingStockEntryStatus
from erp.inventory.repositories import balances as balance_repo
from erp.inventory.tests.factories import make_gl, make_item, make_warehouse

pytestmark = pytest.mark.django_db


def _manager(username="opening1") -> User:
    bm, _ = Group.objects.get_or_create(name=BRANCH_MANAGER)
    u = User.objects.create_user(
        username=username, email=f"{username}@erp.local", password="pw12345!", is_superuser=True,
    )
    u.groups.add(bm)
    return u


def _row(batch, row_number, normalized):
    return ImportRow.objects.create(
        batch=batch, row_number=row_number, normalized=normalized, status=ImportRow.Status.VALID,
    )


def test_opening_row_creates_a_pending_entry_not_a_balance_or_gl_posting():
    make_gl()
    item = make_item(sku="WIDGET")
    wh = make_warehouse(code="MAIN")
    actor = _manager()
    batch = ImportBatch.objects.create(entity="inventory_opening")
    _row(batch, 1, {"item_ref": "WIDGET", "warehouse_ref": "MAIN",
                    "quantity": "10", "unit_cost_minor": 100_00, "date": "2026-01-01"})

    report = engine.execute_batch(actor, batch)

    assert report["created"] == 1
    pending = PendingStockEntry.objects.get()
    assert pending.item_id == item.id
    assert pending.warehouse_id == wh.id
    assert pending.status == PendingStockEntryStatus.PENDING
    assert pending.suspense_account == "3110"
    assert balance_repo.for_pair(item, wh) is None  # untouched — applying is a separate step


def test_unknown_item_pauses_the_batch_without_creating_anything():
    """Mirrors every other row-level (ungrouped) adapter today (items/receipts/payments): a
    ``write`` exception aborts the whole chunk's transaction rather than isolating to one row (only
    grouped/document adapters get per-document isolation) — nothing partial is left behind."""
    make_gl()
    make_warehouse(code="MAIN")
    actor = _manager("opening2")
    batch = ImportBatch.objects.create(entity="inventory_opening")
    _row(batch, 1, {"item_ref": "NOPE", "warehouse_ref": "MAIN",
                    "quantity": "10", "unit_cost_minor": 100_00, "date": "2026-01-01"})

    report = engine.execute_batch(actor, batch)

    assert report["created"] == 0
    assert PendingStockEntry.objects.count() == 0
    batch.refresh_from_db()
    assert batch.status == ImportBatch.Status.PAUSED
    assert "unknown item" in batch.stats.get("last_error", "")


def test_rollback_deletes_a_still_pending_entry():
    make_gl()
    make_item(sku="WIDGET")
    make_warehouse(code="MAIN")
    actor = _manager("opening3")
    batch = ImportBatch.objects.create(entity="inventory_opening")
    _row(batch, 1, {"item_ref": "WIDGET", "warehouse_ref": "MAIN",
                    "quantity": "10", "unit_cost_minor": 100_00, "date": "2026-01-01"})
    engine.execute_batch(actor, batch)
    assert PendingStockEntry.objects.count() == 1

    result = engine.rollback_batch(actor, batch)

    assert result == {"reverted": 1, "skipped": 0, "cannot": []}
    assert PendingStockEntry.objects.count() == 0


def test_rollback_refuses_an_applied_entry():
    from erp.inventory.services.pending_stock import apply_pending_stock_opening

    make_gl()
    make_item(sku="WIDGET")
    make_warehouse(code="MAIN")
    actor = _manager("opening4")
    batch = ImportBatch.objects.create(entity="inventory_opening")
    _row(batch, 1, {"item_ref": "WIDGET", "warehouse_ref": "MAIN",
                    "quantity": "10", "unit_cost_minor": 100_00, "date": "2026-01-01"})
    engine.execute_batch(actor, batch)
    apply_pending_stock_opening(PendingStockEntry.objects.get())

    result = engine.rollback_batch(actor, batch)

    assert result["reverted"] == 0
    assert len(result["cannot"]) == 1
    assert PendingStockEntry.objects.count() == 1
