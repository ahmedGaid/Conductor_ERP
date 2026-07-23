# SESSION 14 — Wizard UI 3: Progress, Report, History, Rollback
# Files: apps/web/src/pages/imports/RunStep.tsx, ImportReport.tsx, ImportHistory.tsx (new), imports.css, api/imports.ts, router, locales

> Model note: Sonnet fits this session — established patterns, no new design decisions.
> Recall `erp-frontend` for the polling/toast/undo primitives.

---

## Before You Start

1. Open how the app polls/streams live status today (grep the assistant status panel or any
   long-running UI) → same mechanism for progress; do not invent a new one.
2. Open the export/download pattern (`ExportButtons` usage) → report download reuses it.
3. Open sessions 11's `GET /api/imports/{id}` + report + history shapes.

"Do not write anything yet."

---

## Task A — RunStep (spec step 21)

Progress: stage line ("Importing rows…"), calm progress bar (token motion), rows processed /
total, speed, ETA — all as words+numbers, no dashboard theater. Pause / Resume / Cancel
buttons (permission-gated, confirm on cancel with the exact consequence sentence: "keeps the
{n} rows already imported"). Inline path (small files) skips straight to the report.

## Task B — ImportReport (spec step 22)

The report screen: created / updated / skipped / errors / created-masters counts by entity,
duration, each created-entity line deep-linking to the module list filtered to the batch
(verifiable by click — ARP mechanic 4). "Download report" → the CSV endpoint (per-row
outcomes). PDF version: ONLY if a PDF export primitive already exists (check linear-polish
FILE_10 landed) — else CSV/Excel only and note it; never a new PDF dependency here.
Rollback button with a designed confirm: what reverts, what cannot (posted docs listed), and
the result state after.

## Task C — ImportHistory (spec step 23)

`/imports` route: list of batches — file name, entity, who, when, rows, outcome words, status.
Row → report screen. Empty state designed ("Your first import…" with the new-import action).
Rollback availability shown as a plain word. This page is also where a `rolled_back` batch
shows its reversal summary.

## Task D — i18n + wiring

All keys both locales, Arabic plurals for counts. Wizard rail's "Import" step now live —
full flow: upload → map → review → run → report.

---

## Smoke Test

- [ ] 5k-row import: live progress, pause/resume from the UI works, ETA sane
- [ ] Report: counts exact, deep links land filtered, CSV downloads
- [ ] Rollback from report → confirm → history shows rolled_back with summary
- [ ] History empty state + populated state both designed; ar RTL clean
- [ ] parity + tsc + gate03 + brand-feel checklist green

---

## After This Session

```
Smoke test passed?  ← MERGE CHECKPOINT: masters importable end-to-end in the UI — THE DEMO
POINT ("spreadsheets to a running system"). Gates green, merge to main.
→ Rename with _done. Update erp-status. /compact.
→ Open FILE_15_DOCUMENT_ADAPTERS.md in a FRESH session.
```
