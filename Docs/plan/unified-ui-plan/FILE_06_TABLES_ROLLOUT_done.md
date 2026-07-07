# FILE_06 — Remaining tables rollout (inventory, accounting, CRM, admin)

**Model:** Sonnet · **Est:** 30 min · **MERGE CHECKPOINT after this file**

## Goal

Every remaining list table gets the FILE_05 kit + the unified look of sales>orders (FilterBar,
keyboard nav, hover-prefetch, designed empty state). App-wide rule holds: same table anatomy on
every list.

## Before You Start — read these (mandatory)

- FILE_05's kit + recipe (as merged — not this plan's prose)
- `apps/web/src/pages/sales/OrdersPage.tsx` — still the reference anatomy
- Enumerate remaining lists (glob `pages/**` minus detail/create pages): inventory items,
  warehouses, movements, counts, batches; accounting journals, chart, fixed assets, cost
  centers, budgets; CRM pipeline, leads, tickets, campaigns; admin users; notifications
- `erp/identity/users.py` `bulk()` + its API route — the ONE ready-made bulk backend

## Tasks

1. **Fan the kit** to each list. Bulk verbs per table, existing endpoints only:
   - **Users** → suspend / activate / assign-role via the existing identity bulk endpoint
   - **Tickets / leads** → bulk assign / close IF endpoints exist (verify; else per-row loop
     via `bulkAct`, else skip verb)
   - **Journals** → bulk post drafts if a post endpoint exists per-row
   - **Everything** → تصدير المحدد CSV
   - No verb → no checkbox (FILE_05 rule).
2. **Anatomy pass** per table while there: FilterBar present where fields exist, keyboard nav
   wired, hover-prefetch on row links, empty state designed (never bare), header row consistent
   (`.num` tabular for numeric columns, `Bdi` where mixed-direction).
3. Do NOT redesign per-page columns here — that's FILE_08's job. This session is selection +
   anatomy consistency only.
4. i18n keys; parity.

## Acceptance

- Spot-check 4 tables across modules: selection keys identical, bulk verb round-trips, CSV
  export of selection correct in Arabic.
- No list page left with a visibly different table anatomy (padding, header, hover, empty
  state) from sales>orders.

## Gates

Parity + `npx tsc -b` + gate03 + brand checklist on 2 tables (one accounting, one CRM).
Commit → `_done` → `erp-status` → fresh session.

---
**Merge checkpoint:** tables program (05–06) merges here. Demo: pick any list — same keys,
same checkboxes, same bulk bar.
