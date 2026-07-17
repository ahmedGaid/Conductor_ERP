"""Automatic master-data creation from missing_ref issues — plan session 08.

Same situation as ``test_validate.py``: no registered adapter has a "ref" field yet (document
adapters land in FILE_15/16), so the whole missing_ref -> creation-plan -> execute path is
exercised here against a throwaway ref-bearing test adapter, extended with a SECOND ref field
(``part`` -> ``items``) so the dependency-order behaviour has something real to sort against
``customers`` (items IS listed in ``masters._DEPENDENCY_ORDER``, customers is not).

Also: every registered adapter's ``write`` gates on the SAME role (``BRANCH_MANAGER`` — there is
no per-entity permission split in this codebase today), so "actor allowed to import X but not Y"
is exercised as "actor holds the role" vs "actor doesn't", not as two different entities blocked
differently.
"""
from __future__ import annotations

import pytest
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile

from erp.assistant.models import Attachment
from erp.identity.models import User
from erp.identity.roles import BRANCH_MANAGER
from erp.imports import masters, registry
from erp.imports.analyze import analyze
from erp.imports.models import ImportBatch, ImportRow
from erp.imports.registry import FieldSpec, Issue
from erp.imports.validate import validate_batch
from erp.inventory.domain.models import Item
from erp.sales import contracts as sales_contracts
from erp.sales.domain.models import Customer

pytestmark = pytest.mark.django_db


# --- helpers (duplicated from test_validate.py — no conftest.py in this package) ---------------
def _manager(username: str = "mgr") -> User:
    bm, _ = Group.objects.get_or_create(name=BRANCH_MANAGER)
    u = User.objects.create_user(username=username, email=f"{username}@erp.local", password="pw12345!")
    u.groups.add(bm)
    return u


def _plain_user(username: str = "viewer") -> User:
    return User.objects.create_user(username=username, email=f"{username}@erp.local", password="pw12345!")


def _csv(rows) -> bytes:
    text = "\n".join(",".join("" if c is None else str(c) for c in r) for r in rows)
    return text.encode("utf-8")


def _attachment(user, rows) -> Attachment:
    raw = _csv(rows)
    upload = SimpleUploadedFile("data.csv", raw, content_type="text/csv")
    return Attachment.objects.create(
        user=user, file=upload, name="data.csv", content_type="text/csv", size=len(raw),
    )


def _batch(entity: str, mapping: dict, attachment: Attachment) -> ImportBatch:
    return ImportBatch.objects.create(entity=entity, source_file=attachment, mapping=mapping)


class _WidgetAdapter:
    """Throwaway adapter with two "ref" fields, resolving against the REAL Customer/Item models —
    same pattern as test_validate.py's widget adapter, extended with a second ref for the
    dependency-order test."""

    entity = "widgets"
    label_key = "imports.entity.widgets"
    fields = [
        FieldSpec(name="code", required=True, kind="text"),
        FieldSpec(name="owner", kind="ref", ref="customers"),
        FieldSpec(name="part", kind="ref", ref="items"),
    ]
    natural_key = ["code"]
    group_by = None

    def lookup(self, actor, field, value):
        if field == "owner":
            return Customer.objects.filter(name=value).first()
        if field == "part":
            return Item.objects.filter(sku=value).first()
        return None

    def validate(self, actor, row: dict) -> list[Issue]:
        return []

    def write(self, actor, row: dict):
        return object()

    def exists(self, actor, row: dict):
        return None

    def existing_labels(self, actor):
        return []


@pytest.fixture()
def widget_adapter():
    adapter = _WidgetAdapter()
    registry.register(adapter)
    try:
        yield adapter
    finally:
        registry.REGISTER.pop("widgets", None)


def _analyzed_batch(actor, rows, mapping=None) -> ImportBatch:
    mapping = mapping or {"code": "Code", "owner": "Owner"}
    attachment = _attachment(actor, rows)
    batch = _batch("widgets", mapping, attachment)
    analyze(actor, batch)
    validate_batch(actor, batch)
    return batch


# --- build_creation_plan -------------------------------------------------------------------------
def test_plan_dedupes_the_same_missing_value_across_many_rows(widget_adapter):
    actor = _manager("m1")
    rows = [["Code", "Owner"]] + [[f"W{i}", "Wonka"] for i in range(40)]
    batch = _analyzed_batch(actor, rows)

    plan = masters.build_creation_plan(actor, batch)

    entries = [e for e in plan["entries"] if e["entity"] == "customers"]
    assert len(entries) == 1
    assert entries[0]["value"] == "Wonka"
    assert entries[0]["action"] == "create"
    assert entries[0]["proposed"] == {"name": "Wonka"}
    assert entries[0]["editable"] is True
    assert batch.stats["creation_plan"] == plan["entries"]


def test_plan_proposes_link_when_a_fuzzy_match_already_exists(widget_adapter):
    actor = _manager("m2")
    sales_contracts.create_customer(name="Ahmed Trading Co", code="", credit_limit_minor=0, actor=actor)
    batch = _analyzed_batch(actor, [["Code", "Owner"], ["W1", "Ahmed Trading"]])

    plan = masters.build_creation_plan(actor, batch)

    assert len(plan["entries"]) == 1
    entry = plan["entries"][0]
    assert entry["action"] == "link"
    assert entry["link_pk"] == str(Customer.objects.get(name="Ahmed Trading Co").pk)


def test_plan_orders_entries_by_dependency(widget_adapter):
    actor = _manager("m3")
    batch = _analyzed_batch(
        actor,
        [["Code", "Owner", "Part"], ["W1", "NewCo", "SKU-1"]],
        mapping={"code": "Code", "owner": "Owner", "part": "Part"},
    )

    plan = masters.build_creation_plan(actor, batch)

    order = [e["entity"] for e in plan["entries"]]
    # "items" is in masters._DEPENDENCY_ORDER, "customers" is not -> items sorts first.
    assert order == ["items", "customers"]


def test_plan_marks_an_entity_with_no_import_adapter_as_blocked_unsupported(widget_adapter):
    actor = _manager("m4")
    batch = _analyzed_batch(actor, [["Code", "Owner"], ["W1", "Wonka"]])
    # Poke an unsupported entity in directly — no ref field in this schema points at "warehouses"
    # today (FILE_05 blocker), but validate.py's contract (Issue.meta = {entity, value}) is generic.
    row = ImportRow.objects.get(batch=batch, row_number=1)
    row.issues = [*row.issues, {
        "field": "wh", "code": "missing_ref", "meta": {"entity": "warehouses", "value": "Cairo"},
    }]
    row.status = ImportRow.Status.ERROR
    row.save(update_fields=["issues", "status"])

    plan = masters.build_creation_plan(actor, batch)

    blocked = next(e for e in plan["entries"] if e["entity"] == "warehouses")
    assert blocked["action"] == "blocked_unsupported"
    assert blocked["editable"] is False


# --- execute_creation_plan -----------------------------------------------------------------------
def test_execute_creates_approved_entries_and_revalidates_rows_to_valid(widget_adapter):
    actor = _manager("m5")
    batch = _analyzed_batch(actor, [["Code", "Owner"], ["W1", "Wonka"]])
    plan = masters.build_creation_plan(actor, batch)
    row = ImportRow.objects.get(batch=batch, row_number=1)
    assert row.status == ImportRow.Status.ERROR

    result = masters.execute_creation_plan(actor, batch, approved=plan["entries"])

    assert result["resolved"] == 1
    assert Customer.objects.filter(name="Wonka").exists()
    row.refresh_from_db()
    assert row.status == ImportRow.Status.VALID
    assert not any(i["code"] == "missing_ref" for i in row.issues)
    entry = batch.stats["creation_plan"][0]
    assert entry["outcome"] == "created"
    assert batch.stats["created_masters"][0]["value"] == "Wonka"


def test_execute_skips_permission_blocked_entity_and_leaves_the_row_a_missing_ref(widget_adapter):
    actor = _plain_user("v1")
    batch = _analyzed_batch(actor, [["Code", "Owner"], ["W1", "Wonka"]])
    plan = masters.build_creation_plan(actor, batch)

    result = masters.execute_creation_plan(actor, batch, approved=plan["entries"])

    assert result["resolved"] == 0
    assert not Customer.objects.filter(name="Wonka").exists()
    row = ImportRow.objects.get(batch=batch, row_number=1)
    assert row.status == ImportRow.Status.ERROR
    assert any(i["code"] == "missing_ref" for i in row.issues)
    entry = batch.stats["creation_plan"][0]
    assert entry["action"] == "blocked_permission"
    assert entry["editable"] is False


def test_execute_ignores_entries_not_in_the_approved_list(widget_adapter):
    actor = _manager("m6")
    batch = _analyzed_batch(actor, [["Code", "Owner"], ["W1", "Wonka"]])
    masters.build_creation_plan(actor, batch)

    result = masters.execute_creation_plan(actor, batch, approved=[])

    assert result["resolved"] == 0
    assert not Customer.objects.filter(name="Wonka").exists()
