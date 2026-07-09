# SESSION 14 — File Intelligence: Import Pipeline
# Files: erp/assistant/services/imports.py (new), erp/assistant/api/views.py, erp/assistant/api/urls.py, apps/web/src/assistant/ImportCard.tsx (new), apps/web/src/assistant/MessageList.tsx, apps/web/src/api/assistant.ts, apps/web/src/i18n/locales/*.json, erp/assistant/tests/test_imports.py (new)

---

## Before You Start

1. Open `erp/assistant/services/files.py` (session 7) → the CSV/XLSX reading path to build on.
2. Open `erp/assistant/services/actions.py` (session 10) → the propose→confirm→execute discipline;
   import is the same discipline at N-rows scale, so reuse its endpoint shape and card states.
3. Open the create contracts for the three import targets: `erp/crm/contracts.py` (customers),
   `erp/purchasing/…` (suppliers), `erp/inventory/…` (items) — exact required fields and
   validation errors. **Import calls these row by row; never `bulk_create` around validation.**
4. Open `erp/assistant/tests/test_actions.py` → fixture style to mirror.

"Do not write anything yet."

---

## Task A — Import service

Create `erp/assistant/services/imports.py` with three phases, all actor-scoped:

```python
TARGETS = {"customers": ..., "suppliers": ..., "items": ...}  # target -> field spec + contract fn

def inspect(actor, attachment, target_hint: str | None) -> dict:
    """Sniff structure → propose mapping. Model maps headers→target fields (one complete_json
    call with headers + 5 sample rows); code validates the mapping against the field spec.
    Returns {target, columns, mapping, sample, row_count, issues}."""

def preview(actor, attachment, mapping) -> dict:
    """Dry-run all rows through parsing + contract-level checks WITHOUT writing.
    Returns {valid: n, errors: [{row, field, message}], duplicates: [...], rows: first 20 parsed}."""

def execute(actor, attachment, mapping) -> dict:
    """Import valid rows via the contract, one by one, as actor. Skip error rows.
    audit.record per batch (module="assistant", action="import", counts in after).
    Returns {created: n, skipped: n, errors: [...], links: sample EntityLinks}."""
```

Duplicate detection at preview: match on the target's natural key (customer name+phone, item SKU,
supplier tax id) — duplicates default to **skip**, listed plainly.

Rows blocked by a missing *reference* (e.g. items referencing an unknown unit of measure or
warehouse) surface through the session-12 blocker vocabulary: the preview card shows a guided
detour (create it, come back, re-preview) instead of a dead error row. Reuse
`suggestions.build_suggestion` — do not build a second suggestion path here.

## Task B — Endpoints + loop hook

- `POST /api/assistant/imports/inspect`, `/preview`, `/execute` — bodies carry `attachment_id`,
  `mapping`; same auth pattern as actions. Register in `api/urls.py`.
- Agent loop: when the user asks to import an attached tabular file, the loop responds with a new
  `{"action": "import", "attachment_id": ..., "target": ...}` option → server runs `inspect` and
  emits SSE `{"type": "import", "stage": "inspect", ...}` persisted to `meta` — same one-turn
  ending as proposals.

## Task C — ImportCard UI

Create `ImportCard.tsx` — a stepped card (states persisted in message `meta`, reload-safe like
ActionCard):

1. **Mapping** — table: file column → detected field (select to override from the field spec),
   unmapped columns marked "ignored"; `row_count` line; continue button runs `preview`.
2. **Preview** — valid/error/duplicate counts as words with icons (colour only beside the word);
   first rows in a compact table; errors listed `row N — field — reason` (human, blame-free);
   duplicates listed with "will be skipped".
3. **Confirm** — exact sentence: "Create {n} customers, skip {k}" → execute with inline progress.
4. **Report** — created/skipped counts, sample `EntityLink`s, "download full report" (CSV of
   per-row outcomes via a small endpoint or data-URI — match how exports work elsewhere:
   find `ExportButtons` usage first), follow-up chips.

## Task D — i18n + tests

Both locales: `assistant.import.*` — `mapColumns`, `ignored`, `rows`, `valid`, `errors`,
`duplicates`, `willSkip`, `confirmLine` (with count interpolation + Arabic plural forms),
`created`, `skipped`, `report`, `downloadReport`.

`erp/assistant/tests/test_imports.py`: clean CSV → inspect maps correctly (mock the model call),
preview validates, execute creates + audits; dirty CSV → bad rows skipped and reported; duplicate
rows skipped; unpermitted actor blocked at inspect.

---

## Smoke Test

- [ ] Drop a 50-row customer CSV → "import these customers" → mapping card with sensible auto-map
- [ ] Override one column mapping → preview reflects it
- [ ] Preview shows the seeded bad row + one duplicate, both skipped on execute
- [ ] Report card: correct counts, clickable created customers, downloadable row report
- [ ] Re-running the same import → all rows now duplicates → zero created (idempotent-safe)
- [ ] `pytest erp/assistant` + i18n parity + tsc + gate03 green

---

## After This Session

```
Smoke test passed?
→ Rename this file: append _done (e.g. FILE_01_CONVERSATIONS_BACKEND_done.md). A _done file is finished forever - never reopen it.
→ Type /compact in Claude Code
→ Open FILE_15_ACCEPTANCE.md and continue
```
