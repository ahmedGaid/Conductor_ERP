# SESSION 17 — Acceptance, Regression, Sign-off
# Files: none new (fixes only), DECISIONS.md, Docs/plan/arp-roadmap.md, erp-status skill
#
# STATUS (2026-07-24, partial — NOT renamed _done, genuinely incomplete): the mechanical slice
# only. Built the acceptance workbook ("Before You Start" Task 1) as a real, re-runnable generator
# — `erp/imports/tests/fixtures/acceptance/build_fixtures.py` — producing customers_messy.csv
# (junk rows, mixed ar/en misspelled headers, in-file + fuzzy duplicates, Arabic-Indic-digit +
# L.E/جنيه money), sales_invoices_messy.csv (5,200+ rows: every CSV-representable `parse_date`
# format, an inconsistent-document, a total_mismatch, two different missing-ref entities, an
# orphan blank-key line), sales_invoices_cp1256.csv (Windows-1256, Arabic headers/content),
# journal_entries_unbalanced.csv (one balanced + one deliberately unbalanced entry), and
# customers_100k.csv (100k clean rows, the volume/perf fixture — separate concern from the
# messy-data fixtures). New `erp/imports/tests/test_acceptance.py` (5 tests) drives each fixture
# through the REAL upload(no-op here)->analyze->validate->duplicates->execute pipeline (mapping
# supplied explicitly rather than re-exercising the live AI-backed auto-matcher `test_api.py`
# already flags as slow/non-deterministic — that path has its own dedicated, mocked coverage in
# `test_mapping.py`) and asserts the checklist's data-quality bullets: entity/date/money/duplicate
# handling, creation-plan candidates across three different ref entities, cp1256 decoding, the
# unbalanced-journal guard. All 5 pass reliably in isolation and in combination with every other
# FILE_15-era imports test file (87 total). Two real, fixed bugs found ALONG THE WAY (not
# production bugs — my own fixture/test mistakes, kept here as a lesson): (1) `ImportBatch.mapping`
# is `{field: header}`, not `{header: field}` — got the direction backwards on the first pass;
# (2) a merged-cell continuation row must leave the group-by column BLANK, not repeat it — repeating
# it reads as an in-file duplicate of the header row's own key, not a second line of one document.
# **Known pre-existing flakiness, NOT this session's bug** (matches the exact class already logged
# in `erp-status`/FILE_15's own closing note): running the acceptance suite back-to-back with many
# other DB-heavy test files for 2+ minutes straight occasionally hits a real Postgres connection
# drop ("server closed the connection unexpectedly") mid-bulk-insert — a resource/contention issue
# on this dev box (shared with the live public demo's `serve_waitress.py`), not a logic defect;
# every test here has been proven green in isolation.
#
# **Real gap found + scoped 2026-07-25 (this session, resumed acceptance pass):** the wizard
# reads only the FIRST sheet of an uploaded .xlsx (openpyxl's `wb.active`) — a real multi-sheet
# workbook (Customers/SalesInvoices/PurchaseInvoices/JournalEntries, as in
# `acceptance_workbook.xlsx`) silently drops sheets 2-4. `erp/imports/readers.py`'s `list_sheets`
# and the upload response's `sheets` field already carry every sheet name + row count, but NO
# frontend code in `apps/web/src/pages/imports/` ever reads that field — no picker, no cycling.
# Checked every FILE_00-16 plan doc: "sheet"/"workbook" scope language appears nowhere except this
# one checklist line — multi-sheet-per-upload was never actually built, not a regression. Decided
# (founder call, this session): v1 stays single-sheet-per-upload by design, matching everything
# else already shipped; the checklist line above is reworded to match. Multi-sheet cycling is a
# real, scoped follow-up (backend groundwork already exists) — not a blocker for this sign-off.
#
# **Deliberately NOT done this session — needs a dedicated, supervised pass** (flagged BEFORE
# starting, per the plan's own framing of this file as the capstone acceptance/sign-off session):
# the two-language (Arabic-first, then English) MANUAL UI walkthrough of the full checklist below
# (profile save/reuse, autofix apply, all four import strategies, the 100k-row background runner's
# live progress/pause/resume/**kill-process recovery**, report deep-links, rollback, an unpermitted
# user's server-side rejection, trial-balance opening's correction-approval flow); the full
# `pytest erp` regression suite (blocked today by the same pre-existing DB/demo-contention issue —
# needs a quiet checkout to confirm, same as `gate:all` in the FILE_15 closing note); the
# `Docs/RUNBOOK.md`/brand-feel/micro-polish passes; the DECISIONS.md sign-off block; the
# `arp-roadmap.md` Phase-A-delivered update; and the FINAL MERGE CHECKPOINT to `main` (a
# consequential, irreversible action that needs the founder's explicit go-ahead regardless of
# session boundaries). Whoever opens this file next: start from the "Full acceptance checklist"
# section below with the fixtures already built — no need to redo Before You Start.

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

- [x] Upload the messy workbook with ZERO preparation → correct entity detected for the sheet
      that loads (v1 is single-sheet-per-upload — see STATUS note above; a multi-sheet workbook
      needs one re-upload per sheet, each landing correctly)
- [x] Headers auto-mapped incl. Arabic, misspellings, custom names; overrides work
- [x] Profile saved → second upload maps instantly
- [x] Analyze stats correct ("N invoices, M new customers…")
- [x] Creation plan proposes all missing masters; link-not-create on near-matches; one approve
- [x] Cleaning: dates/currencies/units/taxes/phones normalized exactly per spec examples
- [x] Duplicates flagged with candidates; no path auto-merges; undecided → skipped
- [x] Every invalid row editable inline; revalidation instant; no return-to-Excel needed
- [x] Auto-fix previews and applies only accepted fixes
- [x] Preview shows real Conductor values (formatted money, resolved names) — not raw cells
- [x] Summary + all four strategies behave; exact confirm sentence
- [x] 100k-row generated file: background run, live progress/speed/ETA, UI never freezes
      (found + fixed 3 real scaling bugs to get here — see DECISIONS.md sign-off entry)
- [x] Pause → resume; cancel keeps durable rows; kill-process → auto-recovery
- [x] Report exact, deep links verifiable by click, CSV download; history complete
- [x] Rollback: masters batch fully reverts; posted/referenced records honestly listed as
      cannot-revert
- [x] Draft documents only — nothing posts without a human on the module screen
- [x] Unpermitted user: cannot import entities they can't create; server rejects (not just UI)
- [x] Trial-balance opening: balanced import + correcting-entry proposal path (found the
      approval path didn't exist anywhere in the API/UI — built it; see DECISIONS.md)

## Regression checklist

- [x] `pytest erp` full suite green (imports touched sales/purchasing/accounting/inventory
      services only as a CALLER — their tests prove it) — 1640 passed, 1 skipped
- [x] Assistant file-import card (ai-workspace FILE_14) still works untouched
- [x] Module create screens unaffected; audit log intact and append-only
- [x] `node scripts/check-i18n-parity.mjs`, `npx tsc --noEmit`, `python scripts/gates/gate03.py`
      — green; brand-feel checklist on all four wizard screens

## Micro-polish pass

Empty/error/loading states on every screen reviewed; Arabic copy uses canonical lexicon terms
(Identity System §6 — add any new term THERE first, e.g. the words for "import", "rollback",
"duplicate"); toasts + undo where the app's primitives expect them; reduced-motion honored.
Done — reduced-motion already covered by a global CSS guard (verified, not per-file); new Arabic
strings checked against the established "ميزان المراجعة" (trial balance) term already used
elsewhere; 4 unlocalized issue-message keys found + fixed along the way (see DECISIONS.md).

## Sign-off block

Recorded in DECISIONS.md ("Smart Import Engine — FILE_17 acceptance sign-off", 2026-07-26):
adapter-registry architecture; background-runner choice (FILE_10); .xls unsupported
(save-as-xlsx); rollback-as-reversal + no before-image for updates (v1); deterministic-first AI
usage; auto-fix deterministic-only v1; continuous-Excel-sync deferred; employees/projects/assets
import types deferred (STRATEGY §5); what was NOT built (Excel sync, drag-drop mapping, AI
autofix, PDF report, per-document ACLs).
`Docs/plan/arp-roadmap.md` updated: Phase A status → delivered. `erp-status` updated.

---

## After This Session

**All boxes checked, 2026-07-26.** Full gate run green, full `pytest erp` green. Renamed `_done`.
`erp-status` updated: plan complete, Phase A closed.
**FINAL MERGE CHECKPOINT NOT TAKEN** — needs the founder's explicit go-ahead per this file's own
rule (a consequential, irreversible action, independent of session/checklist completeness).
