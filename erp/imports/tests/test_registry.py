"""Registry contract + model wiring: register/get roundtrip, duplicate guard, FieldSpec defaults."""
from __future__ import annotations

import pytest

from erp.imports import registry
from erp.imports.models import ImportBatch, ImportProfile, ImportRow
from erp.imports.registry import FieldSpec, ImportAdapter, Issue


class _ExampleAdapter:
    """Throwaway adapter used only in tests (real ones live in erp/imports/adapters/)."""

    entity = "widgets"
    label_key = "imports.entity.widgets"
    fields = [
        FieldSpec(name="code", required=True, synonyms_ar=["كود"]),
        FieldSpec(name="price", kind="money"),
        FieldSpec(name="owner", kind="ref", ref="customers"),
    ]
    natural_key = ["code"]
    group_by = None

    def lookup(self, actor, field, value):
        return None

    def validate(self, actor, row):
        return []

    def write(self, actor, row):
        return object()

    def exists(self, actor, row):
        return None

    def existing_labels(self, actor):
        return []


@pytest.fixture(autouse=True)
def _clean_registry():
    """Each test gets a pristine registry; restore whatever was there after."""
    saved = dict(registry.REGISTER)
    registry.REGISTER.clear()
    try:
        yield
    finally:
        registry.REGISTER.clear()
        registry.REGISTER.update(saved)


def test_register_get_roundtrip():
    adapter = _ExampleAdapter()
    registry.register(adapter)
    assert registry.get("widgets") is adapter
    assert registry.entities() == ["widgets"]


def test_example_adapter_satisfies_protocol():
    # runtime_checkable Protocol: the example must structurally match ImportAdapter.
    assert isinstance(_ExampleAdapter(), ImportAdapter)


def test_duplicate_registration_raises():
    registry.register(_ExampleAdapter())
    with pytest.raises(ValueError, match="already registered"):
        registry.register(_ExampleAdapter())


def test_get_unknown_entity_raises_with_message():
    with pytest.raises(KeyError, match="no import adapter for entity 'nope'"):
        registry.get("nope")


def test_fieldspec_defaults():
    fs = FieldSpec(name="title")
    assert fs.required is False
    assert fs.kind == "text"
    assert fs.ref is None
    assert fs.synonyms_en == [] and fs.synonyms_ar == []
    assert fs.default is None


def test_fieldspec_rejects_unknown_kind():
    with pytest.raises(ValueError, match="unknown kind"):
        FieldSpec(name="x", kind="bogus")


def test_issue_as_dict():
    issue = Issue(field="code", code="required", message="imports.err.required")
    assert issue.as_dict() == {
        "field": "code",
        "code": "required",
        "message": "imports.err.required",
    }


pytestmark = pytest.mark.django_db


def test_models_persist_and_relate():
    profile = ImportProfile.objects.create(
        name="Old system customers", entity="customers", mapping={"الاسم": "name"},
    )
    batch = ImportBatch.objects.create(entity="customers", profile=profile)
    assert batch.status == ImportBatch.Status.ANALYZING
    assert batch.strategy == ImportBatch.Strategy.CREATE_ONLY

    row = ImportRow.objects.create(batch=batch, row_number=1, raw={"الاسم": "أحمد"})
    assert row.status == ImportRow.Status.PENDING
    assert batch.rows.count() == 1


def test_row_number_unique_per_batch():
    from django.db import IntegrityError

    batch = ImportBatch.objects.create(entity="customers")
    ImportRow.objects.create(batch=batch, row_number=1)
    with pytest.raises(IntegrityError):
        ImportRow.objects.create(batch=batch, row_number=1)
