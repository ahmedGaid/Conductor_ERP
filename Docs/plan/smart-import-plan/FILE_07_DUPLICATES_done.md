# SESSION 7 — Smart Duplicate Detection
# Files: erp/imports/duplicates.py (new), erp/imports/validate.py (extend), erp/imports/tests/test_duplicates.py (new)

---

## Before You Start

1. Open `erp/imports/validate.py` + `analyze.py` (session 6) → where exact natural-key
   duplicates are already flagged. This session adds the FUZZY tier on top.
2. Open `erp/imports/mapping.py` → reuse `levenshtein` + Arabic text normalization.

"Do not write anything yet."

---

## Task A — `duplicates.py`: fuzzy candidate matching (spec step 9)

```python
def similarity(a: str, b: str) -> int:
    """0–100. Normalized (Arabic-folded, lowercased, legal-suffix-stripped) comparison:
    token-set overlap + levenshtein on the joined form. Suffix list ar+en:
    شركة/مؤسسة/التجارية/Co/Company/Trading/Ltd/LLC — 'Ahmed' vs 'Ahmed Trading' scores high."""

def find_candidates(actor, adapter, batch) -> None:
    """For rows NOT exact-matched: compare normalized name against existing records
    (prefetched once per entity) AND against other new rows in the batch.
    ≥85 → row.status="duplicate", row.issues += {code:"probable_duplicate",
    candidates:[{pk|row_number, label, score}]}. Below 85 → leave valid. Cap 3 candidates."""
```

Blocking guard for scale: compare only within same first-token bucket or same code prefix —
never all-pairs over 100k rows.

## Task B — Decisions (never auto-merge — spec's hard rule)

Extend `ImportRow.decision` handling in validate.py:

- `{"duplicate": "merge", "target_pk": …}` → row will UPDATE the target (strategy permitting)
- `{"duplicate": "create"}` → import as new despite the match
- `{"duplicate": "ignore"}` → status `skipped`

`apply_decision(actor, batch, row_id, decision)` validates the shape, sets status, returns the
revalidated row. Default when undecided: **skip** (safe), counted in the summary. The engine
NEVER merges without an explicit decision — enforce in code, assert in tests.

## Task C — Tests

"Ahmed" / "Ahmed Co" / "Ahmed Company" / "Ahmed Trading" cluster ≥85 among themselves; the
Arabic equivalents (أحمد التجارية…) too. Distinct names ("Ahmed" vs "Mohamed Trading") stay
below. Decision paths: merge/create/ignore each set the right status; undecided → skipped at
execute-readiness check; no code path mutates DB records here.

---

## Smoke Test

- [ ] Spec's Ahmed cluster → flagged with scores ≈96-level confidence, 3 candidates max
- [ ] Arabic-name variants cluster the same way
- [ ] No decision → row skips, never merges
- [ ] 10k-row batch: candidate pass finishes in seconds (bucketing works)
- [ ] `pytest erp/imports` green

---

## After This Session

```
Smoke test passed?
→ Rename with _done. Update erp-status. /compact.
→ Open FILE_08_AUTO_MASTERS.md in a FRESH session.
```
