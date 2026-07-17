"""Background runner for import batches — DECISIONS-gated (smart-import FILE_10): a DB-backed job
queue + management command (Option 1 — see the DECISIONS.md entry for why, given Celery already
exists in this repo, Option 1 was still the founder's pick). ``ImportBatch`` itself IS the job
row: ``status`` already carries ``ready`` -> ``running`` -> ``done``/``paused``, so claiming is
just an atomic status flip under ``select_for_update(skip_locked=True)`` — no new table, no new
infra.

``run`` drives one claimed batch through ``engine.resume_batch``, using that function's
``on_chunk`` hook (added alongside this session) to write progress/heartbeat and check the
``batch.stats["control"]`` pause/cancel flags between every chunk — the only two points a batch
this size can safely be interrupted (spec step 20: recovery after interruption; a chunk itself is
already all-or-nothing via ``engine``'s own transaction).
"""
from __future__ import annotations

import time
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from erp.identity.roles import BRANCH_MANAGER

from .adapters._rbac import require_role
from .engine import resume_batch
from .models import ImportBatch

IMPORTS_SYNC_LIMIT = 500  # rows — below this, the API runs the batch inline (spec: "extremely fast")
HEARTBEAT_STALE_SECONDS = 5 * 60


def should_run_inline(batch: ImportBatch) -> bool:
    """True when ``batch`` is small enough to run synchronously in the API request instead of
    waiting for a ``run_imports`` pass."""
    return batch.row_count < IMPORTS_SYNC_LIMIT


# --- claim -----------------------------------------------------------------------------------
def claim_next() -> ImportBatch | None:
    """Exclusively claim one batch to work on: the oldest ``ready`` one, or — crash recovery —
    the oldest ``running`` one whose heartbeat has gone stale (a process that died mid-batch).
    ``skip_locked=True`` means a second concurrent claimer skips a row already locked by the
    first rather than blocking on it, so two runner processes never claim the same batch."""
    with transaction.atomic():
        batch = (
            ImportBatch.objects.select_for_update(skip_locked=True)
            .filter(status=ImportBatch.Status.READY)
            .order_by("created_at")
            .first()
        )
        if batch is None:
            batch = _claim_stale_running()
        if batch is None:
            return None

        stats = dict(batch.stats or {})
        stats["heartbeat"] = timezone.now().isoformat()
        batch.stats = stats
        batch.status = ImportBatch.Status.RUNNING
        batch.save(update_fields=["stats", "status"])
        return batch


def _claim_stale_running() -> ImportBatch | None:
    cutoff = timezone.now() - timedelta(seconds=HEARTBEAT_STALE_SECONDS)
    for batch in (
        ImportBatch.objects.select_for_update(skip_locked=True)
        .filter(status=ImportBatch.Status.RUNNING)
        .order_by("created_at")
    ):
        heartbeat = (batch.stats or {}).get("heartbeat")
        parsed = parse_datetime(heartbeat) if heartbeat else None
        if parsed is None or parsed < cutoff:
            return batch
    return None


# --- run -------------------------------------------------------------------------------------
def run(actor, batch: ImportBatch) -> dict:
    """Drive one claimed (``running``) batch to completion, pause, or cancellation — whichever
    the chunk loop or a control flag decides first. Progress (``rows_done``, a rolling
    ``rows_per_sec``, ``eta_seconds``, ``stage``) and the heartbeat are refreshed after every
    chunk, whether or not anything ends up interrupting the run."""
    started_at = time.monotonic()
    rows_done_at_start = batch.processed_count

    def on_chunk(current: ImportBatch) -> str | None:
        _update_progress(current, started_at, rows_done_at_start)
        control = (current.stats or {}).get("control", {})
        if control.get("cancel"):
            return "cancel"
        if control.get("pause"):
            return "pause"
        return None

    # claim_next already flipped status to `running`, so this call is a "resume" whether or not
    # any chunk has run yet — resume_batch's readiness/status handling is identical either way.
    return resume_batch(actor, batch, on_chunk=on_chunk)


def _update_progress(batch: ImportBatch, started_at: float, rows_done_at_start: int) -> None:
    elapsed = max(time.monotonic() - started_at, 0.001)
    done_this_run = max(batch.processed_count - rows_done_at_start, 0)
    rate = done_this_run / elapsed
    remaining = max(batch.row_count - batch.processed_count, 0)
    eta_seconds = round(remaining / rate) if rate > 0 else None

    stats = dict(batch.stats or {})
    stats.update({
        "heartbeat": timezone.now().isoformat(),
        "rows_done": batch.processed_count,
        "rows_per_sec": round(rate, 2),
        "eta_seconds": eta_seconds,
        "stage": "importing",
    })
    batch.stats = stats
    batch.save(update_fields=["stats"])


# --- control (permission-checked flag setters) ------------------------------------------------
def request_pause(actor, batch: ImportBatch) -> None:
    require_role(actor, BRANCH_MANAGER)
    _set_control(batch, pause=True)


def request_cancel(actor, batch: ImportBatch) -> None:
    require_role(actor, BRANCH_MANAGER)
    _set_control(batch, cancel=True)


def request_resume(actor, batch: ImportBatch) -> None:
    """Clear the pause flag and re-queue a paused batch for the next ``run_imports`` pass."""
    require_role(actor, BRANCH_MANAGER)
    _set_control(batch, pause=False)
    if batch.status == ImportBatch.Status.PAUSED:
        batch.status = ImportBatch.Status.READY
        batch.save(update_fields=["status"])


def _set_control(batch: ImportBatch, **flags: bool) -> None:
    stats = dict(batch.stats or {})
    control = dict(stats.get("control", {}))
    control.update(flags)
    stats["control"] = control
    batch.stats = stats
    batch.save(update_fields=["stats"])
