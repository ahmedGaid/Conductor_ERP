# FILE_03 — List & report pages rollout (split pattern; retire ExportButtons row)

**Model:** Sonnet · **Est:** 30 min

## Goal

- **List pages** (orders, items, customers…): primary = "جديد …" create action; ⋯ = طباعة +
  تصدير CSV/Excel (of current filtered view) + مشاركة (FILE_04).
- **Report pages** (trial balance, GL, cash flow, VAT…): visible button = طباعة / PDF (the
  report's main job — decision 1); ⋯ = CSV + Excel + مشاركة.
- `ExportButtons` as a standalone row disappears; its download logic is reused.

## Before You Start — read these (mandatory)

- FILE_00 index (decisions 1, 8) + `PageActionsContext` / `PageHeaderBar` (FILE_01)
- `apps/web/src/components/ExportButtons.tsx` — `downloadExport(url)` + `?export=fmt&lang=` API
- The 11 `ExportButtons` call sites (grep `ExportButtons`) — each carries the report `path`
- One list page with filters: `pages/sales/OrdersPage.tsx` (FilterBar → `filtered`)

## Tasks

1. **Reports:** each call site publishes primary = PDF/print button (keeps `window.print()`),
   ⋯ = CSV + Excel calling the existing `downloadExport` with the page's `path` (query string
   preserved so the export matches on-screen filters). Delete the old `ExportButtons` row from
   the layout; delete the component once zero call sites remain (or keep as internal helper of
   the bar if reuse is cleaner — builder's call, note it).
2. **Lists:** publish primary = the page's existing "new" CTA (route or dialog — reuse).
   ⋯ export: lists have NO backend export endpoint (rule 8: don't add one). Generate CSV
   **client-side from the current filtered rows** (visible columns, localized headers, Latin
   digits, UTF-8 BOM so Arabic opens right in Excel). Excel item OMITTED on lists (no endpoint,
   no dependency for xlsx generation) — CSV opens in Excel fine; say so in the tooltip.
3. **طباعة on lists** prints the current view via print stylesheet; check table print CSS.
4. Remove any per-page ad-hoc export/print buttons found along the way — the bar is the home.
5. i18n keys; any new term → lexicon first.

## Acceptance

- All 11 report pages: PDF visible, CSV/Excel in ⋯, downloads respect current filters + lang.
- 3 spot-checked lists: client CSV opens in Excel with correct Arabic + Latin digits.
- No page anywhere still renders the old `ExportButtons` row.

## Gates

Parity + `npx tsc -b` + gate03 + brand checklist on one report page.
Commit → `_done` → `erp-status` → fresh session.

---
*Merge checkpoint boundary is after FILE_04.*
