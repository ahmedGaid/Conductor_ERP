"""Analyze (existing-data diff) + validate (row gate) — plan session 06.

None of the four registered master adapters (customers/suppliers/items/contacts) have a "ref"
field yet (FILE_05 note), so the ref/missing-ref paths are exercised here against a throwaway test
adapter — same pattern as ``test_registry.py``'s ``_ExampleAdapter``. This also proves the "no ref
adapter yet" case degrades to empty stats rather than crashing.
"""
from __future__ import annotations

import pytest
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.utils import CaptureQueriesContext
from django.db import connection

from erp.assistant.models import Attachment
from erp.identity.models import User
from erp.identity.roles import BRANCH_MANAGER
from erp.imports import registry
from erp.imports.analyze import analyze
from erp.imports.models import ImportBatch, ImportRow
from erp.imports.registry import FieldSpec, Issue
from erp.imports.validate import revalidate_rows, validate_batch, validate_row
from erp.sales import contracts as sales_contracts
from erp.sales.domain.models import Customer

pytestmark = pytest.mark.django_db


# --- helpers -----------------------------------------------------------------------------------
def _manager(username: str = "mgr") -> User:
    bm, _ = Group.objects.get_or_create(name=BRANCH_MANAGER)
    u = User.objects.create_user(username=username, email=f"{username}@erp.local", password="pw12345!")
    u.groups.add(bm)
    return u


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
    """Throwaway adapter with one "ref" field — resolves against the REAL ``Customer`` model so the
    batched-lookup test can assert on real query counts, exactly like a production adapter would."""

    entity = "widgets"
    label_key = "imports.entity.widgets"
    fields = [
        FieldSpec(name="code", required=True, kind="text"),
        FieldSpec(name="owner", kind="ref", ref="customers"),
    ]
    natural_key = ["code"]
    group_by = None

    def __init__(self):
        self.known_codes: set[str] = set()

    def lookup(self, actor, field, value):
        if field != "owner":
            return None
        return Customer.objects.filter(name=value).first()

    def validate(self, actor, row: dict) -> list[Issue]:
        return []

    def write(self, actor, row: dict):
        return object()

    def exists(self, actor, row: dict):
        return object() if row.get("code") in self.known_codes else None


@pytest.fixture()
def widget_adapter():
    adapter = _WidgetAdapter()
    registry.register(adapter)
    try:
        yield adapter
    finally:
        registry.REGISTER.pop("widgets", None)


# --- analyze: rows + normalize issues -----------------------------------------------------------
def test_analyze_writes_one_row_per_source_row(widget_adapter):
    actor = _manager("a1")
    attachment = _attachment(actor, [
        ["Code", "Owner"],
        ["W1", "Acme"],
        ["W2", "Wonka"],
    ])
    batch = _batch("widgets", {"code": "Code", "owner": "Owner"}, attachment)

    stats = analyze(actor, batch)

    assert stats["rows"] == 2
    assert ImportRow.objects.filter(batch=batch).count() == 2
    batch.refresh_from_db()
    assert batch.status == ImportBatch.Status.PREVIEWING
    assert batch.stats == stats


def test_analyze_flags_required_missing():
    actor = _manager("a2")
    attachment = _attachment(actor, [["Code", "Name"], ["W1", ""]])  # name required, blank here
    batch = _batch("customers", {"name": "Name", "code": "Code"}, attachment)

    stats = analyze(actor, batch)

    row = ImportRow.objects.get(batch=batch, row_number=1)
    assert any(i["code"] == "required_missing" and i["field"] == "name" for i in row.issues)
    assert stats["issues_by_code"] == {"required_missing": 1}


def test_analyze_new_refs_and_existing_split(widget_adapter):
    actor = _manager("a3")
    sales_contracts.create_customer(name="Acme", code="", credit_limit_minor=0, actor=actor)
    attachment = _attachment(actor, [
        ["Code", "Owner"],
        ["W1", "Acme"],
        ["W2", "Wonka"],
        ["W3", "Wonka"],
    ])
    batch = _batch("widgets", {"code": "Code", "owner": "Owner"}, attachment)

    stats = analyze(actor, batch)

    assert stats["existing"] == {"customers": 1}  # Acme resolves — one DISTINCT value
    assert stats["new_refs"] == {"customers": ["Wonka"]}  # Wonka doesn't — deduped, not per-row


def test_analyze_degrades_gracefully_with_no_ref_fields():
    """customers/suppliers/items/contacts have zero ref fields — must not crash, just come back empty."""
    actor = _manager("a4")
    attachment = _attachment(actor, [["Name"], ["Acme"]])
    batch = _batch("customers", {"name": "Name"}, attachment)

    stats = analyze(actor, batch)

    assert stats["existing"] == {}
    assert stats["new_refs"] == {}


def test_analyze_flags_duplicate_in_file_only_on_repeat(widget_adapter):
    actor = _manager("a5")
    attachment = _attachment(actor, [
        ["Code", "Owner"],
        ["W1", "Acme"],
        ["W2", "Acme"],
        ["W1", "Acme"],  # repeat of row 1's natural key
    ])
    batch = _batch("widgets", {"code": "Code", "owner": "Owner"}, attachment)

    stats = analyze(actor, batch)

    rows = {r.row_number: r for r in ImportRow.objects.filter(batch=batch)}
    assert stats["duplicates_in_file"] == 1
    assert rows[1].issues == []  # first occurrence: clean
    assert any(i["code"] == "duplicate_in_file" for i in rows[3].issues)  # repeat: flagged


def test_batched_ref_lookup_query_count_independent_of_row_count(widget_adapter):
    """distinct owners = 2 (Acme, Wonka) across many rows → lookup queries stay O(2), not O(rows)."""
    actor = _manager("a6")
    sales_contracts.create_customer(name="Acme", code="", credit_limit_minor=0, actor=actor)
    rows = [["Code", "Owner"]] + [[f"W{i}", "Acme" if i % 2 else "Wonka"] for i in range(200)]
    attachment = _attachment(actor, rows)
    batch = _batch("widgets", {"code": "Code", "owner": "Owner"}, attachment)

    with CaptureQueriesContext(connection) as ctx:
        stats = analyze(actor, batch)

    assert stats["rows"] == 200
    # 2 distinct-value lookups + a small constant number of bulk_create/save queries — nowhere near 200.
    assert len(ctx.captured_queries) < 15


# --- validate_row / validate_batch ---------------------------------------------------------------
def test_validate_row_flags_missing_ref_with_entity_and_value(widget_adapter):
    actor = _manager("v1")
    attachment = _attachment(actor, [["Code", "Owner"], ["W1", "Wonka"]])
    batch = _batch("widgets", {"code": "Code", "owner": "Owner"}, attachment)
    analyze(actor, batch)
    row = ImportRow.objects.get(batch=batch, row_number=1)

    issues = validate_row(actor, widget_adapter, row, ref_cache={("owner", "Wonka"): None})

    missing = [i for i in issues if i.code == "missing_ref"]
    assert len(missing) == 1
    assert missing[0].meta == {"entity": "customers", "value": "Wonka"}


def test_validate_row_no_issue_when_ref_resolves(widget_adapter):
    actor = _manager("v2")
    customer = sales_contracts.create_customer(name="Acme", code="", credit_limit_minor=0, actor=actor)
    attachment = _attachment(actor, [["Code", "Owner"], ["W1", "Acme"]])
    batch = _batch("widgets", {"code": "Code", "owner": "Owner"}, attachment)
    analyze(actor, batch)
    row = ImportRow.objects.get(batch=batch, row_number=1)

    issues = validate_row(actor, widget_adapter, row, ref_cache={("owner", "Acme"): customer})

    assert not any(i.code == "missing_ref" for i in issues)


def test_validate_batch_first_in_file_duplicate_stays_valid_second_is_flagged(widget_adapter):
    actor = _manager("v3")
    sales_contracts.create_customer(name="Acme", code="", credit_limit_minor=0, actor=actor)
    attachment = _attachment(actor, [
        ["Code", "Owner"], ["W1", "Acme"], ["W1", "Acme"],
    ])
    batch = _batch("widgets", {"code": "Code", "owner": "Owner"}, attachment)
    analyze(actor, batch)

    validate_batch(actor, batch)

    rows = {r.row_number: r for r in ImportRow.objects.filter(batch=batch)}
    assert rows[1].status == ImportRow.Status.VALID
    assert rows[2].status == ImportRow.Status.DUPLICATE


def test_validate_batch_sets_duplicate_status_on_natural_key_db_match(widget_adapter):
    actor = _manager("v4")
    sales_contracts.create_customer(name="Acme", code="", credit_limit_minor=0, actor=actor)
    widget_adapter.known_codes.add("W1")
    attachment = _attachment(actor, [["Code", "Owner"], ["W1", "Acme"]])
    batch = _batch("widgets", {"code": "Code", "owner": "Owner"}, attachment)
    analyze(actor, batch)

    validate_batch(actor, batch)

    row = ImportRow.objects.get(batch=batch, row_number=1)
    assert row.status == ImportRow.Status.DUPLICATE


def test_validate_batch_marks_error_when_required_missing():
    actor = _manager("v5")
    attachment = _attachment(actor, [["Name", "Code"], ["", "W9"]])
    batch = _batch("customers", {"name": "Name", "code": "Code"}, attachment)
    analyze(actor, batch)

    counts = validate_batch(actor, batch)

    assert counts["error"] == 1
    row = ImportRow.objects.get(batch=batch, row_number=1)
    assert row.status == ImportRow.Status.ERROR
    assert any(i["code"] == "required_missing" for i in row.issues)


# --- revalidate_rows: the inline-edit fast path ---------------------------------------------------
def test_revalidate_rows_flips_error_to_valid_after_edit(widget_adapter):
    actor = _manager("r1")
    sales_contracts.create_customer(name="Acme", code="", credit_limit_minor=0, actor=actor)
    attachment = _attachment(actor, [
        ["Code", "Owner"], ["W1", "Wonka"], ["W2", "Acme"],
    ])
    batch = _batch("widgets", {"code": "Code", "owner": "Owner"}, attachment)
    analyze(actor, batch)
    validate_batch(actor, batch)

    bad_row = ImportRow.objects.get(batch=batch, row_number=1)
    other_row = ImportRow.objects.get(batch=batch, row_number=2)
    assert bad_row.status == ImportRow.Status.ERROR
    bad_row.decision = {"edits": {"owner": "Acme"}}
    bad_row.save(update_fields=["decision"])

    counts = revalidate_rows(actor, batch, [bad_row.id])

    bad_row.refresh_from_db()
    other_row_after = ImportRow.objects.get(pk=other_row.pk)
    assert bad_row.status == ImportRow.Status.VALID
    assert bad_row.normalized["owner"] == "Acme"
    assert counts == {"valid": 1, "error": 0, "duplicate": 0}
    # untouched sibling row: same status it had after the batch validate, not re-evaluated here
    assert other_row_after.status == other_row.status
