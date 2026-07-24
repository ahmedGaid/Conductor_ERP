"""Existing-data diff + row materialization (plan session 06).

``analyze`` is the first server-side pass over an uploaded file, once a header→field mapping has
been chosen (deterministic match, AI fallback, or a saved profile — session 03). It streams the
file through the FILE_02 reader, cleans every cell through the FILE_04 normalizer, and writes one
``ImportRow`` per source row in bulk chunks — a 100k-row file costs one read pass, not several
(``ImportRow`` is our own working table, so ``bulk_create`` here is fine; it never touches business
data). While it streams, it also collects the values every "ref" field will need resolved
(customer names, item skus, …) and the natural keys used to catch in-file duplicates. Both are then
resolved in ONE pass per target entity, over the DISTINCT values only — never one query per row.
"""
from __future__ import annotations

import datetime as _dt
from collections import Counter
from decimal import Decimal

from . import readers
from .models import ImportBatch, ImportRow
from .normalize import normalize_row
from .registry import FieldSpec, Issue
from .registry import get as get_adapter

CHUNK_SIZE = 500
NEW_REFS_SAMPLE = 50


def analyze(actor, batch: ImportBatch) -> dict:
    """Stream every row of ``batch.source_file`` into ``ImportRow`` records; return pre-import stats.

    Stats shape: ``{rows, existing: {entity: n, …}, new_refs: {entity: [values…up to 50], …},
    issues_by_code: {code: n, …}, duplicates_in_file}``. ``existing``/``new_refs`` are grouped by
    the REFERENCED entity (``FieldSpec.ref``) — empty for every adapter with no "ref" fields (the
    four master adapters today), never a crash. Also saves the stats onto ``batch`` and moves it to
    ``previewing``.
    """
    adapter = get_adapter(batch.entity)
    ref_fields = [f for f in adapter.fields if f.kind == "ref"]

    raw_bytes = _read_source(batch)
    seen_natural_keys: set[tuple] = set()
    ref_values: dict[str, set[str]] = {f.name: set() for f in ref_fields}
    issues_by_code: Counter = Counter()
    duplicates_in_file = 0
    row_count = 0
    chunk: list[ImportRow] = []

    for row_number, raw_row in readers.iter_rows(raw_bytes):
        normalized, issues = normalize_row(adapter, batch.mapping, raw_row)
        if not adapter.group_by:
            # For a grouped (document) adapter, natural_key IS the group_by field (session
            # convention — see registry.py), so every line of one legitimate multi-line document
            # shares it by design. Row-level in-file dedup only makes sense for one-row-per-record
            # master adapters; grouping.py's own header-conflict/missing-key checks are the
            # document-shaped equivalent (FILE_15 CONFIRMED SCOPE).
            issues = _flag_in_file_duplicate(adapter, normalized, issues, seen_natural_keys)
            if issues and issues[-1].code == "duplicate_in_file":
                duplicates_in_file += 1

        for field_spec in ref_fields:
            value = normalized.get(field_spec.name)
            if value not in (None, ""):
                ref_values[field_spec.name].add(value)
        for issue in issues:
            issues_by_code[issue.code] += 1

        chunk.append(ImportRow(
            batch=batch,
            row_number=row_number,
            raw=raw_row,
            normalized=_json_safe(normalized),
            issues=[i.as_dict() for i in issues],
        ))
        row_count += 1
        if len(chunk) >= CHUNK_SIZE:
            ImportRow.objects.bulk_create(chunk)
            chunk = []
    if chunk:
        ImportRow.objects.bulk_create(chunk)

    existing, new_refs = _resolve_refs(actor, adapter, ref_fields, ref_values)
    stats = {
        "rows": row_count,
        "existing": existing,
        "new_refs": new_refs,
        "issues_by_code": dict(issues_by_code),
        "duplicates_in_file": duplicates_in_file,
    }
    batch.stats = stats
    batch.row_count = row_count
    batch.status = ImportBatch.Status.PREVIEWING
    batch.save(update_fields=["stats", "row_count", "status"])
    return stats


def _flag_in_file_duplicate(adapter, normalized: dict, issues: list[Issue], seen: set[tuple]) -> list[Issue]:
    """Same natural key seen twice in this file → later rows get ``duplicate_in_file`` (spec step 8
    tail). The FIRST occurrence is never flagged — only a repeat is a duplicate of something."""
    key = tuple(normalized.get(k) for k in adapter.natural_key)
    if not any(part not in (None, "") for part in key):
        return issues  # an all-blank natural key can't collide with anything
    if key in seen:
        return [*issues, Issue(field="", code="duplicate_in_file", message="imports.issues.duplicateInFile")]
    seen.add(key)
    return issues


def _resolve_refs(
    actor, adapter, ref_fields: list[FieldSpec], ref_values: dict[str, set[str]],
) -> tuple[dict[str, int], dict[str, list[str]]]:
    """One ``adapter.lookup`` call per DISTINCT value per ref field — bounded by distinct values,
    never by row count. Adapters with no ref fields (today: all four master adapters) return
    ``({}, {})`` without ever calling ``lookup``."""
    existing: dict[str, int] = {}
    new_refs: dict[str, list[str]] = {}
    for field_spec in ref_fields:
        entity = field_spec.ref or field_spec.name
        found = 0
        missing: list[str] = []
        for value in sorted(ref_values.get(field_spec.name, ())):
            if adapter.lookup(actor, field_spec.name, value) is not None:
                found += 1
            elif len(missing) < NEW_REFS_SAMPLE:
                missing.append(value)
        if found:
            existing[entity] = existing.get(entity, 0) + found
        if missing:
            new_refs.setdefault(entity, []).extend(missing)
    return existing, new_refs


def _read_source(batch: ImportBatch) -> bytes:
    attachment = batch.source_file
    attachment.file.open("rb")
    try:
        return attachment.file.read()
    finally:
        attachment.file.close()


def _json_safe(normalized: dict) -> dict:
    """``normalize_row`` may hand back ``Decimal``/``date`` values — ``JSONField`` needs JSON-native
    types, so this is the one place that stringifies them for storage (money is already an int)."""
    out: dict = {}
    for k, v in normalized.items():
        if isinstance(v, Decimal):
            out[k] = str(v)
        elif isinstance(v, (_dt.datetime, _dt.date)):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out
