"""Row validation — the gate before preview/execute (plan session 06).

``analyze`` already stamped every ``ImportRow`` with its normalize-time issues (bad dates, a
missing required field, …). ``validate_row`` adds what only the DATABASE can answer: does a "ref"
field resolve to a real record, and does the adapter's own domain rule (negative qty, invalid
account, …) accept the row. ``validate_batch`` runs this over a whole batch using a ``ref_cache``
built ONCE — so per-row cost afterwards is a dict lookup, not a query. ``revalidate_rows`` is the
same gate scoped to a handful of rows: the inline-edit fast path, so fixing one cell doesn't
re-touch the other 99,999.

Duplicate vs existing: a natural-key match against the DB sets ``status = duplicate`` (the
decision — merge / create anyway / skip — is a session 07/13 concern, not this one's). A
``missing_ref`` is never a bare error string — it carries ``{entity, value}`` in ``Issue.meta`` so
session 08's auto-create-masters flow can act on it directly.
"""
from __future__ import annotations

from . import grouping
from .models import ImportBatch, ImportRow
from .registry import Issue
from .registry import get as get_adapter

# ``duplicate_in_file``/``probable_duplicate`` mark a row DUPLICATE, not ERROR — a duplicate is a
# decision to make (session 07's ``apply_decision``), never a blocker on its own.
_NON_BLOCKING_CODES = frozenset({"duplicate_in_file", "probable_duplicate"})

# Codes ``normalize_row``/``analyze`` stamped onto the row that ``validate_row`` does NOT
# recompute — carried over as-is. These all come from parsing the RAW cell text (a bad date
# string, an unparseable amount, …); ``revalidate_rows`` never reparses raw text, it only folds
# ``decision.edits`` straight into ``normalized``, so there is nothing new to recompute here.
# ``required_missing`` is NOT one of these — it's a blank/non-blank check on ``normalized``
# itself, which DOES change after an edit, so it is recomputed below instead of carried over
# (a carried-over required_missing would never clear once an edit filled the field in).
_CARRY_OVER_CODES = frozenset({
    "date_invalid", "date_ambiguous", "money_invalid", "number_invalid", "currency_unknown",
    "phone_invalid", "email_invalid", "tax_id_invalid", "tax_id_length",
    "duplicate_in_file",
})


def _build_ref_cache(actor, adapter, rows) -> dict[tuple[str, str], object]:
    """One ``adapter.lookup`` call per DISTINCT ``(field, value)`` pair across ``rows`` — the same
    distinct-values discipline as ``analyze._resolve_refs``, just scoped to whatever rows are
    being (re)validated right now."""
    ref_fields = [f for f in adapter.fields if f.kind == "ref"]
    if not ref_fields:
        return {}
    distinct: dict[str, set[str]] = {f.name: set() for f in ref_fields}
    for row in rows:
        for field_spec in ref_fields:
            value = row.normalized.get(field_spec.name)
            if value not in (None, ""):
                distinct[field_spec.name].add(value)
    cache: dict[tuple[str, str], object] = {}
    for field_spec in ref_fields:
        for value in distinct[field_spec.name]:
            cache[(field_spec.name, value)] = adapter.lookup(actor, field_spec.name, value)
    return cache


def validate_row(actor, adapter, row: ImportRow, ref_cache: dict) -> list[Issue]:
    """Field-spec issues already on the row (from ``normalize``) + reference checks against
    ``ref_cache`` + the adapter's own domain rules. Never queries the DB itself — the cache and
    ``adapter.validate``/``adapter.exists`` are the only DB touchpoints, both already batched or
    inherently per-row by the adapter contract."""
    issues = [_issue_from_dict(d) for d in row.issues if d.get("code") in _CARRY_OVER_CODES]

    for field_spec in adapter.fields:
        if field_spec.required and row.normalized.get(field_spec.name) in (None, ""):
            issues.append(Issue(
                field=field_spec.name, code="required_missing", message="imports.issues.requiredMissing",
            ))

    for field_spec in adapter.fields:
        if field_spec.kind != "ref":
            continue
        value = row.normalized.get(field_spec.name)
        if value in (None, ""):
            continue
        if ref_cache.get((field_spec.name, value)) is None:
            meta = {"entity": field_spec.ref, "value": value}
            # Optional adapter hook: extra context for this ref (e.g. the row's supplier for an item
            # ref), so the masters resolver/capture is supplier-scoped. Duck-typed like header_fields.
            ref_context = getattr(adapter, "ref_context", None)
            if callable(ref_context):
                meta.update(ref_context(row.normalized, field_spec.name) or {})
            issues.append(Issue(
                field=field_spec.name,
                code="missing_ref",
                message="imports.issues.missingRef",
                meta=meta,
            ))

    issues.extend(adapter.validate(actor, row.normalized))
    return issues


def _status_for(adapter, actor, row: ImportRow, issues: list[Issue]) -> str:
    if any(i.code not in _NON_BLOCKING_CODES for i in issues):
        return ImportRow.Status.ERROR
    if any(i.code == "duplicate_in_file" for i in issues):
        return ImportRow.Status.DUPLICATE
    if adapter.exists(actor, row.normalized) is not None:
        return ImportRow.Status.DUPLICATE
    return ImportRow.Status.VALID


def _recompute_in_file_duplicates(adapter, rows: list[ImportRow], issues_map: dict) -> set:
    """Whole-batch in-file-duplicate detection, mirroring ``analyze._flag_in_file_duplicate``'s
    "first occurrence is never flagged" rule. In-file duplicate is a cross-row concept — fixing
    THIS row's natural key can newly create or clear ANOTHER row's ``duplicate_in_file`` flag — so
    it is always rescanned over every row currently in the batch instead of trusting whatever
    ``analyze()`` saw on its one-time first pass (the same permanent-carry-over bug
    ``required_missing`` had). Mutates ``issues_map[row.pk]`` in place; returns the set of row
    pks whose duplicate membership actually changed (grouped adapters never call this — they skip
    ``natural_key`` dedup entirely in favor of ``grouping.annotate_groups``)."""
    changed: set = set()
    seen: set[tuple] = set()
    for row in sorted(rows, key=lambda r: r.row_number):
        issues = issues_map[row.pk]
        had = any(i.code == "duplicate_in_file" for i in issues)
        issues[:] = [i for i in issues if i.code != "duplicate_in_file"]
        key = tuple(row.normalized.get(k) for k in adapter.natural_key)
        is_dup = False
        if any(part not in (None, "") for part in key):
            if key in seen:
                is_dup = True
                issues.append(Issue(field="", code="duplicate_in_file", message="imports.issues.duplicateInFile"))
            else:
                seen.add(key)
        if had != is_dup:
            changed.add(row.pk)
    return changed


def validate_batch(actor, batch: ImportBatch) -> dict:
    """Validate every row of ``batch`` — runs right after ``analyze`` and again after any bulk
    re-mapping. Builds one ``ref_cache`` for the whole batch."""
    adapter = get_adapter(batch.entity)
    rows = list(batch.rows.all())
    ref_cache = _build_ref_cache(actor, adapter, rows)

    issues_map = {row.pk: validate_row(actor, adapter, row, ref_cache) for row in rows}
    if not adapter.group_by and adapter.natural_key:
        _recompute_in_file_duplicates(adapter, rows, issues_map)
    for row in rows:
        issues = issues_map[row.pk]
        row.issues = [i.as_dict() for i in issues]
        row.status = _status_for(adapter, actor, row, issues)

    update_fields = ["issues", "status"]
    if adapter.group_by:
        # Pre-execution preview of the same group-level issues engine.py would produce at execute
        # time (FILE_15 CONFIRMED SCOPE) — may additionally flip some rows to ERROR, so this runs
        # BEFORE counts are tallied below.
        grouping.annotate_groups(adapter, rows)
        update_fields.append("group_meta")

    counts = {"valid": 0, "error": 0, "duplicate": 0}
    for row in rows:
        counts[row.status] = counts.get(row.status, 0) + 1
    ImportRow.objects.bulk_update(rows, update_fields)

    batch.error_count = counts.get("error", 0)
    batch.status = ImportBatch.Status.READY
    batch.save(update_fields=["error_count", "status"])
    return counts


def revalidate_rows(actor, batch: ImportBatch, row_ids: list[int]) -> dict:
    """Re-validate exactly ``row_ids`` — the inline-edit fast path (spec step 15). A row's
    ``decision.edits`` (field → corrected value) are folded into ``normalized`` first, so fixing a
    date or filling in a missing reference actually changes what gets checked. ``ref_cache`` is
    scoped to only these rows, so a single-row edit costs O(1) lookups, not a full-batch rebuild."""
    adapter = get_adapter(batch.entity)
    rows = list(ImportRow.objects.filter(batch=batch, id__in=row_ids))
    for row in rows:
        edits = row.decision.get("edits") or {}
        if edits:
            row.normalized = {**row.normalized, **edits}
    ref_cache = _build_ref_cache(actor, adapter, rows)  # built AFTER edits so a fixed ref resolves

    issues_map = {row.pk: validate_row(actor, adapter, row, ref_cache) for row in rows}

    if not adapter.group_by and adapter.natural_key:
        # Same whole-batch reasoning as the grouped branch below: an edit here can flip another,
        # untouched row's duplicate_in_file flag, so every row's current issues (not just the
        # ones just edited) feed the rescan — see `_recompute_in_file_duplicates`.
        edited_ids = {row.pk for row in rows}
        other_rows = list(
            ImportRow.objects.filter(batch=batch).exclude(pk__in=edited_ids).order_by("row_number")
        )
        for row in other_rows:
            issues_map[row.pk] = [_issue_from_dict(d) for d in row.issues]
        changed_ids = _recompute_in_file_duplicates(adapter, rows + other_rows, issues_map)
        stale = [row for row in other_rows if row.pk in changed_ids]
        for row in stale:
            issues = issues_map[row.pk]
            row.issues = [i.as_dict() for i in issues]
            row.status = _status_for(adapter, actor, row, issues)
        if stale:
            ImportRow.objects.bulk_update(stale, ["issues", "status"])

    for row in rows:
        issues = issues_map[row.pk]
        row.issues = [i.as_dict() for i in issues]
        row.status = _status_for(adapter, actor, row, issues)
    ImportRow.objects.bulk_update(rows, ["normalized", "issues", "status"])

    if not adapter.group_by:
        counts = {"valid": 0, "error": 0, "duplicate": 0}
        for row in rows:
            counts[row.status] = counts.get(row.status, 0) + 1
        _sync_error_count(batch)
        return counts

    # A group-level issue (header conflict / missing key / total mismatch) can only be judged
    # across the WHOLE document, not just the edited row(s) — refetch every row of the batch and
    # re-annotate, then report counts over the post-annotation state. Grouped-entity files are
    # invoice-shaped (small), so this trades the O(1) fast path for correctness here.
    all_rows = list(ImportRow.objects.filter(batch=batch).order_by("row_number"))
    grouping.annotate_groups(adapter, all_rows)
    ImportRow.objects.bulk_update(all_rows, ["issues", "status", "group_meta"])

    counts = {"valid": 0, "error": 0, "duplicate": 0}
    for row in all_rows:
        counts[row.status] = counts.get(row.status, 0) + 1
    _sync_error_count(batch)
    return counts


def _sync_error_count(batch: ImportBatch) -> None:
    """``ImportBatch.error_count`` is a denormalized counter the EXECUTE readiness gate reads
    (``engine._readiness_reasons``) — it must reflect the batch's CURRENT rows, not whatever
    ``validate_batch`` saw on the initial pass. ``revalidate_rows`` changes row statuses via
    inline edits without ever touching this field otherwise, which left it permanently stale:
    fixing every row's error could never clear the gate (same staleness bug class as
    ``required_missing``/``duplicate_in_file`` — this is the batch-level instance of it)."""
    batch.error_count = ImportRow.objects.filter(batch=batch, status=ImportRow.Status.ERROR).count()
    batch.save(update_fields=["error_count"])


_DUPLICATE_DECISIONS = frozenset({"merge", "create", "ignore"})


def apply_decision(actor, batch: ImportBatch, row_id: int, decision: dict) -> ImportRow:
    """Record a human duplicate decision on one row — session 07's hard rule: the engine NEVER
    merges without this explicit call.

    ``decision`` is ``{"duplicate": "merge", "target_pk": ...}``, ``{"duplicate": "create"}``, or
    ``{"duplicate": "ignore"}``. The row is re-validated first (so a bundled edit — e.g. fixing the
    name — is reflected), then the decision's outcome is applied: ``ignore`` → ``skipped``;
    ``merge`` → stays ``duplicate`` (the execution engine reads ``target_pk`` off ``decision``);
    ``create`` needs no override — revalidation alone drops the fuzzy flag and the row lands on its
    own merits (``valid`` unless something else is wrong with it).
    """
    kind = decision.get("duplicate")
    if kind not in _DUPLICATE_DECISIONS:
        raise ValueError(f"unknown duplicate decision: {decision!r}")
    if kind == "merge" and not decision.get("target_pk"):
        raise ValueError("merge decision requires target_pk")

    row = ImportRow.objects.get(batch=batch, id=row_id)
    row.decision = {**(row.decision or {}), **decision}
    row.save(update_fields=["decision"])

    revalidate_rows(actor, batch, [row.id])
    row.refresh_from_db()

    if kind == "ignore":
        row.status = ImportRow.Status.SKIPPED
        row.save(update_fields=["status"])
    elif kind == "merge":
        row.status = ImportRow.Status.DUPLICATE
        row.save(update_fields=["status"])
    return row


def execute_status(row: ImportRow) -> str:
    """Read-only: the status a row executes as, given its decision (or the safe default when
    undecided). Never mutates the row — only ``apply_decision``/the execution engine (session 09)
    write. A ``duplicate`` row with no ``merge``/``ignore`` decision defaults to ``skipped``: the
    engine never imports — and never merges — an undecided probable duplicate."""
    if row.status != ImportRow.Status.DUPLICATE:
        return row.status
    if (row.decision or {}).get("duplicate") == "merge":
        return ImportRow.Status.DUPLICATE
    return ImportRow.Status.SKIPPED


def _issue_from_dict(d: dict) -> Issue:
    return Issue(
        field=d.get("field", ""), code=d.get("code", ""), message=d.get("message", ""),
        meta=d.get("meta") or {},
    )
