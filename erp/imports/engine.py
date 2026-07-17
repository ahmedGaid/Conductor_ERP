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

Grouped (document) adapters set ``adapter.group_by`` (FILE_15): rows bucket into one write call per
document (``_build_groups``/``_execute_chunk_grouped``) instead of one per row — see those
functions' docstrings. Every adapter with ``group_by = None`` (every master today) runs the
original one-row-one-write path unchanged.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from django.db import transaction

from erp.audit.models import AuditEntry
from erp.audit.services import record as audit_record

from .models import ImportBatch, ImportRow
from .registry import Issue
from .registry import get as get_adapter
from .registry import group_key as _group_key
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

    # Ungrouped (every master adapter): one unit == one row, exactly as before. Grouped (a document
    # adapter — FILE_15): one unit == one document's rows, bucketed by ``adapter.group_by`` — a
    # group-level failure errors only that document, never the surrounding chunk (see
    # ``_execute_chunk_grouped``).
    if adapter.group_by:
        ordered_rows = list(ImportRow.objects.filter(id__in=row_ids).order_by("row_number"))
        units: list[tuple[list[int], Issue | None]] = [
            ([row.id for row in group["rows"]], group["issue"])
            for group in _build_groups(adapter, ordered_rows)
        ]
    else:
        units = [([rid], None) for rid in row_ids]

    for i in range(0, len(units), CHUNK):
        chunk_units = units[i : i + CHUNK]
        chunk_ids = [rid for ids, _issue in chunk_units for rid in ids]
        try:
            with transaction.atomic():
                if adapter.group_by:
                    _execute_chunk_grouped(actor, adapter, batch, chunk_units)
                else:
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

        action, result_ref, warnings = _dispatch(actor, adapter, batch, row)
        row.status = action
        row.result_ref = result_ref
        if warnings:
            row.issues = [*row.issues, *[w.as_dict() for w in warnings]]
        if action == ImportRow.Status.IMPORTED:
            imported += 1
            if result_ref.get("action") == "updated":
                updated += 1
            else:
                created += 1
        else:
            skipped += 1

    ImportRow.objects.bulk_update(rows, ["status", "result_ref", "issues"])

    batch.refresh_from_db()
    batch.processed_count = batch.processed_count + len(rows)
    batch.save(update_fields=["processed_count"])

    audit_record(
        module="imports", action="execute_chunk", entity_type=batch.entity, entity_id=str(batch.pk),
        actor=actor, after={"imported": imported, "created": created, "updated": updated, "skipped": skipped},
    )


def _write_row(adapter, actor, normalized: dict) -> tuple[Any, list[Issue]]:
    """Mirrors ``_dispatch_group``'s ``_write()`` helper — ``adapter.write`` may return the record
    alone (every adapter built before this) or ``(record, warnings)`` (session 16b: a row-level
    adapter that needs to flag something non-blocking, e.g. an unmatched payment)."""
    result = adapter.write(actor, normalized)
    if isinstance(result, tuple) and len(result) == 2:
        return result
    return result, []


def _dispatch(actor, adapter, batch: ImportBatch, row: ImportRow) -> tuple[str, dict, list[Issue]]:
    if row.status == ImportRow.Status.DUPLICATE:  # merge-decided; readiness already verified support
        target_pk = (row.decision or {}).get("target_pk")
        record = adapter.update(actor, row.normalized, target_pk=target_pk)
        return ImportRow.Status.IMPORTED, _result_ref(adapter, row.normalized, record, "updated"), []

    existing = adapter.exists(actor, row.normalized)
    strategy = batch.strategy

    if strategy == ImportBatch.Strategy.CREATE_ONLY:
        if existing is not None:
            return ImportRow.Status.SKIPPED, {}, []
        record, warnings = _write_row(adapter, actor, row.normalized)
        return ImportRow.Status.IMPORTED, _result_ref(adapter, row.normalized, record, "created"), warnings

    if strategy == ImportBatch.Strategy.UPDATE_ONLY:
        if existing is None:
            return ImportRow.Status.SKIPPED, {}, []
        record = adapter.update(actor, row.normalized, target_pk=getattr(existing, "pk", None))
        return ImportRow.Status.IMPORTED, _result_ref(adapter, row.normalized, record, "updated"), []

    if strategy == ImportBatch.Strategy.UPSERT:
        if existing is not None:
            record = adapter.update(actor, row.normalized, target_pk=getattr(existing, "pk", None))
            return ImportRow.Status.IMPORTED, _result_ref(adapter, row.normalized, record, "updated"), []
        record, warnings = _write_row(adapter, actor, row.normalized)
        return ImportRow.Status.IMPORTED, _result_ref(adapter, row.normalized, record, "created"), warnings

    if strategy == ImportBatch.Strategy.SKIP_EXISTING:
        if existing is not None:
            return ImportRow.Status.SKIPPED, {}, []
        record, warnings = _write_row(adapter, actor, row.normalized)
        return ImportRow.Status.IMPORTED, _result_ref(adapter, row.normalized, record, "created"), warnings

    raise ValueError(f"unknown strategy: {strategy!r}")  # pragma: no cover — model choices are exhaustive


def _result_ref(adapter, normalized: dict, record, action: str) -> dict:
    """A rollback/report anchor for whatever ``adapter.write``/``update`` returned. Several real
    adapters (customers/items/suppliers) return a lightweight ``*Info`` dataclass keyed by business
    code, not a Django model instance — there's no ``.pk``/``.id`` to read. Falls back to the
    adapter's own natural-key field on the record, then on ``normalized`` (a row's ``.normalized``,
    or a document group's header+lines payload), before giving up."""
    pk = getattr(record, "pk", None)
    if pk is None:
        pk = getattr(record, "id", None)
    if pk is None and adapter.natural_key:
        key_field = adapter.natural_key[0]
        pk = getattr(record, key_field, None) or normalized.get(key_field)
    return {
        "model": f"{type(record).__module__}.{type(record).__name__}",
        "pk": None if pk is None else str(pk),
        "action": action,
    }


# --- execute — grouped (document adapters, ``adapter.group_by`` set — FILE_15) ------------------
def _build_groups(adapter, rows: list[ImportRow]) -> list[dict]:
    """Bucket ``rows`` (ordered by ``row_number``, already VALID/DUPLICATE) into documents by
    ``registry.group_key``. A blank-key row attaches to whichever group came right before it in
    file order UNLESS it still carries its own header data (``adapter.header_fields`` all blank is
    the merged-cell signal; any of them non-blank on a blank-key row is ambiguous, never guessed
    at) — that case, and a blank-key row with no group open yet, becomes its own one-row "orphan"
    group carrying a ``missing_group_key`` issue. Returns ``[{"rows": [...], "issue": Issue|None}]``
    in first-seen order (orphans last); ``issue`` set means the whole group errors without ever
    calling ``adapter.write``."""
    header_fields = getattr(adapter, "header_fields", [])
    buckets: dict[Any, list[ImportRow]] = {}
    order: list[Any] = []
    orphans: list[ImportRow] = []
    current_key: Any = None

    for row in rows:
        key = _group_key(adapter, row.normalized)
        if key is None:
            has_header_data = any(row.normalized.get(f) not in (None, "") for f in header_fields)
            if current_key is None or has_header_data:
                orphans.append(row)
                continue
            key = current_key
        else:
            current_key = key
        if key not in buckets:
            buckets[key] = []
            order.append(key)
        buckets[key].append(row)

    groups = [
        {"rows": buckets[key], "issue": _header_conflict_issue(header_fields, buckets[key])}
        for key in order
    ]
    if orphans:
        groups.append({
            "rows": orphans,
            "issue": Issue(
                field=adapter.group_by, code="missing_group_key",
                message="imports.issues.missingGroupKey",
            ),
        })
    return groups


def _header_conflict_issue(header_fields: list[str], rows: list[ImportRow]) -> Issue | None:
    """The first header field that carries two different non-blank values across ``rows`` — a
    dirty-data case (e.g. two customer names under one invoice number), never silently resolved."""
    for field_name in header_fields:
        seen = None
        for row in rows:
            value = row.normalized.get(field_name)
            if value in (None, ""):
                continue
            if seen is None:
                seen = value
            elif value != seen:
                return Issue(
                    field=field_name, code="inconsistent_document",
                    message="imports.issues.inconsistentDocument",
                )
    return None


def _group_payload(header_fields: list[str], rows: list[ImportRow]) -> dict:
    """One document's write payload: each header field taken from the first row that has it
    (the merged-cell pattern — normally the group's first row), plus every row's normalized values
    as ``lines``."""
    header: dict = {}
    for field_name in header_fields:
        for row in rows:
            value = row.normalized.get(field_name)
            if value not in (None, ""):
                header[field_name] = value
                break
    return {**header, "lines": [row.normalized for row in rows]}


def _validate_group(adapter, actor, batch: ImportBatch, payload: dict) -> list[Issue]:
    """Optional pre-write, group-level validation for a document adapter — duck-typed via
    ``getattr`` exactly like ``header_fields``/``update``/``delete``, so a master adapter or a
    document adapter that doesn't need it simply omits it (unchanged behaviour for every adapter
    built before FILE_16). ``validate_group(actor, payload, batch) -> list[Issue]`` runs AFTER the
    group's payload is assembled and BEFORE ``adapter.write``: a non-empty return errors the whole
    document (its rows → ERROR carrying those issues) and the write never runs — the balanced-entry
    guard the finance adapters need, which ``write`` raising can only ever express as a generic
    ``group_write_failed``. The hook may also MUTATE ``payload`` in place to inject engine-approved
    generated lines (``account_opening``'s human-approved suspense correction) that ``write`` then
    consumes; it is handed ``batch`` so it can read/record an approval decision in ``batch.stats``."""
    hook = getattr(adapter, "validate_group", None)
    if hook is None:
        return []
    return hook(actor, payload, batch)


def _dispatch_group(actor, adapter, batch: ImportBatch, payload: dict) -> tuple[str, dict, list[Issue]]:
    """Same strategy dispatch as ``_dispatch``, scoped to one document's payload instead of one
    row. ``adapter.write`` may return either the record alone, or ``(record, warnings)`` — the
    latter lets a document adapter attach a non-blocking issue (e.g. ``total_mismatch``) without
    changing the return contract every master adapter already relies on."""

    def _write() -> tuple[Any, list[Issue]]:
        result = adapter.write(actor, payload)
        if isinstance(result, tuple) and len(result) == 2:
            return result
        return result, []

    existing = adapter.exists(actor, payload)
    strategy = batch.strategy

    if strategy == ImportBatch.Strategy.CREATE_ONLY:
        if existing is not None:
            return ImportRow.Status.SKIPPED, {}, []
        record, warnings = _write()
        return ImportRow.Status.IMPORTED, _result_ref(adapter, payload, record, "created"), warnings

    if strategy == ImportBatch.Strategy.UPDATE_ONLY:
        if existing is None:
            return ImportRow.Status.SKIPPED, {}, []
        record = adapter.update(actor, payload, target_pk=getattr(existing, "pk", None))
        return ImportRow.Status.IMPORTED, _result_ref(adapter, payload, record, "updated"), []

    if strategy == ImportBatch.Strategy.UPSERT:
        if existing is not None:
            record = adapter.update(actor, payload, target_pk=getattr(existing, "pk", None))
            return ImportRow.Status.IMPORTED, _result_ref(adapter, payload, record, "updated"), []
        record, warnings = _write()
        return ImportRow.Status.IMPORTED, _result_ref(adapter, payload, record, "created"), warnings

    if strategy == ImportBatch.Strategy.SKIP_EXISTING:
        if existing is not None:
            return ImportRow.Status.SKIPPED, {}, []
        record, warnings = _write()
        return ImportRow.Status.IMPORTED, _result_ref(adapter, payload, record, "created"), warnings

    raise ValueError(f"unknown strategy: {strategy!r}")  # pragma: no cover — model choices are exhaustive


def _execute_chunk_grouped(
    actor, adapter, batch: ImportBatch, chunk_units: list[tuple[list[int], Issue | None]],
) -> None:
    """One transaction (savepoint scope from the caller's ``transaction.atomic()``) covering
    several documents. Each document's write runs in its OWN nested ``transaction.atomic()`` — a
    savepoint — so one bad document (a pre-flagged header conflict, or ``adapter.write`` raising)
    rolls back only that document's rows to ERROR and the rest of the chunk's documents still
    commit; the whole-chunk abort-and-pause behaviour ``_execute_chunk`` relies on for masters would
    turn "one dirty invoice" into "the whole file didn't import" — never what FILE_15 asks for."""
    header_fields = getattr(adapter, "header_fields", [])
    imported = created = updated = skipped = errored = 0

    for row_ids, issue in chunk_units:
        rows = list(ImportRow.objects.select_for_update().filter(id__in=row_ids).order_by("row_number"))
        if not rows:
            continue  # pragma: no cover — defensive; every unit is built from real row ids

        if issue is not None:
            for row in rows:
                row.status = ImportRow.Status.ERROR
                row.issues = [*row.issues, issue.as_dict()]
            ImportRow.objects.bulk_update(rows, ["status", "issues"])
            errored += len(rows)
            continue

        payload = _group_payload(header_fields, rows)

        group_issues = _validate_group(adapter, actor, batch, payload)
        if group_issues:
            issue_dicts = [gi.as_dict() for gi in group_issues]
            for row in rows:
                row.status = ImportRow.Status.ERROR
                row.issues = [*row.issues, *issue_dicts]
            ImportRow.objects.bulk_update(rows, ["status", "issues"])
            errored += len(rows)
            continue

        try:
            with transaction.atomic():
                action, result_ref, warnings = _dispatch_group(actor, adapter, batch, payload)
        except Exception as exc:  # noqa: BLE001 — isolate to this document only, see docstring
            fail_issue = Issue(field="", code="group_write_failed", message=str(exc)).as_dict()
            for row in rows:
                row.status = ImportRow.Status.ERROR
                row.issues = [*row.issues, fail_issue]
            ImportRow.objects.bulk_update(rows, ["status", "issues"])
            errored += len(rows)
            continue

        warning_dicts = [w.as_dict() for w in warnings]
        for row in rows:
            row.status = action
            row.result_ref = result_ref
            if warning_dicts:
                row.issues = [*row.issues, *warning_dicts]
        ImportRow.objects.bulk_update(rows, ["status", "result_ref", "issues"] if warning_dicts else
                                       ["status", "result_ref"])
        if action == ImportRow.Status.IMPORTED:
            imported += len(rows)
            if result_ref.get("action") == "updated":
                updated += len(rows)
            else:
                created += len(rows)
        else:
            skipped += len(rows)

    batch.refresh_from_db()
    batch.processed_count = batch.processed_count + sum(len(ids) for ids, _issue in chunk_units)
    batch.save(update_fields=["processed_count"])

    audit_record(
        module="imports", action="execute_chunk", entity_type=batch.entity, entity_id=str(batch.pk),
        actor=actor,
        after={"imported": imported, "created": created, "updated": updated,
               "skipped": skipped, "errored": errored},
    )


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
    # A grouped document's rows (FILE_15) all share one ``result_ref`` (same pk — one write call per
    # document, many rows). Revert that pk once; every other row of the same document just follows
    # its status without a second delete call or a second count.
    reverted_pks: set[tuple] = set()
    cannot_pks: set[tuple] = set()  # a created document whose delete already failed — report it once

    rows = list(batch.rows.filter(status=ImportRow.Status.IMPORTED).order_by("-row_number"))
    for row in rows:
        ref = row.result_ref or {}
        action = ref.get("action")
        dedupe_key = (action, ref.get("pk"))
        if action == "created" and dedupe_key in reverted_pks:
            row.status = ImportRow.Status.REVERTED
            continue
        if action == "created" and dedupe_key in cannot_pks:
            continue  # sibling row of a document already reported cannot_revert — don't re-report it
        if action == "created" and hasattr(adapter, "delete"):
            try:
                adapter.delete(actor, ref.get("pk"))
            except Exception as exc:  # noqa: BLE001
                cannot.append({"row": row.row_number, "pk": ref.get("pk"), "reason": str(exc)})
                cannot_pks.add(dedupe_key)
                continue
            row.status = ImportRow.Status.REVERTED
            reverted += 1
            reverted_pks.add(dedupe_key)
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
