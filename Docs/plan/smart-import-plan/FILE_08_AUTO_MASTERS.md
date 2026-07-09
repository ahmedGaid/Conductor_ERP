# SESSION 8 — Automatic Master-Data Creation
# Files: erp/imports/masters.py (new), erp/imports/tests/test_masters.py (new)

> Model note: Sonnet fits this session.

---

## Before You Start

1. Open `erp/imports/analyze.py` → `new_refs` stats + `missing_ref` issue shape (session 6).
2. Open `erp/imports/adapters/__init__.py` → adapter `defaults` + `write` (session 5).
3. Re-read STRATEGY §3 mechanic 3: writes are human-in-the-loop. Auto-create = auto-PROPOSED,
   one-click-confirmed — never silent.

"Do not write anything yet."

---

## Task A — `masters.py`: the creation plan (spec step 7)

```python
def build_creation_plan(actor, batch) -> dict:
    """From missing_ref issues: distinct (entity, value) pairs → proposed records using the
    ref entity's adapter FieldSpecs + IMPORTS_DEFAULTS. Dedupe against fuzzy candidates
    (session 7 similarity ≥85 against existing → propose LINK to existing instead of create).
    Persist to batch.stats["creation_plan"]:
    [{entity, value, proposed: {...}, action: "create"|"link", link_pk?, editable: true}]."""

def execute_creation_plan(actor, batch, approved: list) -> dict:
    """ONLY approved entries. Create via adapter.write (module service → its own audit),
    in dependency order (units/categories/warehouses before items; items before nothing).
    Record each created pk in batch.stats["created_masters"] (rollback anchor, report line).
    Then re-run the ref lookups for affected rows → missing_ref issues clear → rows flip valid."""
```

Batch-level confirmation is ONE approval action for the whole plan (with per-line untick in
the UI, session 13) — not 800 separate confirms. The confirm sentence pattern:
"Create 35 customers, 820 items, 2 warehouses; link 3 to existing records."

## Task B — Permission split

A user allowed to import invoices but NOT create items: creation-plan entries for entities the
actor can't write → marked `blocked_permission` with the module's own error message (blame-free,
actionable — "ask an inventory manager to approve" pattern used elsewhere). Plan executes the
allowed subset; blocked refs stay as missing_ref blockers.

## Task C — Tests

Plan builds distinct proposals (same customer in 40 rows → ONE entry); link-instead-of-create
when a fuzzy match exists; dependency order (item creation after its new unit); permission-
blocked entity → plan entry marked, execute skips it; after execute, previously-blocked rows
revalidate to valid.

---

## Smoke Test

- [ ] Invoice fixture referencing 3 unknown customers + 2 unknown items → plan with 5 entries
- [ ] Approve → masters exist (module audit fired), rows flip to valid without re-upload
- [ ] Fuzzy-near ref proposes LINK, not a near-duplicate create
- [ ] Actor without item permission → items entry blocked, customers still created
- [ ] `pytest erp/imports` green

---

## After This Session

```
Smoke test passed?
→ Rename with _done. Update erp-status. /compact.
→ Open FILE_09_EXECUTION_ENGINE.md in a FRESH session.
```
