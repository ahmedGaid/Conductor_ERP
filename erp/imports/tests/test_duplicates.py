"""Fuzzy duplicate detection — plan session 07."""
from __future__ import annotations

import time

import pytest
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile

from erp.assistant.models import Attachment
from erp.identity.models import User
from erp.identity.roles import BRANCH_MANAGER
from erp.imports.analyze import analyze
from erp.imports.duplicates import MAX_BUCKET_FOR_FUZZY, find_candidates, similarity
from erp.imports.models import ImportBatch, ImportRow
from erp.imports.registry import get as get_adapter
from erp.imports.validate import apply_decision, execute_status, validate_batch
from erp.sales import contracts as sales_contracts

pytestmark = pytest.mark.django_db


def _manager(username: str) -> User:
    bm, _ = Group.objects.get_or_create(name=BRANCH_MANAGER)
    u = User.objects.create_user(username=username, email=f"{username}@erp.local", password="pw12345!")
    u.groups.add(bm)
    return u


def _csv(rows) -> bytes:
    text = "\n".join(",".join("" if c is None else str(c) for c in r) for r in rows)
    return text.encode("utf-8")


def _batch(actor, entity: str, mapping: dict, rows) -> ImportBatch:
    raw = _csv(rows)
    upload = SimpleUploadedFile("data.csv", raw, content_type="text/csv")
    attachment = Attachment.objects.create(
        user=actor, file=upload, name="data.csv", content_type="text/csv", size=len(raw),
    )
    batch = ImportBatch.objects.create(entity=entity, source_file=attachment, mapping=mapping)
    analyze(actor, batch)
    validate_batch(actor, batch)
    return batch


# --- similarity ----------------------------------------------------------------------------------
@pytest.mark.parametrize("other", ["Ahmed Co", "Ahmed Company", "Ahmed Trading"])
def test_similarity_clusters_legal_suffix_variants(other):
    assert similarity("Ahmed", other) >= 85


@pytest.mark.parametrize("other", ["شركة احمد التجارية", "مؤسسة احمد", "احمد التجارية"])
def test_similarity_clusters_arabic_variants(other):
    assert similarity("احمد", other) >= 85


def test_similarity_distinct_names_stay_low():
    assert similarity("Ahmed", "Mohamed Trading") < 85


# --- find_candidates: against existing DB records -------------------------------------------------
def test_find_candidates_flags_probable_duplicate_against_existing_record():
    actor = _manager("fc1")
    sales_contracts.create_customer(name="Ahmed Trading", code="", credit_limit_minor=0, actor=actor)
    batch = _batch(actor, "customers", {"name": "Name"}, [["Name"], ["Ahmed"]])
    adapter = get_adapter("customers")

    find_candidates(actor, adapter, batch)

    row = ImportRow.objects.get(batch=batch, row_number=1)
    assert row.status == ImportRow.Status.DUPLICATE
    dup = next(i for i in row.issues if i["code"] == "probable_duplicate")
    assert dup["meta"]["candidates"][0]["label"] == "Ahmed Trading"
    assert dup["meta"]["candidates"][0]["score"] >= 85


def test_find_candidates_caps_at_three_candidates():
    actor = _manager("fc2")
    for label in ["Ahmed Co", "Ahmed Company", "Ahmed Trading", "Ahmed LLC"]:
        sales_contracts.create_customer(name=label, code="", credit_limit_minor=0, actor=actor)
    batch = _batch(actor, "customers", {"name": "Name"}, [["Name"], ["Ahmed"]])
    adapter = get_adapter("customers")

    find_candidates(actor, adapter, batch)

    row = ImportRow.objects.get(batch=batch, row_number=1)
    dup = next(i for i in row.issues if i["code"] == "probable_duplicate")
    assert len(dup["meta"]["candidates"]) == 3


def test_find_candidates_flags_in_batch_pair():
    actor = _manager("fc3")
    batch = _batch(actor, "customers", {"name": "Name"}, [
        ["Name"], ["Ahmed Trading"], ["Ahmed Co"],
    ])
    adapter = get_adapter("customers")

    find_candidates(actor, adapter, batch)

    rows = {r.row_number: r for r in ImportRow.objects.filter(batch=batch)}
    assert rows[1].status == ImportRow.Status.DUPLICATE
    assert rows[2].status == ImportRow.Status.DUPLICATE
    dup1 = next(i for i in rows[1].issues if i["code"] == "probable_duplicate")
    assert dup1["meta"]["candidates"][0]["row_number"] == 2


def test_find_candidates_leaves_distinct_names_valid():
    actor = _manager("fc4")
    sales_contracts.create_customer(name="Ahmed Trading", code="", credit_limit_minor=0, actor=actor)
    batch = _batch(actor, "customers", {"name": "Name"}, [["Name"], ["Mohamed Trading"]])
    adapter = get_adapter("customers")

    find_candidates(actor, adapter, batch)

    row = ImportRow.objects.get(batch=batch, row_number=1)
    assert row.status == ImportRow.Status.VALID


def test_find_candidates_scales_with_bucketing():
    """Distinct-first-token names across thousands of rows must not compare all-pairs."""
    actor = _manager("fc5")
    rows = [["Name"]] + [[f"Company{i} Trading"] for i in range(3000)]
    batch = _batch(actor, "customers", {"name": "Name"}, rows)
    adapter = get_adapter("customers")

    started = time.monotonic()
    find_candidates(actor, adapter, batch)
    elapsed = time.monotonic() - started

    assert elapsed < 5.0


def test_find_candidates_skips_oversized_bucket_instead_of_quadratic_blowup():
    """A templated file (or a common Arabic legal-name word like 'شركة') can put THOUSANDS of rows
    in the SAME first-token bucket — the exact case the bucketing guard was meant to price out.
    Without the size cap this is a real O(cluster^2) hang (FILE_17 acceptance finding: a 100k-row
    file where every row starts "Volume Test Customer" hung the mapping request indefinitely)."""
    actor = _manager("fc6")
    n = MAX_BUCKET_FOR_FUZZY * 10
    rows = [["Name"]] + [[f"Volume Test Customer {i:06d}"] for i in range(n)]
    batch = _batch(actor, "customers", {"name": "Name"}, rows)
    adapter = get_adapter("customers")

    started = time.monotonic()
    find_candidates(actor, adapter, batch)
    elapsed = time.monotonic() - started

    assert elapsed < 5.0
    assert not ImportRow.objects.filter(batch=batch, status=ImportRow.Status.DUPLICATE).exists()


# --- decisions: never auto-merge -------------------------------------------------------------------
def test_apply_decision_ignore_sets_skipped():
    actor = _manager("d1")
    existing = sales_contracts.create_customer(name="Ahmed Trading", code="", credit_limit_minor=0, actor=actor)
    batch = _batch(actor, "customers", {"name": "Name"}, [["Name"], ["Ahmed"]])
    adapter = get_adapter("customers")
    find_candidates(actor, adapter, batch)
    row = ImportRow.objects.get(batch=batch, row_number=1)

    updated = apply_decision(actor, batch, row.id, {"duplicate": "ignore"})

    assert updated.status == ImportRow.Status.SKIPPED
    assert existing is not None


def test_apply_decision_create_lands_valid():
    actor = _manager("d2")
    sales_contracts.create_customer(name="Ahmed Trading", code="", credit_limit_minor=0, actor=actor)
    batch = _batch(actor, "customers", {"name": "Name"}, [["Name"], ["Ahmed"]])
    adapter = get_adapter("customers")
    find_candidates(actor, adapter, batch)
    row = ImportRow.objects.get(batch=batch, row_number=1)

    updated = apply_decision(actor, batch, row.id, {"duplicate": "create"})

    assert updated.status == ImportRow.Status.VALID


def test_apply_decision_merge_keeps_duplicate_with_target():
    actor = _manager("d3")
    sales_contracts.create_customer(name="Ahmed Trading", code="", credit_limit_minor=0, actor=actor)
    batch = _batch(actor, "customers", {"name": "Name"}, [["Name"], ["Ahmed"]])
    adapter = get_adapter("customers")
    find_candidates(actor, adapter, batch)
    row = ImportRow.objects.get(batch=batch, row_number=1)
    target_pk = str(adapter.existing_labels(actor)[0][0])

    updated = apply_decision(actor, batch, row.id, {"duplicate": "merge", "target_pk": target_pk})

    assert updated.status == ImportRow.Status.DUPLICATE
    assert updated.decision["target_pk"] == target_pk


def test_apply_decision_merge_requires_target_pk():
    actor = _manager("d4")
    batch = _batch(actor, "customers", {"name": "Name"}, [["Name"], ["Ahmed"]])
    row = ImportRow.objects.get(batch=batch, row_number=1)

    with pytest.raises(ValueError, match="target_pk"):
        apply_decision(actor, batch, row.id, {"duplicate": "merge"})


def test_apply_decision_rejects_unknown_kind():
    actor = _manager("d5")
    batch = _batch(actor, "customers", {"name": "Name"}, [["Name"], ["Ahmed"]])
    row = ImportRow.objects.get(batch=batch, row_number=1)

    with pytest.raises(ValueError, match="unknown duplicate decision"):
        apply_decision(actor, batch, row.id, {"duplicate": "delete"})


# --- execute_status: the undecided default, no DB writes ----------------------------------------
def test_execute_status_undecided_duplicate_defaults_to_skipped():
    actor = _manager("e1")
    sales_contracts.create_customer(name="Ahmed Trading", code="", credit_limit_minor=0, actor=actor)
    batch = _batch(actor, "customers", {"name": "Name"}, [["Name"], ["Ahmed"]])
    adapter = get_adapter("customers")
    find_candidates(actor, adapter, batch)
    row = ImportRow.objects.get(batch=batch, row_number=1)

    assert execute_status(row) == ImportRow.Status.SKIPPED
    row.refresh_from_db()
    assert row.status == ImportRow.Status.DUPLICATE  # execute_status never mutates the row


def test_execute_status_non_duplicate_row_passes_through():
    actor = _manager("e2")
    batch = _batch(actor, "customers", {"name": "Name"}, [["Name"], ["Distinct Co"]])
    row = ImportRow.objects.get(batch=batch, row_number=1)

    assert execute_status(row) == row.status == ImportRow.Status.VALID
