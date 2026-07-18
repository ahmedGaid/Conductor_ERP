# SESSION 17 — List UX: Inline Editing + Peek Audit
# Files: apps/web/src (unified table kit + module PATCH clients), i18n locales

Twenty reference: click a cell, type, done — no form round-trip for small corrections; and
records preview in a side panel without leaving the list. Perceived speed is real speed.

---

## Before You Start

1. **Peek overlap audit (mandatory):** linear-polish shipped "peek". Find it, list which pages
   have it and which don't. This session's peek work = closing THAT gap table only. If coverage
   is already complete → peek scope is zero; say so in the commit.
2. Open the unified table kit cell rendering → where an edit affordance can live.
3. Per candidate column, find the EXISTING service-contract PATCH path (`erp/<module>/api`) —
   inline edit calls what exists; a column with no service update path is NOT a candidate
   (that's a STOP, not a workaround).
4. Open the optimistic-update + toast-undo primitives (they exist — erp-frontend skill).

"Do not write anything yet."

---

## Task A — Inline edit on safe columns

Candidates (verify each against its service path): draft-document line qty/note, lead
stage/owner, item reorder level, customer contact fields. NEVER inline-editable: anything on a
POSTED document, money amounts on confirmed docs, permission-bearing fields. Interaction:
click (or Enter on focused cell) → input in place matching the field type → esc cancels /
enter+blur saves → optimistic update + toast with undo → server error returns the old value
with a human message. Keyboard path complete.

## Task B — Cell affordance craft

Editable cells get a quiet hover/focus affordance (border token, no color flood); a read-only
cell gives a one-line reason on attempted edit ("مستند مرحَّل لا يُعدَّل") — designed, not
silent failure.

## Task C — Peek gap closure

From the audit table in reads: wire the missing pages to the existing peek pattern (record
opens in side panel from the list; full page stays one click away). No new pattern invented.

---

## Smoke Test

- [ ] Edit a draft order line qty inline → total updates optimistically → undo restores
- [ ] Posted invoice cell refuses edit with the designed reason
- [ ] Server-rejected edit rolls back with human ar/en error
- [ ] Peek works on every list page in the audit table (or table shows pre-existing full coverage)
- [ ] Keyboard-only: navigate cells, edit, cancel, save; RTL correct
- [ ] parity + tsc + gate03 green; brand-feel checklist passed

---

## After This Session

```
Smoke test passed?
→ Rename with _done. Update erp-status. /compact.
→ Open FILE_18_KANBAN_PIPELINE.md in a FRESH session.
```
