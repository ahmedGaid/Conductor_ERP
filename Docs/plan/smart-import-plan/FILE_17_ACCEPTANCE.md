# SESSION 17 — Acceptance, Regression, Sign-off
# Files: none new (fixes only), DECISIONS.md, Docs/plan/arp-roadmap.md, erp-status skill

---

## Before You Start

1. Build the acceptance workbook FIRST (a real messy one, in `erp/imports/tests/fixtures/
   acceptance/`): Arabic+English mixed headers, junk title rows, cp1256 csv, every date
   format from the spec, ١٢٣ digits, "L.E"/جنيه money, PCS/قطعة units, 14%/ضريبة taxes,
   misspelled headers, in-file duplicates, near-duplicate customer names, missing masters,
   an unbalanced journal, a wrong file total, 5k+ rows in one sheet.
2. Reopen `FILE_00_INDEX.md` → verify every "Never touch" held (grep for violations).

---

## Full acceptance checklist (run in Arabic UI first, then English)

- [ ] Upload the messy workbook with ZERO preparation → correct entity detected per sheet
- [ ] Headers auto-mapped incl. Arabic, misspellings, custom names; overrides work
- [ ] Profile saved → second upload maps instantly
- [ ] Analyze stats correct ("N invoices, M new customers…")
- [ ] Creation plan proposes all missing masters; link-not-create on near-matches; one approve
- [ ] Cleaning: dates/currencies/units/taxes/phones normalized exactly per spec examples
- [ ] Duplicates flagged with candidates; no path auto-merges; undecided → skipped
- [ ] Every invalid row editable inline; revalidation instant; no return-to-Excel needed
- [ ] Auto-fix previews and applies only accepted fixes
- [ ] Preview shows real Conductor values (formatted money, resolved names) — not raw cells
- [ ] Summary + all four strategies behave; exact confirm sentence
- [ ] 100k-row generated file: background run, live progress/speed/ETA, UI never freezes
- [ ] Pause → resume; cancel keeps durable rows; kill-process → auto-recovery
- [ ] Report exact, deep links verifiable by click, CSV download; history complete
- [ ] Rollback: masters batch fully reverts; posted/referenced records honestly listed as
      cannot-revert
- [ ] Draft documents only — nothing posts without a human on the module screen
- [ ] Unpermitted user: cannot import entities they can't create; server rejects (not just UI)
- [ ] Trial-balance opening: balanced import + correcting-entry proposal path

## Regression checklist

- [ ] `pytest erp` full suite green (imports touched sales/purchasing/accounting/inventory
      services only as a CALLER — their tests prove it)
- [ ] Assistant file-import card (ai-workspace FILE_14) still works untouched
- [ ] Module create screens unaffected; audit log intact and append-only
- [ ] `node scripts/check-i18n-parity.mjs`, `npx tsc --noEmit`, `python scripts/gates/gate03.py`
      — green; brand-feel checklist on all four wizard screens

## Micro-polish pass

Empty/error/loading states on every screen reviewed; Arabic copy uses canonical lexicon terms
(Identity System §6 — add any new term THERE first, e.g. the words for "import", "rollback",
"duplicate"); toasts + undo where the app's primitives expect them; reduced-motion honored.

## Sign-off block

Record in DECISIONS.md: adapter-registry architecture; background-runner choice (FILE_10);
.xls unsupported (save-as-xlsx); rollback-as-reversal + no before-image for updates (v1);
deterministic-first AI usage; auto-fix deterministic-only v1; continuous-Excel-sync deferred;
employees/projects/assets import types deferred (STRATEGY §5).
Update `Docs/plan/arp-roadmap.md`: Phase A status → delivered by `smart-import-plan/`
(migration agent conversational layer = optional follow-up). Update `erp-status`.
State plainly what was NOT built: Excel sync, drag-drop mapping, AI autofix, PDF report
(unless primitive existed), per-document ACLs.

---

## After This Session

```
All boxes checked?  ← FINAL MERGE CHECKPOINT — full gate run, merge to main.
→ Rename with _done. Update erp-status: plan complete.
→ Tell the user: Smart Import Engine shipped; next queue item per EXECUTION_ORDER.
```
