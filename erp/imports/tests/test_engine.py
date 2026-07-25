"""Execution engine: strategies, chunked commits, resume, rollback, report — plan session 09.

No registered adapter supports update/delete yet (FILE_05/06 blocker — customers/items/suppliers/
contacts only expose a create path), so ``supports_update``/``update``/``delete`` are exercised
against a small in-memory fake adapter ("gizmos") — same throwaway-test-adapter pattern as
``test_validate.py``/``test_masters.py`` — plus one end-to-end pass against the real ``customers``
adapter to prove the report/rollback fallbacks (no ``.pk``, no delete path) behave correctly
against an actual module write-path.
"""
from __future__ import annotations

from dataclasses import dataclass

import pytest
from django.contrib.auth.models import Group

from erp.audit.models import AuditEntry
from erp.identity.models import User
from erp.identity.roles import BRANCH_MANAGER
from erp.imports import engine, registry
from erp.imports.models import ImportBatch, ImportRow
from erp.imports.registry import FieldSpec, Issue
from erp.sales.domain.models import Customer

pytestmark = pytest.mark.django_db


# --- helpers -------------------------------------------------------------------------------------
def _manager(username: str) -> User:
    bm, _ = Group.objects.get_or_create(name=BRANCH_MANAGER)
    u = User.objects.create_user(username=username, email=f"{username}@erp.local", password="pw12345!")
    u.groups.add(bm)
    return u


def _make_batch(entity: str = "gizmos", strategy=ImportBatch.Strategy.CREATE_ONLY, stats=None) -> ImportBatch:
    return ImportBatch.objects.create(entity=entity, strategy=strategy, stats=stats or {})


def _make_row(batch, row_number, normalized, *, status=ImportRow.Status.VALID, decision=None, issues=None) -> ImportRow:
    return ImportRow.objects.create(
        batch=batch, row_number=row_number, normalized=normalized, status=status,
        decision=decision or {}, issues=issues or [],
    )


@dataclass
class _Record:
    pk: str
    code: str
    name: str


class _GizmoAdapter:
    """In-memory fake with update+delete (neither exists on a real adapter yet). ``write`` raises
    for ``name == "BOOM"`` — the deterministic trigger the chunk-crash test needs."""

    entity = "gizmos"
    label_key = "imports.entity.gizmos"
    fields = [
        FieldSpec(name="code", required=True, kind="text"),
        FieldSpec(name="name", required=True, kind="text"),
    ]
    natural_key = ["code"]
    group_by = None
    supports_update = True

    def __init__(self):
        self.store: dict[str, _Record] = {}
        self._next_pk = 1

    def lookup(self, actor, field, value):
        return None

    def validate(self, actor, row: dict) -> list[Issue]:
        return []

    def write(self, actor, row: dict) -> _Record:
        if row.get("name") == "BOOM":
            raise RuntimeError("simulated write failure")
        pk = str(self._next_pk)
        self._next_pk += 1
        record = _Record(pk=pk, code=row["code"], name=row["name"])
        self.store[pk] = record
        return record

    def update(self, actor, row: dict, *, target_pk=None) -> _Record:
        pk = target_pk or next((p for p, r in self.store.items() if r.code == row.get("code")), None)
        if pk is None or pk not in self.store:
            raise ValueError("no matching gizmo to update")
        current = self.store[pk]
        record = _Record(pk=pk, code=row.get("code", current.code), name=row.get("name", current.name))
        self.store[pk] = record
        return record

    def delete(self, actor, pk) -> None:
        del self.store[str(pk)]

    def exists(self, actor, row: dict):
        code = (row.get("code") or "").strip()
        return next((r for r in self.store.values() if r.code == code), None)

    def existing_labels(self, actor):
        return [(r.pk, r.name) for r in self.store.values()]


@pytest.fixture()
def gizmo_adapter():
    adapter = _GizmoAdapter()
    registry.register(adapter)
    try:
        yield adapter
    finally:
        registry.REGISTER.pop("gizmos", None)


# --- readiness gate --------------------------------------------------------------------------
def test_readiness_blocks_undecided_duplicate_rows(gizmo_adapter):
    actor = _manager("rd1")
    batch = _make_batch()
    _make_row(batch, 1, {"code": "G1", "name": "One"}, status=ImportRow.Status.DUPLICATE)

    with pytest.raises(engine.ReadinessError) as exc:
        engine.execute_batch(actor, batch)
    assert exc.value.reasons[0] == {"code": "undecided_duplicates", "count": 1}


def test_readiness_blocks_unresolved_creation_plan_entries(gizmo_adapter):
    actor = _manager("rd2")
    plan = [{"entity": "customers", "value": "X", "action": "create", "editable": True}]
    batch = _make_batch(stats={"creation_plan": plan})
    _make_row(batch, 1, {"code": "G1", "name": "One"})

    with pytest.raises(engine.ReadinessError) as exc:
        engine.execute_batch(actor, batch)
    assert exc.value.reasons[0] == {"code": "pending_creation_plan", "count": 1}


def test_readiness_blocks_errors_unless_continue_after_errors_is_set(gizmo_adapter):
    actor = _manager("rd3")
    batch = _make_batch()
    _make_row(batch, 1, {"code": "G1", "name": "One"})
    _make_row(batch, 2, {"code": "G2", "name": ""}, status=ImportRow.Status.ERROR)

    with pytest.raises(engine.ReadinessError):
        engine.execute_batch(actor, batch)

    batch.stats = {"continue_after_errors": True}
    batch.save(update_fields=["stats"])
    report = engine.execute_batch(actor, batch)
    assert report["created"] == 1


def test_upsert_blocked_when_the_adapter_has_no_update_support():
    actor = _manager("rd4")
    batch = ImportBatch.objects.create(entity="customers", strategy=ImportBatch.Strategy.UPSERT)
    _make_row(batch, 1, {"name": "NoUpdateCo"})

    with pytest.raises(engine.ReadinessError) as exc:
        engine.execute_batch(actor, batch)
    assert exc.value.reasons[0] == {"code": "adapter_no_update_support", "entity": "customers"}


# --- strategy dispatch -----------------------------------------------------------------------
def test_create_only_creates_new_and_skips_existing(gizmo_adapter):
    actor = _manager("s1")
    gizmo_adapter.write(actor, {"code": "EXIST", "name": "Pre"})
    batch = _make_batch(strategy=ImportBatch.Strategy.CREATE_ONLY)
    _make_row(batch, 1, {"code": "NEW1", "name": "New"})
    _make_row(batch, 2, {"code": "EXIST", "name": "Ignored"})

    report = engine.execute_batch(actor, batch)

    assert report["created"] == 1
    assert report["skipped"] == 1
    assert len(gizmo_adapter.store) == 2
    assert gizmo_adapter.exists(actor, {"code": "EXIST"}).name == "Pre"


def test_update_only_updates_existing_and_skips_new(gizmo_adapter):
    actor = _manager("s2")
    gizmo_adapter.write(actor, {"code": "EXIST", "name": "Pre"})
    batch = _make_batch(strategy=ImportBatch.Strategy.UPDATE_ONLY)
    _make_row(batch, 1, {"code": "EXIST", "name": "Updated"})
    _make_row(batch, 2, {"code": "NEW1", "name": "New"})

    report = engine.execute_batch(actor, batch)

    assert report["updated"] == 1
    assert report["skipped"] == 1
    assert gizmo_adapter.exists(actor, {"code": "EXIST"}).name == "Updated"
    assert gizmo_adapter.exists(actor, {"code": "NEW1"}) is None


def test_upsert_creates_new_and_updates_existing(gizmo_adapter):
    actor = _manager("s3")
    gizmo_adapter.write(actor, {"code": "EXIST", "name": "Pre"})
    batch = _make_batch(strategy=ImportBatch.Strategy.UPSERT)
    _make_row(batch, 1, {"code": "EXIST", "name": "Updated"})
    _make_row(batch, 2, {"code": "NEW1", "name": "New"})

    report = engine.execute_batch(actor, batch)

    assert report["created"] == 1
    assert report["updated"] == 1
    assert report["skipped"] == 0


def test_skip_existing_creates_new_and_skips_existing(gizmo_adapter):
    actor = _manager("s4")
    gizmo_adapter.write(actor, {"code": "EXIST", "name": "Pre"})
    batch = _make_batch(strategy=ImportBatch.Strategy.SKIP_EXISTING)
    _make_row(batch, 1, {"code": "EXIST", "name": "Ignored"})
    _make_row(batch, 2, {"code": "NEW1", "name": "New"})

    report = engine.execute_batch(actor, batch)

    assert report["created"] == 1
    assert report["skipped"] == 1
    assert gizmo_adapter.exists(actor, {"code": "EXIST"}).name == "Pre"


def test_merge_decided_duplicate_updates_the_target_record(gizmo_adapter):
    actor = _manager("s5")
    existing = gizmo_adapter.write(actor, {"code": "EXIST", "name": "Pre"})
    batch = _make_batch(strategy=ImportBatch.Strategy.CREATE_ONLY)  # strategy is irrelevant to a merge row
    _make_row(
        batch, 1, {"code": "NEWCODE", "name": "Merged"},
        status=ImportRow.Status.DUPLICATE, decision={"duplicate": "merge", "target_pk": existing.pk},
    )

    report = engine.execute_batch(actor, batch)

    assert report["updated"] == 1
    assert gizmo_adapter.store[existing.pk].name == "Merged"


# --- chunking / resume -----------------------------------------------------------------------
def test_chunk_crash_rolls_back_only_that_chunk_and_resume_completes_without_double_import(
    gizmo_adapter, monkeypatch,
):
    monkeypatch.setattr(engine, "CHUNK", 3)
    actor = _manager("c1")
    batch = _make_batch(strategy=ImportBatch.Strategy.CREATE_ONLY)
    for n in range(1, 8):
        name = "BOOM" if n == 4 else f"Item{n}"
        _make_row(batch, n, {"code": f"G{n}", "name": name})

    report = engine.execute_batch(actor, batch)

    batch.refresh_from_db()
    assert batch.status == ImportBatch.Status.PAUSED
    assert report["created"] == 3  # chunk 1 (rows 1-3) durable; chunk 2 (rows 4-6) rolled back whole
    assert {r.code for r in gizmo_adapter.store.values()} == {"G1", "G2", "G3"}
    pending = sorted(batch.rows.filter(status=ImportRow.Status.VALID).values_list("row_number", flat=True))
    assert pending == [4, 5, 6, 7]  # chunk 3 (row 7) never attempted once chunk 2 failed

    bad_row = batch.rows.get(row_number=4)
    bad_row.normalized = {"code": "G4", "name": "Item4"}
    bad_row.save(update_fields=["normalized"])

    report2 = engine.resume_batch(actor, batch)

    batch.refresh_from_db()
    assert batch.status == ImportBatch.Status.DONE
    assert report2["created"] == 7  # whole-batch total, not just this call's chunk
    assert {r.code for r in gizmo_adapter.store.values()} == {f"G{n}" for n in range(1, 8)}
    assert len(gizmo_adapter.store) == 7  # no row imported twice
    assert not batch.rows.filter(status=ImportRow.Status.VALID).exists()


def test_execute_chunk_writes_one_audit_entry_per_chunk(gizmo_adapter):
    actor = _manager("c2")
    batch = _make_batch(strategy=ImportBatch.Strategy.CREATE_ONLY)
    _make_row(batch, 1, {"code": "G1", "name": "One"})

    engine.execute_batch(actor, batch)

    assert AuditEntry.objects.filter(module="imports", action="execute_chunk").count() == 1


# --- rollback ---------------------------------------------------------------------------------
def test_rollback_deletes_created_records_when_the_adapter_supports_delete(gizmo_adapter):
    actor = _manager("r1")
    batch = _make_batch(strategy=ImportBatch.Strategy.CREATE_ONLY)
    _make_row(batch, 1, {"code": "G1", "name": "One"})
    _make_row(batch, 2, {"code": "G2", "name": "Two"})
    engine.execute_batch(actor, batch)
    assert len(gizmo_adapter.store) == 2

    result = engine.rollback_batch(actor, batch)

    assert result == {"reverted": 2, "skipped": 0, "cannot": []}
    assert gizmo_adapter.store == {}
    batch.refresh_from_db()
    assert batch.status == ImportBatch.Status.ROLLED_BACK
    assert set(batch.rows.values_list("status", flat=True)) == {ImportRow.Status.REVERTED}


def test_rollback_marks_cannot_revert_when_the_adapter_has_no_delete_path():
    actor = _manager("r2")
    batch = ImportBatch.objects.create(entity="customers", strategy=ImportBatch.Strategy.CREATE_ONLY)
    _make_row(batch, 1, {"name": "Acme RB"})
    engine.execute_batch(actor, batch)
    assert Customer.objects.filter(name="Acme RB").exists()

    result = engine.rollback_batch(actor, batch)

    assert result["reverted"] == 0
    assert len(result["cannot"]) == 1
    assert "no delete path" in result["cannot"][0]["reason"]
    # Structured code + entity so the frontend can show a translated, blame-free message instead of
    # this raw string (which was leaking straight into the UI before FILE_17 acceptance caught it).
    assert result["cannot"][0]["code"] == "no_delete_path"
    assert result["cannot"][0]["entity"] == "customers"
    assert Customer.objects.filter(name="Acme RB").exists()  # nothing was actually touched


# --- report ------------------------------------------------------------------------------------
def test_report_counts_reconcile_with_row_statuses(gizmo_adapter):
    actor = _manager("rep1")
    gizmo_adapter.write(actor, {"code": "DUP", "name": "Existing"})
    batch = _make_batch(strategy=ImportBatch.Strategy.CREATE_ONLY)
    _make_row(batch, 1, {"code": "A", "name": "A"})
    _make_row(batch, 2, {"code": "DUP", "name": "Ignored"})
    _make_row(
        batch, 3, {}, status=ImportRow.Status.ERROR,
        issues=[{"field": "code", "code": "required_missing", "message": "x"}],
    )
    batch.error_count = 1
    batch.stats = {"continue_after_errors": True}
    batch.save(update_fields=["error_count", "stats"])

    report = engine.execute_batch(actor, batch)

    assert report["created"] == 1
    assert report["skipped"] == 1
    assert report["errors"] == 1
    assert report["error_rows"] == [{"row": 3, "issues": [{"field": "code", "code": "required_missing", "message": "x"}]}]
    assert report["created"] + report["skipped"] + report["errors"] == 3
    assert len(report["row_outcomes"]) == 3


# --- real adapter integration ------------------------------------------------------------------
def test_real_customers_adapter_end_to_end_create_only():
    actor = _manager("real1")
    batch = ImportBatch.objects.create(entity="customers", strategy=ImportBatch.Strategy.CREATE_ONLY)
    _make_row(batch, 1, {"name": "Real Co", "credit_limit_minor": 1000})

    report = engine.execute_batch(actor, batch)

    assert report["created"] == 1
    customer = Customer.objects.get(name="Real Co")
    assert customer.credit_limit_minor == 1000
    row = batch.rows.get(row_number=1)
    # CustomerAdapter.write returns a CustomerInfo dataclass (no .pk) -> falls back to the
    # adapter's natural-key field (CustomerAdapter.natural_key == ["name"]) on the record.
    assert row.result_ref == {"model": "erp.sales.contracts.CustomerInfo", "pk": customer.name, "action": "created"}
