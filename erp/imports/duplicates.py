"""Fuzzy duplicate detection — plan session 07.

``validate.py`` already catches EXACT natural-key duplicates (in-file repeats and DB matches via
``adapter.exists``). This module adds a FUZZY tier on top, for rows that look like the same
business entity under a different spelling — "Ahmed" vs "Ahmed Trading Co" vs "أحمد التجارية" — so
a messy spreadsheet doesn't quietly create three customers for one company.

``find_candidates`` never decides anything by itself: it only flags a row as ``duplicate`` with
scored candidates attached. The user always makes the call — merge into an existing record, create
anyway, or ignore the match — via ``validate.apply_decision``. The engine never auto-merges.
"""
from __future__ import annotations

from collections import defaultdict

from .mapping import levenshtein, normalize_header
from .models import ImportBatch, ImportRow

MAX_CANDIDATES = 3
SCORE_THRESHOLD = 85

# Legal-entity suffixes stripped before comparison (ar + en) so "Ahmed" and "Ahmed Trading Co"
# fold to the same core name. Normalized via the same ``normalize_header`` folding as the words
# they're matched against (case/diacritic/Arabic-letter insensitive).
_LEGAL_SUFFIXES = {
    normalize_header(w) for w in (
        "شركة", "مؤسسة", "التجارية", "Co", "Company", "Trading", "Ltd", "LLC",
    )
}


def _fold(name: str) -> str:
    """Comparison key: header-style normalization (Arabic-fold, lowercase, punctuation-strip)
    plus legal-suffix removal, so only the company's actual name is left to compare."""
    tokens = [t for t in normalize_header(name).split(" ") if t and t not in _LEGAL_SUFFIXES]
    return " ".join(tokens)


def _bucket_key(name: str) -> str:
    """Blocking key for the candidate scan: the folded name's first token. Two names can only be
    compared if they share this key — the scale guard that keeps the pass off all-pairs O(n^2)."""
    folded = _fold(name)
    return folded.split(" ")[0] if folded else ""


def similarity(a: str, b: str) -> int:
    """0-100. Token-set overlap OR whole-string Levenshtein closeness on the folded, suffix-
    stripped forms — whichever reads the pair as more alike. Token overlap catches word-order and
    dropped/added suffix words ("Ahmed" vs "Ahmed Trading"); Levenshtein catches typos within a
    single-token name."""
    fa, fb = _fold(a), _fold(b)
    if not fa or not fb:
        return 0
    if fa == fb:
        return 100
    ta, tb = set(fa.split(" ")), set(fb.split(" "))
    token_score = len(ta & tb) / len(ta | tb) if (ta or tb) else 0.0
    joined_a, joined_b = fa.replace(" ", ""), fb.replace(" ", "")
    longest = max(len(joined_a), len(joined_b), 1)
    dist = levenshtein(joined_a, joined_b, max_distance=longest)
    lev_score = max(0.0, 1 - dist / longest)
    return round(100 * max(token_score, lev_score))


def _name_field(adapter) -> str | None:
    """The field fuzzy-matching compares — an entity with no ``name`` field (none registered
    today) simply gets no fuzzy pass."""
    return "name" if any(f.name == "name" for f in adapter.fields) else None


def find_candidates(actor, adapter, batch: ImportBatch) -> None:
    """Flag rows that probably duplicate an existing record or another row in this same batch.
    Only considers rows ``validate_batch`` left VALID (exact matches are already handled). Existing
    records are prefetched once via ``adapter.existing_labels``; both existing and in-batch
    comparisons are bucketed by first-token so cost scales with cluster size, never row-count^2."""
    name_field = _name_field(adapter)
    if name_field is None:
        return

    rows = list(ImportRow.objects.filter(batch=batch, status=ImportRow.Status.VALID))
    if not rows:
        return

    existing_buckets: dict[str, list[tuple[object, str]]] = defaultdict(list)
    for pk, label in adapter.existing_labels(actor):
        if label:
            existing_buckets[_bucket_key(label)].append((pk, label))

    row_names: dict[int, str] = {}
    row_buckets: dict[str, list[ImportRow]] = defaultdict(list)
    for row in rows:
        value = row.normalized.get(name_field)
        if value:
            row_names[row.id] = value
            row_buckets[_bucket_key(value)].append(row)

    updated: list[ImportRow] = []
    for row in rows:
        value = row_names.get(row.id)
        if not value:
            continue
        bucket = _bucket_key(value)
        scored: list[tuple[int, dict]] = []
        for pk, label in existing_buckets.get(bucket, ()):
            score = similarity(value, label)
            if score >= SCORE_THRESHOLD:
                scored.append((score, {"pk": str(pk), "label": label, "score": score}))
        for other in row_buckets.get(bucket, ()):
            if other.id == row.id:
                continue
            other_value = row_names[other.id]
            score = similarity(value, other_value)
            if score >= SCORE_THRESHOLD:
                scored.append((score, {
                    "row_number": other.row_number, "label": other_value, "score": score,
                }))
        if not scored:
            continue
        scored.sort(key=lambda t: -t[0])
        candidates = [c for _, c in scored[:MAX_CANDIDATES]]

        row.status = ImportRow.Status.DUPLICATE
        row.issues = [*row.issues, {
            "field": name_field,
            "code": "probable_duplicate",
            "message": "imports.issues.probableDuplicate",
            "meta": {"candidates": candidates},
        }]
        updated.append(row)

    if updated:
        ImportRow.objects.bulk_update(updated, ["status", "issues"])
