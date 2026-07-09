# FILE_08 — Meta columns rollout (rings, chips, bars in the tables)

**Model:** Sonnet · **Est:** 30 min

## Goal

FILE_07 primitives land in the live tables. Calm density: each table gets the columns its work
needs — not all columns everywhere.

## Before You Start — read these (mandatory)

- FILE_07 components + `lib/lifecycle.ts` (as merged)
- FILE_00 decisions 5–7
- Each target page's row shape in `api/*.ts` — which fields actually exist (owner? due date?
  priority?). NO fake data, no placeholder columns.

## Tasks

1. **Column map** (verify fields at build; drop a column if the API lacks the data):
   - Sales orders / purchase orders / quotations / requests → StatusRing+word, OwnerChip
     (salesperson/created_by), fulfilment % on sales orders IF delivered qty is in the list
     payload (else skip — do not widen the API here)
   - Invoices (sales, purchase, e-invoice) → StatusRing+word, DueMarker, OwnerChip
   - Journals → StatusRing+word (draft/posted), OwnerChip
   - Tickets / leads → PriorityBar+word, OwnerChip, StatusRing where lifecycle-like
   - Purchase requests → PriorityBar ONLY if the field exists (FILE_00 decision 7)
2. Replace plain status text cells with StatusRing+word (the word stays — the ring joins it).
3. Column headers localized; FilterBar/saved-views field lists updated where these columns are
   filterable (owner, priority, due).
4. Print: rings/chips print acceptably or hide via `no-print` (builder judgment — table must
   stay readable on paper either way).
5. Density check per table: row height unchanged, no horizontal scroll at common widths, RTL
   alignment right.

## Acceptance

- Orders, invoices, tickets side-by-side with the Linear reference: same at-a-glance read
  (where is it, whose is it, how urgent) with Conductor's quiet palette.
- No column shows without real data behind it; empty cells are designed (— placeholder), not
  blank holes.
- AR + EN, light + dark spot-checks; digits Latin, tabular.

## Gates

Parity + `npx tsc -b` + gate03 + brand checklist on 2 tables.
Commit → `_done` → `erp-status` → fresh session.
