"""Execution engine: strategies, chunked commits, resume, rollback, report — plan session 09.

``execute_batch`` is the only thing that ever writes business records for an import. It gates on
readiness first (STRATEGY §3: writes are human-in-the-loop — nothing runs half-configured), then
walks every PENDING row (``valid``, or ``duplicate`` with an explicit ``merge`` decision — an
undecided duplicate already blocked readiness) in fixed-size chunks, each inside its own
transaction: a failure rolls back only that chunk, earlier chunks stay durable, and
``resume_batch`` picks up exactly where it stopped (pending-row selection makes re-running safe —
spec step 20, "recovery after interruption"). ``rollback_batch`` reverses in import order:
records the batch created and that expose a delete path are removed; everything else (an update
with no before-image, a record with no delete path, a posted/referenced document) is reported
``cannot_revert`` with a reason rather than guessed at.

The adapter Protocol (``registry.ImportAdapter``) has no ``update``/``delete`` today — no
registered adapter needs them yet (FILE_05/06 blocker: no module exposes an update/delete
service write-path for customers/items/suppliers/contacts). This module reads them via
``getattr`` duck-typing, exactly like ``supports_update``, so a future adapter can opt in without
this file changing: ``update(actor, normalized, *, target_pk=None) -> record`` (update the record
at ``target_pk``, or whatever ``adapter.exists`` found when ``target_pk`` is ``None``) and
``delete(actor, pk) -> None``. Until one exists, ``update_only``/``upsert`` and any ``merge``
duplicate decision fail the readiness gate by design, and every rollback of a created master
reports ``cannot_revert`` — both exercised here against a small in-memory fake adapter (same
"throwaway test adapter" pattern the rest of this plan uses for not-yet-built capabilities), plus
one end-to-end pass against the real ``customers`` adapter.
"""
from __future__ import annotations

from collections import Counter

from django.db import transaction

from erp.audit.models import AuditEntry
from erp.audit.services import record as audit_record

from .models import ImportBatch, ImportRow
from .registry import get as get_adapter
from .validate import execute_status

CHUNK = 200  # rows per transaction — small enough to keep locks short, big enough to be fast


class ReadinessError(Exception):
    """Raised before any row is touched — the batch isn't ready to run/resume. ``reasons`` is an
    actionable, blame-free list; never a bare message."""

    def __init__(self, reasons: list[str]):
        self.reasons = reasons
        super().__init__("; ".join(reasons))


# --- readiness -----------------------------------------------------------------------------------
def _undecided_duplicates(batch: ImportBatch) -> list[ImportRow]:
    return [
        row for row in batch.rows.filter(status=ImportRow.Status.DUPLICATE)
        if (row.decision or {}).get("duplicate") != "merge"
    ]


def _needs_update_support(batch: ImportBatch) -> bool:
    if batch.strategy in (ImportBatch.Strategy.UPDATE_ONLY, ImportBatch.Strategy.UPSERT):
        return True
    return any(
        (row.decision or {}).get("duplicate") == "merge"
        for row in batch.rows.filter(status=ImportRow.Status.DUPLICATE)
    )


def _readiness_reasons(adapter, batch: ImportBatch) -> list[str]:
    reasons: list[str] = []

    undecided = _undecided_duplicates(batch)
    if undecided:
        reasons.append(
            f"{len(undecided)} duplicate row(s) have no decision yet — merge, create, or ignore each first"
        )

    if _needs_update_support(batch) and not getattr(adapter, "supports_update", False):
        reasons.append(
            f"adapter '{adapter.entity}' does not support updates — choose create_only or "
            "skip_existing, or resolve merge decisions to create instead"
        )

    pending_plan = [
        e for e in (batch.stats or {}).get("creation_plan", [])
        if e.get("action") in ("create", "link") and "outcome" not in e
    ]
    if pending_plan:
        reasons.append(
            f"{len(pending_plan)} proposed master record(s) not yet approved — resolve the "
            "creation plan first (erp.imports.masters.execute_creation_plan)"
        )

    if batch.error_count and not (batch.stats or {}).get("continue_after_errors"):
        reasons.append(
            f"{batch.error_count} row(s) still have unresolved errors — fix them, or set "
            "batch.stats['continue_after_errors'] = True to run around them"
        )

    return reasons


# --- execute ---------------------------------------------------------------------------------
def execute_batch(actor, batch: ImportBatch, *, on_chunk=None) -> dict:
    """First-run entry point. Readiness gate, then run every pending row in chunks.

    ``on_chunk``, when given, is called with ``batch`` (freshly refreshed from the DB) after
    every successfully committed chunk — the background runner's (FILE_10) hook for progress/
    heartbeat and pause/cancel: return ``"pause"`` to stop after this chunk (``batch.status``
    becomes ``paused``, resumable later) or ``"cancel"`` to stop and skip every remaining pending
    row (``batch.status`` becomes ``done``). Anything else (``None``) continues to the next chunk.
    """
    return _run(actor, batch, on_chunk=on_chunk)


def resume_batch(actor, batch: ImportBatch, *, on_chunk=None) -> dict:
    """Continue a ``paused`` (or interrupted ``running``) batch. Same readiness gate and chunk
    loop as ``execute_batch`` — pending-row selection is what makes re-running safe: already-
    imported/skipped rows are durable and are never touched again."""
    if batch.status not in (ImportBatch.Status.PAUSED, ImportBatch.Status.RUNNING):
        raise ReadinessError([f"batch is '{batch.status}', not paused/running — nothing to resume"])
    return _run(actor, batch, on_chunk=on_chunk)


def _run(actor, batch: ImportBatch, *, on_chunk=None) -> dict:
    adapter = get_adapter(batch.entity)
    reasons = _readiness_reasons(adapter, batch)
    if reasons:
        raise ReadinessError(reasons)

    batch.status = ImportBatch.Status.RUNNING
    batch.save(update_fields=["status"])

    row_ids = list(
        batch.rows.filter(status__in=(ImportRow.Status.VALID, ImportRow.Status.DUPLICATE))
        .order_by("row_number").values_list("id", flat=True)
    )
    continue_after_errors = bool((batch.stats or {}).get("continue_after_errors"))

    for i in range(0, len(row_ids), CHUNK):
        chunk_ids = row_ids[i : i + CHUNK]
        try:
            with transaction.atomic():
                _execute_chunk(actor, adapter, batch, chunk_ids)
        except Exception as exc:  # noqa: BLE001
            stats = dict(batch.stats or {})
            stats["last_error"] = str(exc)
            batch.stats = stats
            batch.save(update_fields=["stats"])
            audit_record(
                module="imports", action="execute_chunk_failed", entity_type=batch.entity,
                entity_id=str(batch.pk), actor=actor, after={"error": str(exc)},
                result=AuditEntry.Result.FAILURE,
            )
            if not continue_after_errors:
                batch.status = ImportBatch.Status.PAUSED
                batch.save(update_fields=["status"])
                return build_report(batch)
            continue

        if on_chunk is not None:
            batch.refresh_from_db()
            signal = on_chunk(batch)
            if signal == "cancel":
                _cancel_remaining(batch)
                batch.status = ImportBatch.Status.DONE
                batch.save(update_fields=["status"])
                return build_report(batch)
            if signal == "pause":
                batch.status = ImportBatch.Status.PAUSED
                batch.save(update_fields=["status"])
                return build_report(batch)

    batch.refresh_from_db()
    batch.status = ImportBatch.Status.DONE
    batch.save(update_fields=["status"])
    return build_report(batch)


def _cancel_remaining(batch: ImportBatch) -> None:
    batch.rows.filter(
        status__in=(ImportRow.Status.VALID, ImportRow.Status.DUPLICATE)
    ).update(status=ImportRow.Status.SKIPPED, result_ref={})


def _execute_chunk(actor, adapter, batch: ImportBatch, row_ids: list) -> None:
    rows = list(ImportRow.objects.select_for_update().filter(id__in=row_ids).order_by("row_number"))
    imported = updated = created = skipped = 0

    for row in rows:
        if execute_status(row) == ImportRow.Status.SKIPPED:
            row.status = ImportRow.Status.SKIPPED
            row.result_ref = {}
            skipped += 1
            continue

        action, result_ref = _dispatch(actor, adapter, batch, row)
        row.status = action
        row.result_ref = result_ref
        if action == ImportRow.Status.IMPORTED:
            imported += 1
            if result_ref.get("action") == "updated":
                updated += 1
            else:
                created += 1
        else:
            skipped += 1

    ImportRow.objects.bulk_update(rows, ["status", "result_ref"])

    batch.refresh_from_db()
    batch.processed_count = batch.processed_count + len(rows)
    batch.save(update_fields=["processed_count"])

    audit_record(
        module="imports", action="execute_chunk", entity_type=batch.entity, entity_id=str(batch.pk),
        actor=actor, after={"imported": imported, "created": created, "updated": updated, "skipped": skipped},
    )


def _dispatch(actor, adapter, batch: ImportBatch, row: ImportRow) -> tuple[str, dict]:
    if row.status == ImportRow.Status.DUPLICATE:  # merge-decided; readiness already verified support
        target_pk = (row.decision or {}).get("target_pk")
        record = adapter.update(actor, row.normalized, target_pk=target_pk)
        return ImportRow.Status.IMPORTED, _result_ref(adapter, row, record, "updated")

    existing = adapter.exists(actor, row.normalized)
    strategy = batch.strategy

    if strategy == ImportBatch.Strategy.CREATE_ONLY:
        if existing is not None:
            return ImportRow.Status.SKIPPED, {}
        record = adapter.write(actor, row.normalized)
        return ImportRow.Status.IMPORTED, _result_ref(adapter, row, record, "created")

    if strategy == ImportBatch.Strategy.UPDATE_ONLY:
        if existing is None:
            return ImportRow.Status.SKIPPED, {}
        record = adapter.update(actor, row.normalized, target_pk=getattr(existing, "pk", None))
        return ImportRow.Status.IMPORTED, _result_ref(adapter, row, record, "updated")

    if strategy == ImportBatch.Strategy.UPSERT:
        if existing is not None:
            record = adapter.update(actor, row.normalized, target_pk=getattr(existing, "pk", None))
            return ImportRow.Status.IMPORTED, _result_ref(adapter, row, record, "updated")
        record = adapter.write(actor, row.normalized)
        return ImportRow.Status.IMPORTED, _result_ref(adapter, row, record, "created")

    if strategy == ImportBatch.Strategy.SKIP_EXISTING:
        if existing is not None:
            return ImportRow.Status.SKIPPED, {}
        record = adapter.write(actor, row.normalized)
        return ImportRow.Status.IMPORTED, _result_ref(adapter, row, record, "created")

    raise ValueError(f"unknown strategy: {strategy!r}")  # pragma: no cover — model choices are exhaustive


def _result_ref(adapter, row: ImportRow, record, action: str) -> dict:
    """A rollback/report anchor for whatever ``adapter.write``/``update`` returned. Several real
    adapters (customers/items/suppliers) return a lightweight ``*Info`` dataclass keyed by business
    code, not a Django model instance — there's no ``.pk``/``.id`` to read. Falls back to the
    adapter's own natural-key field on the record, then on the row, before giving up."""
    pk = getattr(record, "pk", None)
    if pk is None:
        pk = getattr(record, "id", None)
    if pk is None and adapter.natural_key:
        key_field = adapter.natural_key[0]
        pk = getattr(record, key_field, None) or row.normalized.get(key_field)
    return {
        "model": f"{type(record).__module__}.{type(record).__name__}",
        "pk": None if pk is None else str(pk),
        "action": action,
    }


# --- rollback --------------------------------------------------------------------------------
def rollback_batch(actor, batch: ImportBatch) -> dict:
    """Reverse an import in reverse row order. A created master/document with a ``delete`` on its
    adapter is removed via that module write-path; everything else — no delete path, an update
    (no before-image), a posted/referenced record — is reported ``cannot_revert`` with a reason
    instead of guessed at (index decision 7: rollback is reversal, never a raw delete around the
    module)."""
    adapter = get_adapter(batch.entity)
    reverted = skipped = 0
    cannot: list[dict] = []

    rows = list(batch.rows.filter(status=ImportRow.Status.IMPORTED).order_by("-row_number"))
    for row in rows:
        ref = row.result_ref or {}
        action = ref.get("action")
        if action == "created" and hasattr(adapter, "delete"):
            try:
                adapter.delete(actor, ref.get("pk"))
            except Exception as exc:  # noqa: BLE001
                cannot.append({"row": row.row_number, "pk": ref.get("pk"), "reason": str(exc)})
                continue
            row.status = ImportRow.Status.REVERTED
            reverted += 1
        elif action == "created":
            cannot.append({
                "row": row.row_number, "pk": ref.get("pk"),
                "reason": f"adapter '{adapter.entity}' has no delete path",
            })
        elif action == "updated":
            cannot.append({
                "row": row.row_number, "pk": ref.get("pk"),
                "reason": "an update has no before-image to restore",
            })
        else:
            skipped += 1
    if rows:
        ImportRow.objects.bulk_update(rows, ["status"])

    created_masters = (batch.stats or {}).get("created_masters", [])
    reverted_master_pks: list[str] = []
    for master in created_masters:
        master_adapter = _try_get_adapter(master["entity"])
        if master_adapter is not None and hasattr(master_adapter, "delete"):
            try:
                master_adapter.delete(actor, master["pk"])
                reverted_master_pks.append(master["pk"])
                continue
            except Exception as exc:  # noqa: BLE001
                cannot.append({"master": master, "reason": str(exc)})
                continue
        cannot.append({
            "master": master,
            "reason": f"adapter '{master['entity']}' has no delete path" if master_adapter else
                      f"no import adapter for entity '{master['entity']}'",
        })

    stats = dict(batch.stats or {})
    stats["rollback"] = {
        "reverted": reverted, "skipped": skipped, "cannot": cannot,
        "reverted_masters": reverted_master_pks,
    }
    batch.stats = stats
    batch.status = ImportBatch.Status.ROLLED_BACK
    batch.save(update_fields=["stats", "status"])

    audit_record(
        module="imports", action="rollback_batch", entity_type=batch.entity, entity_id=str(batch.pk),
        actor=actor, after={"reverted": reverted, "skipped": skipped, "cannot": len(cannot)},
    )
    return {"reverted": reverted, "skipped": skipped, "cannot": cannot}


def _try_get_adapter(entity: str):
    try:
        return get_adapter(entity)
    except KeyError:
        return None


# --- report ------------------------------------------------------------------------------------
def build_report(batch: ImportBatch) -> dict:
    """imported/updated/skipped/errors/warnings/created-masters/duration/by-entity counts + the
    per-row outcome list (spec step 22 backend; streamed CSV export is session 11's API concern)."""
    rows = list(batch.rows.all().order_by("row_number"))
    by_status = Counter(row.status for row in rows)
    by_action = Counter(
        (row.result_ref or {}).get("action") for row in rows if row.status == ImportRow.Status.IMPORTED
    )
    error_rows = [{"row": r.row_number, "issues": r.issues} for r in rows if r.status == ImportRow.Status.ERROR]
    warning_rows = [
        {"row": r.row_number, "issues": [i for i in r.issues if i.get("code") == "probable_duplicate"]}
        for r in rows if any(i.get("code") == "probable_duplicate" for i in r.issues)
    ]
    duration_seconds = None
    if batch.updated_at and batch.created_at:
        duration_seconds = (batch.updated_at - batch.created_at).total_seconds()

    return {
        "batch_id": batch.pk,
        "entity": batch.entity,
        "status": batch.status,
        "imported": by_status.get(ImportRow.Status.IMPORTED, 0),
        "created": by_action.get("created", 0),
        "updated": by_action.get("updated", 0),
        "skipped": by_status.get(ImportRow.Status.SKIPPED, 0),
        "errors": len(error_rows),
        "error_rows": error_rows,
        "warnings": warning_rows,
        "created_masters": (batch.stats or {}).get("created_masters", []),
        "duration_seconds": duration_seconds,
        "row_outcomes": [
            {"row": r.row_number, "status": r.status, "result_ref": r.result_ref} for r in rows
        ],
    }
