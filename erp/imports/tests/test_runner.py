"""Background runner: claim, run with progress/pause/cancel, crash recovery — smart-import
FILE_10 (DECISIONS: DB-backed job queue + management command, not Celery).

Real concurrent claimers (two OS processes racing ``select_for_update(skip_locked=True)``) aren't
practical to exercise in a single-threaded test; ``test_claim_next_does_not_reclaim_an_already_
running_batch`` instead asserts the observable contract two sequential claimers must respect:
once claimed, a batch is no longer ``ready`` and a second claim never returns it.
"""
from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth.models import Group
from django.utils import timezone

from erp.identity.models import User
from erp.identity.roles import BRANCH_MANAGER
from erp.imports import engine, registry, runner
from erp.imports.models import ImportBatch, ImportRow
from erp.imports.registry import FieldSpec, Issue

pytestmark = pytest.mark.django_db


def _manager(username: str) -> User:
    bm, _ = Group.objects.get_or_create(name=BRANCH_MANAGER)
    u = User.objects.create_user(username=username, email=f"{username}@erp.local", password="pw12345!")
    u.groups.add(bm)
    return u


class _SprocketAdapter:
    """Minimal in-memory fake — the runner only needs a working create path; strategy dispatch
    itself is FILE_09's concern, already covered in test_engine.py."""

    entity = "sprockets"
    label_key = "imports.entity.sprockets"
    fields = [
        FieldSpec(name="code", required=True, kind="text"),
        FieldSpec(name="name", required=True, kind="text"),
    ]
    natural_key = ["code"]
    group_by = None

    def __init__(self):
        self.store: dict[str, dict] = {}

    def lookup(self, actor, field, value):
        return None

    def validate(self, actor, row: dict) -> list[Issue]:
        return []

    def write(self, actor, row: dict):
        self.store[row["code"]] = row
        return row

    def exists(self, actor, row: dict):
        return self.store.get((row.get("code") or "").strip())

    def existing_labels(self, actor):
        return []


@pytest.fixture()
def sprocket_adapter():
    adapter = _SprocketAdapter()
    registry.register(adapter)
    try:
        yield adapter
    finally:
        registry.REGISTER.pop("sprockets", None)


def _make_ready_batch(actor, row_count: int, **extra) -> ImportBatch:
    batch = ImportBatch.objects.create(
        entity="sprockets", strategy=ImportBatch.Strategy.CREATE_ONLY,
        status=ImportBatch.Status.READY, created_by=actor, row_count=row_count, **extra,
    )
    for n in range(1, row_count + 1):
        ImportRow.objects.create(
            batch=batch, row_number=n, normalized={"code": f"S{n}", "name": f"Item{n}"},
            status=ImportRow.Status.VALID,
        )
    return batch


# --- claim -----------------------------------------------------------------------------------
def test_claim_next_does_not_reclaim_an_already_running_batch(sprocket_adapter):
    actor = _manager("cl1")
    _make_ready_batch(actor, 1)

    first = runner.claim_next()
    second = runner.claim_next()

    assert first is not None
    assert second is None


def test_claim_next_returns_none_with_no_ready_or_stale_batch(sprocket_adapter):
    assert runner.claim_next() is None


def test_claim_next_never_claims_a_validated_but_unconfirmed_batch(sprocket_adapter):
    """FILE_17 acceptance finding: `validate_batch` used to set the batch straight to `ready` —
    the same status `claim_next` claims on sight — so a batch could be auto-executed by the
    background runner within one poll interval of the mapping step finishing, before a human ever
    saw the review screen or clicked Create. `previewing` (this test's setup) is the real
    post-validation, pre-confirm state; only an explicit `/execute` call may reach `ready`."""
    actor = _manager("cl5")
    batch = ImportBatch.objects.create(
        entity="sprockets", strategy=ImportBatch.Strategy.CREATE_ONLY,
        status=ImportBatch.Status.PREVIEWING, created_by=actor, row_count=1,
    )
    ImportRow.objects.create(
        batch=batch, row_number=1, normalized={"code": "S1", "name": "One"}, status=ImportRow.Status.VALID,
    )

    assert runner.claim_next() is None
    batch.refresh_from_db()
    assert batch.status == ImportBatch.Status.PREVIEWING  # untouched — no execution, no heartbeat


def test_claim_next_recovers_a_stale_running_batch(sprocket_adapter):
    actor = _manager("cl2")
    stale = (timezone.now() - timedelta(minutes=10)).isoformat()
    batch = ImportBatch.objects.create(
        entity="sprockets", status=ImportBatch.Status.RUNNING, created_by=actor,
        row_count=1, stats={"heartbeat": stale},
    )
    ImportRow.objects.create(
        batch=batch, row_number=1, normalized={"code": "S1", "name": "One"}, status=ImportRow.Status.VALID,
    )

    claimed = runner.claim_next()

    assert claimed is not None
    assert claimed.pk == batch.pk
    assert claimed.status == ImportBatch.Status.RUNNING
    assert claimed.stats["heartbeat"] != stale  # heartbeat refreshed


def test_claim_next_ignores_a_running_batch_with_a_fresh_heartbeat(sprocket_adapter):
    actor = _manager("cl3")
    ImportBatch.objects.create(
        entity="sprockets", status=ImportBatch.Status.RUNNING, created_by=actor,
        stats={"heartbeat": timezone.now().isoformat()},
    )

    assert runner.claim_next() is None


def test_claim_next_prefers_ready_over_stale_running(sprocket_adapter):
    actor = _manager("cl4")
    stale = (timezone.now() - timedelta(minutes=10)).isoformat()
    ImportBatch.objects.create(
        entity="sprockets", status=ImportBatch.Status.RUNNING, created_by=actor,
        stats={"heartbeat": stale},
    )
    ready = _make_ready_batch(actor, 1)

    claimed = runner.claim_next()

    assert claimed.pk == ready.pk


# --- run: progress, pause, cancel -------------------------------------------------------------
def test_pause_between_chunks_leaves_durable_progress_and_resume_completes(sprocket_adapter, monkeypatch):
    monkeypatch.setattr(engine, "CHUNK", 2)
    actor = _manager("p1")
    batch = _make_ready_batch(actor, 6)
    claimed = runner.claim_next()
    runner.request_pause(actor, claimed)

    report = runner.run(actor, claimed)

    claimed.refresh_from_db()
    assert claimed.status == ImportBatch.Status.PAUSED
    assert report["created"] == 2  # first chunk (rows 1-2) ran before the pause flag was honoured
    assert claimed.stats["rows_done"] == 2
    assert claimed.stats["control"] == {"pause": True}
    pending = sorted(claimed.rows.filter(status=ImportRow.Status.VALID).values_list("row_number", flat=True))
    assert pending == [3, 4, 5, 6]

    runner.request_resume(actor, claimed)
    claimed.refresh_from_db()
    assert claimed.status == ImportBatch.Status.READY

    reclaimed = runner.claim_next()
    assert reclaimed.pk == batch.pk
    report2 = runner.run(actor, reclaimed)

    reclaimed.refresh_from_db()
    assert reclaimed.status == ImportBatch.Status.DONE
    assert report2["created"] == 6  # whole-batch total; no row imported twice
    assert len(sprocket_adapter.store) == 6


def test_cancel_skips_the_remainder(sprocket_adapter, monkeypatch):
    monkeypatch.setattr(engine, "CHUNK", 2)
    actor = _manager("c1")
    _make_ready_batch(actor, 6)
    claimed = runner.claim_next()
    runner.request_cancel(actor, claimed)

    report = runner.run(actor, claimed)

    claimed.refresh_from_db()
    assert claimed.status == ImportBatch.Status.DONE
    assert report["created"] == 2
    assert report["skipped"] == 4
    assert not claimed.rows.filter(status=ImportRow.Status.VALID).exists()
    assert len(sprocket_adapter.store) == 2


def test_run_with_no_control_flags_completes_the_whole_batch(sprocket_adapter, monkeypatch):
    monkeypatch.setattr(engine, "CHUNK", 2)
    actor = _manager("r1")
    _make_ready_batch(actor, 5)
    claimed = runner.claim_next()

    report = runner.run(actor, claimed)

    claimed.refresh_from_db()
    assert claimed.status == ImportBatch.Status.DONE
    assert report["created"] == 5
    assert claimed.stats["rows_done"] == 5
    assert claimed.stats["eta_seconds"] == 0


# --- control permission gate -------------------------------------------------------------------
def test_request_pause_requires_branch_manager(sprocket_adapter):
    actor = _manager("perm1")
    batch = _make_ready_batch(actor, 1)
    clerk = User.objects.create_user(username="clerk_run", email="clerk_run@erp.local", password="pw12345!")

    with pytest.raises(PermissionError):
        runner.request_pause(clerk, batch)


# --- inline threshold -------------------------------------------------------------------------
def test_should_run_inline_below_the_sync_limit():
    batch = ImportBatch(row_count=10)
    assert runner.should_run_inline(batch) is True


def test_should_run_inline_false_at_or_above_the_sync_limit():
    batch = ImportBatch(row_count=runner.IMPORTS_SYNC_LIMIT)
    assert runner.should_run_inline(batch) is False


# --- daemon resilience (management command) -----------------------------------------------------
def test_run_imports_command_marks_an_unready_batch_failed_instead_of_crashing(sprocket_adapter):
    """FILE_17 acceptance regression: a batch left `ready` despite failing the readiness gate
    (the execute-view bug fixed alongside this test) used to crash the whole `run_imports` daemon
    with an uncaught ReadinessError — every OTHER queued import silently blocked behind it,
    forever, since claim_next only claims by status. The command must isolate the failure to the
    one bad batch and keep serving the rest."""
    from django.core.management import call_command

    actor = _manager("crash1")
    batch = ImportBatch.objects.create(
        entity="sprockets", strategy=ImportBatch.Strategy.CREATE_ONLY,
        status=ImportBatch.Status.READY, created_by=actor, row_count=1,
    )
    # An ERROR row with no continue_after_errors flag fails `_readiness_reasons` — exactly the
    # state a batch must never reach, but the daemon has to survive it if it does.
    ImportRow.objects.create(
        batch=batch, row_number=1, normalized={"code": "S1"}, status=ImportRow.Status.ERROR,
    )

    call_command("run_imports", "--once")  # must not raise

    batch.refresh_from_db()
    assert batch.status == ImportBatch.Status.FAILED
    assert "unresolved_errors" in batch.stats["runner_error"]
