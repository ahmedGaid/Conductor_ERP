# SESSION 6 — Analyze Existing Data + Validation Engine
# Files: erp/imports/validate.py (new), erp/imports/analyze.py (new), erp/imports/tests/test_validate.py (new)

---

## Before You Start

1. Open `erp/imports/registry.py`, `normalize.py`, `models.py` — this session wires them.
2. Open `erp/imports/adapters/crm.py` → `exists` / `lookup` shapes.

"Do not write anything yet."

---

## Task A — `analyze.py`: the pre-import diff (spec step 6)

```python
def analyze(actor, batch) -> dict:
    """Stream all rows (readers.iter_rows) → normalize_row → write ImportRow records in bulk
    chunks of 500 (raw+normalized+issues; bulk_create is FINE here — ImportRow is OUR working
    table, not business data). While streaming, collect distinct values per ref field and
    natural keys. Then ONE batched exists/lookup pass per ref entity (values IN query, not
    per-row queries — this is the 100k-row path).
    Returns stats: {rows, existing: {customers: n, …}, new_refs: {customers: [names…up to 50],
    items: [...]}, issues_by_code, duplicates_in_file}."""
```

`duplicates_in_file`: same natural key appearing twice INSIDE the file → later rows flagged
`duplicate_in_file` (spec step 8 tail). Stats saved to `batch.stats`, batch → `previewing`.

## Task B — `validate.py`: the row gate (spec step 14)

```python
def validate_row(actor, adapter, row: ImportRow, ref_cache) -> list[Issue]:
    """Field-spec checks (required present, kind parsed OK — from normalize issues) +
    reference checks against the pre-built ref_cache (unknown customer/warehouse/unit →
    issue code "missing_ref" with entity+value — session 8 consumes these) +
    adapter.validate() domain rules (negative qty, invalid account…).
    Sets row.status: valid / error / duplicate."""

def validate_batch(actor, batch) -> stats     # runs after analyze and after every user edit
def revalidate_rows(actor, batch, row_ids)    # the inline-edit fast path (spec step 15) —
                                              # single rows revalidate in <100ms using ref_cache
```

**Duplicate vs existing:** natural key matches DB → status `duplicate` (decision UI in
session 7/13 decides). `missing_ref` is NOT an error dead-end — it's a structured blocker
(actionable, ARP mechanic 5).

## Task C — Tests

Batched-query discipline: analyze on a 1k-row fixture runs O(entities) lookup queries, not
O(rows) — assert with `django.test.utils.CaptureQueriesContext`. Missing-ref rows carry
entity+value. Edit → revalidate flips error→valid. In-file duplicate flagged once, first
occurrence stays valid.

---

## Smoke Test

- [ ] 1k-row invoice-ish fixture: analyze < a few seconds, query count independent of row count
- [ ] Stats match spec-step-6 shape: "35 new customers, 820 new items…"
- [ ] Row missing customer → `missing_ref` issue, not a bare error string
- [ ] Single-row revalidate touches only that row
- [ ] `pytest erp/imports` green

---

## After This Session

```
Smoke test passed?
→ Rename with _done. Update erp-status. /compact.
→ Open FILE_07_DUPLICATES.md in a FRESH session.
```
