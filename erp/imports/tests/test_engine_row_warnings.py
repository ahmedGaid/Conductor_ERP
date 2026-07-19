"""A row-level (ungrouped) adapter's ``write`` may return ``(record, warnings)`` exactly like a
grouped adapter's — the engine attaches the warnings to that row's issues without erroring it."""
from __future__ import annotations

import pytest
from django.contrib.auth.models import Group

from erp.identity.models import User
from erp.identity.roles import BRANCH_MANAGER
from erp.imports import engine, registry
from erp.imports.models import ImportBatch, ImportRow
from erp.imports.registry import FieldSpec, Issue

pytestmark = pytest.mark.django_db


class _Record:
    def __init__(self, pk):
        self.pk = pk


class _WarningEmittingAdapter:
    entity = "test_row_warnings"
    label_key = "imports.entity.testRowWarnings"
    fields = [FieldSpec(name="value", kind="text")]
    natural_key = []
    group_by = None

    def lookup(self, actor, field, value):
        return None

    def validate(self, actor, row):
        return []

    def write(self, actor, row):
        record = _Record(pk=row["value"])
        if row["value"] == "warn":
            return record, [Issue(field="value", code="test_warning", message="test.warning")]
        return record

    def exists(self, actor, row):
        return None

    def existing_labels(self, actor):
        return []


@pytest.fixture(autouse=True)
def _register():
    if "test_row_warnings" not in registry.REGISTER:
        registry.register(_WarningEmittingAdapter())
    yield


def _manager() -> User:
    bm, _ = Group.objects.get_or_create(name=BRANCH_MANAGER)
    u = User.objects.create_user(username="rw1", email="rw1@erp.local", password="pw12345!", is_superuser=True)
    u.groups.add(bm)
    return u


def test_row_level_write_may_return_warnings_without_erroring():
    actor = _manager()
    batch = ImportBatch.objects.create(entity="test_row_warnings")
    ImportRow.objects.create(batch=batch, row_number=1, normalized={"value": "warn"}, status=ImportRow.Status.VALID)
    ImportRow.objects.create(batch=batch, row_number=2, normalized={"value": "clean"}, status=ImportRow.Status.VALID)

    report = engine.execute_batch(actor, batch)

    assert report["imported"] == 2  # both rows still imported — a warning never blocks
    row1 = batch.rows.get(row_number=1)
    assert row1.status == ImportRow.Status.IMPORTED
    assert any(i["code"] == "test_warning" for i in row1.issues)
    row2 = batch.rows.get(row_number=2)
    assert row2.issues == []


def test_existing_row_level_adapters_unaffected_by_bare_record_return():
    """A guard: any adapter still returning a bare record (every one built before this session)
    behaves exactly as before — no warnings, no crash unpacking a non-tuple."""
    _manager()
    ImportBatch.objects.create(entity="customers")
    assert "customers" in registry.entities()
