# SESSION 13 — Wizard UI 2: Review — Preview Grid, Inline Fix, Auto-Fix, Summary
# Files: apps/web/src/pages/imports/ReviewStep.tsx, PreviewGrid.tsx, DuplicateReview.tsx, CreationPlan.tsx, SummaryPanel.tsx (new), imports.css, api/imports.ts, locales

> Recall `conductor-brand` + `erp-frontend`. This screen is the product's trust moment —
> the user decides here whether Conductor understood their business. Craft accordingly.

---

## Before You Start

1. Open the app's existing table/grid component (find the largest list screen) → reuse its
   virtualized/paged table primitives. NO new grid dependency.
2. Open `api/imports.ts` (session 12) + the rows/PATCH/autofix/creation-plan endpoints
   (session 11 shapes).
3. If ai-workspace FILE_12 (guided detours) landed: open its suggestion-chip component —
   missing_ref blockers reuse it.

"Do not write anything yet."

---

## Task A — ReviewStep layout

Filter tabs by row status: All / Valid / Errors / Duplicates / Skipped — counts in the tab
labels (words, not badges-only). Paged grid below (server pagination via `?status=&page=`).
1M-row safety: the grid never holds more than a page; counts come from stats.

## Task B — PreviewGrid + inline correction (spec steps 15, 17)

Rows show NORMALIZED values (what Conductor will write — "not raw Excel"). Issue cells:
underline + issue message on focus (human, blame-free, from i18n keys). Click → inline edit
(input matching field kind; date/money formatted at the edge per `lib/money.ts`) → PATCH →
row revalidates instantly → status flips live (settled motion, no bounce). `missing_ref`
issues render an actionable chip: "Customer 'Ahmed Trading' doesn't exist — add it in the
creation plan below" (deep-scroll link), never a dead error.

## Task C — DuplicateReview

Grouped list: file row vs candidate(s) side by side, similarity as words ("very likely the
same"), actions Merge / Create new / Ignore per row + "apply to all like this". Undecided
count surfaces in the summary as "will be skipped". Never a bulk-merge-all button.

## Task D — CreationPlan (spec step 7 UI)

The masters plan as a checked list grouped by entity ("35 customers", expandable to names,
each editable, untickable; link-to-existing entries shown with the existing record). One
approve action; permission-blocked groups shown with the actionable message.

## Task E — Auto Fix + SummaryPanel (spec steps 16, 18–19)

"Auto-fix" button → modal listing every proposed change (`row · field · from → to`) →
apply-all or per-row untick. Nothing applies without the confirm.
SummaryPanel (sticky end-of-flow): create / update / skip / errors / duplicates / new masters /
estimated duration + strategy selector (the four strategies, radio, one-line explanation each)
+ atomicity toggle for small batches + "continue after errors" toggle. Import button states
the exact sentence: "Create 520 invoices, update 0, skip 14".

---

## Smoke Test

- [ ] Error row edited inline → flips valid without page reload; blocker chip scrolls to plan
- [ ] Duplicate decisions stick (reload page → still there — server-persisted)
- [ ] Auto-fix previews then applies only what was accepted
- [ ] Summary numbers always reconcile with tab counts; strategy changes update the sentence
- [ ] ar RTL first-class; parity + tsc + gate03 + brand-feel checklist green

---

## After This Session

```
Smoke test passed?
→ Rename with _done. Update erp-status. /compact.
→ Open FILE_14_RUN_REPORT_HISTORY_UI.md in a FRESH session.
```
