"""End-to-end: multi-supplier item resolution through the real purchase-invoice import flow.

Proves the bug fix at the ingestion boundary: an incoming supplier invoice line whose code/name does
NOT match any canonical item resolves to the RIGHT existing item via the supplier alias (no duplicate
item), and an unmatched line's confirmed creation is captured as an alias so the next document from
that supplier resolves deterministically. Rows are built the same way ``test_document_adapters.py``
builds them — the normalized shape ``analyze`` would produce — so the test drives validate → plan →
execute without a real upload.
"""
from __future__ import annotations

import pytest
from django.contrib.auth.models import Group

from erp.identity.models import User
from erp.identity.roles import BRANCH_MANAGER
from erp.imports import masters
from erp.imports.models import ImportBatch, ImportRow
from erp.imports.validate import validate_batch
from erp.inventory.domain.models import Item, SupplierItemAlias
from erp.purchasing.domain.models import Supplier

pytestmark = pytest.mark.django_db


def _manager(username: str) -> User:
    bm, _ = Group.objects.get_or_create(name=BRANCH_MANAGER)
    u = User.objects.create_user(
        username=username, email=f"{username}@erp.local", password="pw12345!", is_superuser=True,
    )
    u.groups.add(bm)
    return u


def _invoice_batch(actor, item_value: str, supplier_code: str = "SUP-B") -> ImportBatch:
    """A one-line purchase-invoice batch whose item column is ``item_value`` under ``supplier_code``."""
    batch = ImportBatch.objects.create(entity="purchase_invoices")
    ImportRow.objects.create(
        batch=batch, row_number=1, status=ImportRow.Status.PENDING,
        normalized={
            "doc_number": "INV-1", "supplier_ref": supplier_code,
            "item_ref": item_value, "quantity": "10", "unit_price_minor": 200_00,
        },
    )
    return batch


def test_alias_resolves_supplier_code_to_canonical_item_no_duplicate():
    """Supplier B invoices item "7788"; an alias maps it to canonical RM-001. Ingestion links to
    RM-001 and creates NO new item — the duplicate the old name-only path would have proposed."""
    actor = _manager("m1")
    Supplier.objects.create(code="SUP-B", name="Supplier B")
    rm = Item.objects.create(sku="RM-001", name="Bearing 6205 ZZ", type="stock")
    SupplierItemAlias.objects.create(
        supplier_code="SUP-B", supplier_item_code="7788",
        supplier_item_name="رولمان بلي 6205", item=rm,
    )
    batch = _invoice_batch(actor, "7788")
    validate_batch(actor, batch)
    assert ImportRow.objects.get(batch=batch).status == ImportRow.Status.ERROR  # 7788 ≠ any SKU

    plan = masters.build_creation_plan(actor, batch)
    entry = next(e for e in plan["entries"] if e["entity"] == "items")
    assert entry["action"] == "link"
    assert entry["link_sku"] == "RM-001"
    assert entry["method"] == "alias_code"

    result = masters.execute_creation_plan(actor, batch, approved=plan["entries"])

    assert result["resolved"] == 1
    assert Item.objects.count() == 1  # NO duplicate item was created
    row = ImportRow.objects.get(batch=batch)
    assert row.status == ImportRow.Status.VALID
    assert not any(i["code"] == "missing_ref" for i in row.issues)


def test_creating_a_new_item_captures_the_supplier_alias():
    """An unmatched line under Supplier C is created as a new item, and the match is captured — so
    re-importing the same supplier line resolves by alias instead of duplicating."""
    actor = _manager("m2")
    Supplier.objects.create(code="SUP-C", name="Supplier C")
    batch = _invoice_batch(actor, "9999", supplier_code="SUP-C")
    validate_batch(actor, batch)

    plan = masters.build_creation_plan(actor, batch)
    entry = next(e for e in plan["entries"] if e["entity"] == "items")
    assert entry["action"] == "create"

    masters.execute_creation_plan(actor, batch, approved=plan["entries"])

    assert Item.objects.filter(sku="9999").exists()
    alias = SupplierItemAlias.objects.get(supplier_code="SUP-C", supplier_item_code="9999")
    assert alias.item.sku == "9999"
    assert alias.source == "imported"

    # The learning loop: a second invoice of the same line now resolves deterministically.
    batch2 = _invoice_batch(actor, "9999", supplier_code="SUP-C")
    validate_batch(actor, batch2)
    plan2 = masters.build_creation_plan(actor, batch2)
    # "9999" is now a real SKU, so it resolves at validate time — no item missing_ref remains.
    assert not any(e["entity"] == "items" for e in plan2["entries"])
    assert ImportRow.objects.get(batch=batch2).status == ImportRow.Status.VALID
