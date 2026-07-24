"""Shared document-grouping logic (FILE_15 CONFIRMED SCOPE, 2026-07-23) — the one place that knows
how to bucket rows into documents, spot a header conflict, and estimate a document's total. Both
the analyze/validate path (pre-execution preview) and ``engine.py`` (execution) call this module —
one copy, so preview and execute can never quietly disagree about what a "bad" document looks like.

The engine core never imports a business-module model (``registry.py``'s own rule), so
``compute_subtotal_minor`` below is a PURE re-derivation of the rounding rule every document
adapter's ``write()`` already applies (gross = round-half-up(qty * unit_price), minus an optional
discount) — not a call into ``erp.sales``/``erp.purchasing``. It exists only to preview a number
before anything is written; execute-time still compares against the module service's own
authoritative computed total (``adapter.write()`` still calls ``total_mismatch_issue`` too, just
with the real posted total instead of this estimate).
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from .models import ImportRow
from .registry import Issue
from .registry import group_key as _group_key

# Issue codes this module attaches — stripped and recomputed on every ``annotate_groups`` call so
# repeated calls (e.g. after an inline edit) never pile up stale copies.
_GROUP_ISSUE_CODES = frozenset({"missing_group_key", "inconsistent_document", "total_mismatch"})


def _round_minor(amount: Any) -> int:
    return int(Decimal(str(amount)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def build_groups(adapter, rows: list[ImportRow]) -> list[dict]:
    """Bucket ``rows`` (ordered by ``row_number``) into documents by ``registry.group_key``. A
    blank-key row attaches to whichever group came right before it in file order UNLESS it still
    carries its own header data (``adapter.header_fields`` all blank is the merged-cell signal; any
    of them non-blank on a blank-key row is ambiguous, never guessed at) — that case, and a
    blank-key row with no group open yet, becomes its own one-row "orphan" group carrying a
    ``missing_group_key`` issue. Returns ``[{"key": ..., "rows": [...], "issue": Issue|None}]`` in
    first-seen order (orphans last); ``issue`` set means the whole group errors without ever
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
        {"key": key, "rows": buckets[key], "issue": header_conflict_issue(header_fields, buckets[key])}
        for key in order
    ]
    for row in orphans:
        groups.append({
            "key": None,
            "rows": [row],
            "issue": Issue(
                field=adapter.group_by, code="missing_group_key",
                message="imports.issues.missingGroupKey",
            ),
        })
    return groups


def header_conflict_issue(header_fields: list[str], rows: list[ImportRow]) -> Issue | None:
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


def forward_filled_header(header_fields: list[str], rows: list[ImportRow]) -> dict:
    """Each header field taken from the first row that has it — the merged-cell pattern (normally
    the group's first row). Shared by ``engine._group_payload`` (execute) and ``annotate_groups``
    (preview) so both read a document's header identically."""
    header: dict = {}
    for field_name in header_fields:
        for row in rows:
            value = row.normalized.get(field_name)
            if value not in (None, ""):
                header[field_name] = value
                break
    return header


def compute_subtotal_minor(rows: list[ImportRow]) -> int | None:
    """Pure re-derivation of a document's subtotal from its lines — round-half-up(qty *
    unit_price_minor) per line, minus an optional discount_minor — the exact arithmetic every
    document adapter's ``write()`` applies via the real order/quotation service (same generic line
    field names across all five adapters). Returns ``None`` when a line is missing the inputs
    needed to estimate it — never guesses at a total."""
    subtotal = 0
    for row in rows:
        qty = row.normalized.get("quantity")
        price = row.normalized.get("unit_price_minor")
        if qty in (None, "") or price in (None, ""):
            return None
        try:
            gross = _round_minor(Decimal(str(qty)) * Decimal(str(price)))
        except (InvalidOperation, ValueError, TypeError):
            return None
        discount = int(row.normalized.get("discount_minor") or 0)
        subtotal += gross - discount
    return subtotal


def total_mismatch_issue(file_total_minor: Any, computed_total_minor: int | None) -> Issue | None:
    """The one shared comparison both the execute-time adapters and the preview annotation call —
    never trust a file's own total column, but never block on a disagreement either (spec: warning,
    not error). ``None`` when either side is unknown (nothing to compare)."""
    if file_total_minor is None or computed_total_minor is None:
        return None
    if int(file_total_minor) == computed_total_minor:
        return None
    return Issue(
        field="file_total_minor", code="total_mismatch",
        message="imports.issues.totalMismatch",
        meta={"file_total_minor": int(file_total_minor), "computed_total_minor": computed_total_minor},
    )


def annotate_groups(adapter, rows: list[ImportRow]) -> None:
    """Pre-execution preview of exactly the issues ``engine.py`` would produce at execute time —
    group ``rows``, attach any group-level issue to every row in that group, and stamp each row's
    ``group_meta`` (group id / first-line flag / forward-filled header / estimated total / line
    count) for the review API. Idempotent: strips any group-level issue this function previously
    attached before recomputing, so it is safe to call again after an inline edit
    (``validate.revalidate_rows``). Mutates ``rows`` in place; the caller persists via
    ``bulk_update`` (include ``"group_meta"`` in the field list)."""
    header_fields = getattr(adapter, "header_fields", [])
    groups = build_groups(adapter, rows)

    for index, group in enumerate(groups):
        group_rows = group["rows"]
        group_id = f"g{index}"
        header = forward_filled_header(header_fields, group_rows)
        structural_issue = group["issue"]
        computed_total = None if structural_issue is not None else compute_subtotal_minor(group_rows)
        mismatch = (
            None if structural_issue is not None
            else total_mismatch_issue(header.get("file_total_minor"), computed_total)
        )

        for line_index, row in enumerate(group_rows):
            row.issues = [d for d in row.issues if d.get("code") not in _GROUP_ISSUE_CODES]
            if structural_issue is not None:
                row.issues.append(structural_issue.as_dict())
                row.status = ImportRow.Status.ERROR
            elif mismatch is not None:
                row.issues.append(mismatch.as_dict())
            row.group_meta = {
                "group_id": group_id,
                "is_first": line_index == 0,
                "key": group["key"],
                "header": header,
                "computed_total_minor": computed_total,
                "line_count": len(group_rows),
            }
