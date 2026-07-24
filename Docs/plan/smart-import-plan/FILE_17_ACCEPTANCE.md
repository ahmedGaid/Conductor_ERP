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
