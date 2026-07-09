# FILE_02 — Document detail pages rollout (header bar + ⋯ everywhere)

**Model:** Sonnet · **Est:** 30 min

## Goal

Every document/record DETAIL page publishes into the PageHeaderBar: its ONE primary action +
its ⋯ menu. Today only 4 pages have `DocumentHeader` (sales order, quotation, purchase order,
purchase request). After this session: every detail page, one pattern.

## Before You Start — read these (mandatory)

- `Docs/plan/unified-ui-plan/FILE_00_INDEX.md` (decisions 1–4, ground rules)
- `apps/web/src/app/PageActionsContext.tsx` + `components/PageHeaderBar.tsx` (built in FILE_01)
- `apps/web/src/components/DocumentHeader.tsx` — how the 4 pilot pages wire `DocMenuItem[]`
- One pilot page end-to-end: `pages/sales/OrderDetailPage.tsx`
- Enumerate detail pages: `Glob apps/web/src/pages/**/*DetailPage.tsx` + invoice/e-invoice/
  journal-entry/item/customer/supplier/ticket/lead/campaign/user detail pages (names drift —
  glob, don't trust this list)

## Tasks

1. **Migrate the 4 `DocumentHeader` pages** to publish via `useSetPageActions`; `DocumentHeader`
   keeps title/status/subtitle duties (`ModuleHeader`), loses its menu slot.
2. **Fan out to every other detail page.** Per page decide:
   - **Primary** = the one verb the page exists for (invoice → تسجيل دفعة; draft order →
     تأكيد; journal draft → ترحيل…). Status-dependent primaries follow the page's existing
     gating logic — reuse it, don't re-derive.
   - **⋯ menu**, in this order: doc verbs (تكرار / تسجيل مرتجع / إرسال فاتورة إلكترونية…) →
     طباعة (`window.print()`) → تصدير PDF (same print path) → مشاركة (placeholder `onClick`
     wired properly in FILE_04 — if FILE_04 not merged, SKIP the item, never ship a dead one) →
     destructive verb last with `danger`.
   - Existing on-page buttons for these verbs are REMOVED (the bar is now their home). Forms/
     line-editors inside the page keep their own controls.
3. **Print check:** every page with طباعة renders acceptably via the print stylesheet (`no-print`
   on the bar itself).
4. i18n: reuse existing verb keys; NEW terms → Identity System §6 first, then both locales.

## Acceptance

- Every detail page: bar shows number crumb + primary + ⋯; no page has two visible primaries;
  no page keeps an old duplicate button row.
- Verbs still work (spot-check: duplicate, print, one status verb per module) in AR and EN.
- Menu items honour status gating exactly as the old buttons did.

## Gates

Parity + `npx tsc -b` + gate03 + brand checklist on 2 pages (one sales, one accounting).
Commit → `_done` → `erp-status` → fresh session.
