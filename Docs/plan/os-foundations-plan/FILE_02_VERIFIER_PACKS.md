# FILE_02 — L1: Verifier framework + invariant packs (standalone)

> ONE SESSION. Prereq: FILE_01 `_done` (pack names referenced from `Action.invariants`).
> Backend-only. The packs are built and unit-tested here; wiring into the confirm flow is FILE_03.

## Why

"The model narrates; it never computes" becomes mechanical here: after any agent write, a
deterministic pack checks the books, not the model. Packs are pure read-only functions — they never
fix anything themselves (compensation is FILE_03's job) and never depend on the LLM.

## Framework shape

NEW package `erp/assistant/verifier/`:

```
erp/assistant/verifier/__init__.py      # registry: PACKS: dict[str, Pack]; run(names, scope) -> Report
erp/assistant/verifier/packs.py         # the 6 pack functions
erp/assistant/tests/test_verifier.py
```

```python
@dataclass(frozen=True)
class Finding:
    pack: str
    ok: bool
    message: str          # human, blame-free, English (i18n happens at the card layer, FILE_03/05)
    data: dict            # machine detail: {account, expected, actual, ...}

@dataclass(frozen=True)
class Report:
    ok: bool              # AND of all findings
    findings: tuple[Finding, ...]
```

`run(names, scope)`: looks up each name in `PACKS`, calls it with `scope` (a dict the caller
builds: `{"links": [...], "payload": {...}, "actor": ...}` — the records the action just touched),
collects findings. Unknown pack name → a failing finding, never a crash (defense in depth).
Every pack is **read-only** (asserted by convention + a test that wraps each pack in
`transaction.atomic` + rollback and diffs row counts).

## The 6 packs (each scoped to the touched records when possible, whole-system when cheap)

| Pack name | Invariant | Data source |
|---|---|---|
| `trial_balance` | total debits == total credits (whole system — the query is one aggregate) | `erp/accounting/services/reports.py::trial_balance` (L46) |
| `journal_balanced` | the touched journal entry's debit sum == credit sum | entry lines via the link in scope |
| `stock_non_negative` | no `StockBalance` row for the touched item/warehouse goes below zero | `erp/inventory/services/stock.py` balances |
| `sequence_unbroken` | the touched document's number sequence (per prefix, per year) has no gaps | the module's `number` column, prefix pattern from the touched record |
| `doc_totals` | the touched document's header total == sum of its line totals (integer minor units) | the document via the link in scope |
| `period_open` | the touched document's date falls in an open fiscal period | `erp/accounting` fiscal period models |

Notes:
- Money comparisons are integer-minor-unit equality — never float, never Decimal tolerance.
- Packs receiving a scope without the record kind they check return `ok=True` with
  `message="not applicable"` (a sales-order confirm shouldn't fail `journal_balanced`).
- `sequence_unbroken` reuses the per-module prefix convention (`SO-{year}-`, see
  `erp/sales/services/orders.py::_next_number` L72).

## Tasks

### [ ] T2.1 — Framework: registry, `run()`, Report/Finding

- **Goal:** `verifier.run(["trial_balance"], scope)` returns a `Report`; unknown names fail soft.
- **Files:** NEW `erp/assistant/verifier/__init__.py`; NEW `erp/assistant/tests/test_verifier.py`.
- **Steps:** implement the shapes above with `PACKS` populated by a `@pack("name")` decorator;
  `run()` never raises (a pack that throws becomes a failing finding with the exception class in
  `data` — traces stay out of user-facing text). Then tighten FILE_01's deferred check: the
  `_validate_action` invariant rule in `actions.py` now asserts every declared name exists in
  `PACKS` (remove the `# tightened in FILE_02` placeholder).
- **Accept:** tests green: unknown pack → failing finding; throwing pack → failing finding, no
  exception escapes.
- **Output:** the L1 skeleton every later phase calls.

### [ ] T2.2 — Accounting packs: `trial_balance`, `journal_balanced`, `period_open`

- **Goal:** the three book-integrity packs pass on seeded books and catch planted corruption.
- **Files:** `erp/assistant/verifier/packs.py`; `erp/assistant/tests/test_verifier.py`.
- **Steps:** implement per the table; tests build fixtures the way `erp/accounting/tests` does,
  then corrupt deliberately (e.g. `update()` one journal line's debit directly, bypassing
  services) and assert the pack catches it with the right `data`.
- **Accept:** `pytest erp/assistant/tests/test_verifier.py` green — each pack has ≥1 passing and
  ≥1 catching test.
- **Output:** book integrity is checkable on demand.

### [ ] T2.3 — Document/stock packs: `stock_non_negative`, `sequence_unbroken`, `doc_totals`

- **Goal:** same bar as T2.2 for the stock/document packs.
- **Files:** same.
- **Steps:** same pattern. For `sequence_unbroken`, plant a gap by deleting a middle document via
  the ORM (test-only) and assert detection; assert the not-applicable path (scope without a
  document link) returns ok.
- **Accept:** `pytest erp/assistant/tests/test_verifier.py` green; read-only test (rollback +
  row-count diff over every pack) green.
- **Output:** all 6 packs live and proven, still wired to nothing.

## After this session

`pytest erp/assistant` green → commit (`feat(assistant): os-foundations L1 — verifier packs`) →
check boxes → rename `_done` → update `erp-status` → fresh session for FILE_03.
