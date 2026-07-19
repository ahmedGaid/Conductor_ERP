"""Deterministic auto-fix pass (spec step 16) — small, always-previewable corrections over rows
still ``error`` after ``validate_batch``. NO model call in v1 (AI-assisted autofix deferred,
recorded in DECISIONS.md at FILE_17 acceptance). Each fix is
``{row_id, row, field, from, to, code}``; nothing is applied until ``apply_fixes`` runs the
caller-approved subset — the same batch-confirm discipline as ``masters.py``.

A carry-over quirk worth knowing (FILE_06, not this session's to fix): ``validate_row`` re-adds a
parse-time issue (``date_invalid``, ``money_invalid``, …) from the row's OWN stored ``issues``
list verbatim — it never re-parses. So the only way to actually clear one is to remove it from
``row.issues`` before re-validating, which is exactly what ``apply_fixes`` does (directly, not via
``decision.edits`` — an edit alone would leave the old issue carried over forever).
"""
from __future__ import annotations

from .mapping import levenshtein, normalize_header
from .models import ImportBatch, ImportRow
from .normalize import _CURRENCY_WORDS, parse_date
from .registry import Issue
from .registry import get as get_adapter
from .validate import revalidate_rows

CURRENCY_FIX_MAX_DISTANCE = 1

# date_ambiguous is a WARNING (the value is already usable — a day-first guess), but validate.py's
# status rule still blocks the row on it (anything outside duplicate_in_file/probable_duplicate
# is blocking). The "fix" is accepting that reading, not producing a different value — so it's
# proposed even when to == from, and any other code needs an ACTUAL changed value to count.
_ACCEPT_AS_IS_CODES = frozenset({"date_ambiguous"})


def preview_fixes(batch: ImportBatch) -> list[dict]:
    """Every proposable fix across every ``error`` row — read-only, mutates nothing."""
    adapter = get_adapter(batch.entity)
    field_specs = {f.name: f for f in adapter.fields}
    mapping = dict(batch.mapping or {})
    fixes: list[dict] = []

    for row in batch.rows.filter(status=ImportRow.Status.ERROR).order_by("row_number"):
        for issue in row.issues:
            field = issue.get("field")
            code = issue.get("code")
            spec = field_specs.get(field)
            if spec is None:
                continue
            current = row.normalized.get(field)

            if code in _ACCEPT_AS_IS_CODES:
                if current is not None:
                    fixes.append(_fix(row, field, current, current, code))
                continue

            header = mapping.get(field)
            raw_value = row.raw.get(header) if header else None
            fixed = _propose(spec, code, current, raw_value)
            if fixed is not None and fixed != current:
                fixes.append(_fix(row, field, current, fixed, code))
    return fixes


def apply_fixes(actor, batch: ImportBatch, accepted: list[dict]) -> dict:
    """Apply exactly the caller-approved fixes (each ``{row_id, field, to, code}`` — normally the
    exact dicts ``preview_fixes`` returned, or a caller-edited subset) and re-validate every
    affected row. ``preview_fixes`` never mutates anything; only this does."""
    # Keyed by str(pk): a fix dict that made a round trip through JSON (the API's preview ->
    # apply flow) carries row_id as a string, not the UUID object preview_fixes originally put
    # there — normalize both sides so the lookup below can't miss on type alone.
    by_row: dict[str, list[dict]] = {}
    for fix in accepted:
        by_row.setdefault(str(fix["row_id"]), []).append(fix)
    if not by_row:
        return {"valid": 0, "error": 0, "duplicate": 0}

    rows = list(ImportRow.objects.filter(batch=batch, id__in=by_row.keys()))
    for row in rows:
        for fix in by_row[str(row.pk)]:
            row.normalized = {**row.normalized, fix["field"]: fix["to"]}
            row.issues = [
                i for i in row.issues
                if not (i.get("field") == fix["field"] and i.get("code") == fix["code"])
            ]
    ImportRow.objects.bulk_update(rows, ["normalized", "issues"])

    return revalidate_rows(actor, batch, list(by_row.keys()))


def _fix(row: ImportRow, field: str, from_, to_, code: str) -> dict:
    return {"row_id": row.pk, "row": row.row_number, "field": field, "from": from_, "to": to_, "code": code}


def _propose(spec, code: str, current, raw_value):
    if code == "required_missing":
        return spec.default

    if code == "date_invalid" and raw_value is not None:
        alt = parse_date(raw_value, dayfirst=False)  # the flip: parse_date's own default is dayfirst=True
        return None if isinstance(alt, Issue) else alt.isoformat()

    if code == "currency_unknown" and isinstance(raw_value, str):
        return _nearest_currency(raw_value)

    if isinstance(current, str) and current != current.strip():
        return current.strip()  # trim/space fix — the last-resort, code-agnostic pass
    return None


def _nearest_currency(raw_value: str) -> str | None:
    key = normalize_header(raw_value)
    if not key:
        return None
    best_word, best_dist = None, CURRENCY_FIX_MAX_DISTANCE + 1
    for word in _CURRENCY_WORDS:
        d = levenshtein(key, word, max_distance=CURRENCY_FIX_MAX_DISTANCE)
        if d < best_dist:
            best_word, best_dist = word, d
    return _CURRENCY_WORDS[best_word] if best_word is not None else None
