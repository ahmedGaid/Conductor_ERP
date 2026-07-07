# FILE_05 — Table kit: shared selection column + bulk bar; sales/purchasing fan-out

**Model:** Opus · **Est:** 30 min

## Goal

The sales>orders table treatment becomes a reusable kit, then lands on every sales + purchasing
list. Kit = checkbox column (tri-state header, Shift-range rows) + bulk action bar + the two
hooks that already exist (`useListKeyboardNav`, `useRowSelection`).

## Before You Start — read these (mandatory)

- `apps/web/src/pages/sales/OrdersPage.tsx` — the reference: hooks wiring, `bulkAct` optimistic
  pass, checkbox cells, bulk bar markup
- `apps/web/src/hooks/useRowSelection.ts` + `hooks/useListKeyboardNav.ts` — contracts; NEVER
  change their key semantics
- The existing bulk bar component (grep `BulkActionBar`) — reuse; extract only if it's inline
- The 6 current `useRowSelection` call sites — what's already consistent

## Tasks

1. **Extract the kit** (judgment call — smallest thing that ends copy-drift):
   - `components/SelectionColumn.tsx` (or a documented cell pair): header checkbox
     (checked/indeterminate from `allSelected`/`someSelected`, click → `toggleAll`) + row
     checkbox (click/Shift-click → `toggle(i, shiftKey)`), a11y labels, `no-print`.
   - Bulk bar: shared component if not already; shows count "تم تحديد N", verbs, Esc hint.
   - A short recipe comment block (or `components/README` section) so FILE_06 fan-out is
     mechanical.
2. **Fan out — sales + purchasing lists** missing selection (glob the list pages; likely
   quotations, customers, invoices, e-invoices, suppliers, requests…). Per table wire kit +
   bulk verbs that map to EXISTING endpoints:
   - Draft docs → bulk approve/confirm (mirror per-row gating exactly, like `approvable`/
     `confirmable` on orders)
   - Any table → "تصدير المحدد CSV" (client-side, reuse FILE_03's CSV helper on
     `selectedItems`)
   - No qualifying verb for a table → NO checkbox there (dead selection UI is worse than none;
     keyboard nav still lands).
3. Bulk passes use the `bulkAct` optimistic pattern verbatim (predict → fire all → reconcile →
   clear → one toast with the count).
4. i18n keys for new verbs; lexicon first for new terms.

## Acceptance

- Each new table: x / Shift-click / ⌘A / Esc behave exactly like sales>orders; bulk verb
  updates rows optimistically; failure rolls back with error toast.
- Checkbox column aligns and prints clean (hidden in print).
- Tables without verbs got no checkbox — intentional, noted in commit.

## Gates

Parity + `npx tsc -b` + gate03 + brand checklist on one table.
Commit → `_done` → `erp-status` → fresh session.
