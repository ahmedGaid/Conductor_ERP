# Conductor ARP — Smart Import Engine — Master Index

## Project Goal

Build an enterprise-grade data-migration engine: a user uploads their existing Excel/CSV files
exactly as they have them, and Conductor detects what the file is, recognizes the columns
(Arabic/English/mixed), cleans the data, finds duplicates, creates missing master records,
validates every row, lets the user fix errors inline, previews real Conductor documents, and
imports safely — transactional, resumable, rollback-able, with a full report and history.

This realizes **roadmap Phase A** (migration agent / "Excel-chaos onboarding") as a standalone
product surface. The conversational migration agent later becomes a thin layer over this engine.
Unbeatable claim it buys: **"From spreadsheets to a running system in one afternoon."**

> **Staleness note (deliberate):** this plan was written 2026-07-04, ahead of its queue turn.
> Code will drift before these sessions run. Snippets here are interface-level BY DESIGN; the
> EXECUTION_ORDER drift rule applies with full force — the "Before You Start" reads are
> mandatory, intent wins over literal snippet, note drift in the commit.

## Architecture decisions (locked at planning; re-confirm only if code contradicts)

1. **New Django app `erp/imports`.** The core engine is module-agnostic (spec step 27): parsing,
   detection, mapping, cleaning, validation, execution, history live here. Zero module-specific
   logic in the core.
2. **Adapter registry.** Each business module registers an `ImportAdapter`: entity name, field
   spec (required/optional/types), reference lookups, natural key, validation rules, default
   values, and a `write(actor, row) -> record` that calls the module's EXISTING service
   write-path. Import never invents a second write-path and never `bulk_create`s around
   validation.
3. **AI proposes, code disposes.** Dataset detection, header mapping, and auto-fix suggestions
   use the existing LLM client (`erp/assistant/services/llm.py`, `complete_json`); every AI
   output is validated against the adapter field spec before use. Deterministic passes
   (synonyms, fuzzy match, normalizers) run FIRST; the model is the fallback, not the engine.
4. **The six ARP mechanics hold** (STRATEGY §3): engine runs as the actor (RBAC + data scope by
   construction), all writes human-confirmed (analyze → preview → confirm → execute), audit on
   every batch, numbers verifiable by click, blockers actionable, interruptions resume.
5. **No new dependencies by default.** xlsx via the already-used reader path
   (`erp/assistant/services/files.py`), csv via stdlib. Legacy `.xls` needs a new package →
   NOT in baseline; the upload UI says "save as .xlsx" for .xls files. Levenshtein = small
   pure-Python helper. Any change to this = written DECISIONS entry first (team rule 7).
6. **Background processing is a gated decision.** No worker infra exists in the repo. FILE_10
   STOPS for a DECISIONS entry (management-command runner vs real worker — same fork as
   roadmap Phase C's scheduler). Baseline recommendation: DB-backed job rows + management
   command; chunked commits make any runner resumable.
7. **Rollback = reversal, not deletion.** ImportBatch records every created/updated record.
   Master records created by the batch and still unreferenced → delete via module write-path.
   Posted documents → reverse by the module's own reversal/contra mechanism, never raw deletes.
8. **Money**: integer minor units on the wire, format/parse only at the edge (`lib/money.ts`).
9. **Arabic-first**: header synonyms, date formats (incl. Arabic-Indic digits ١/٢/٢٠٢٦),
   currency words (جنيه/L.E/LE), unit words (قطعة), tax words (ضريبة) are first-class in the
   normalizers — not an afterthought layer.

## Out of scope (STRATEGY §5 — do not let the spec pull these in)

- **Employees, Projects, Assets import types** — those modules don't exist and are refused
  scope until the money loop is unbeatable. The registry makes adding them later trivial.
- **Continuous Excel sync (spec step 24)** — future plan of its own, not a session here.
- Per-document ACLs on import history; collaborative multi-user editing of one preview.

## Session Map

| # | File | What gets built | Model | Est. |
|---|---|---|---|---|
| 01 | FILE_01_MODELS_AND_REGISTRY.md | `erp/imports` app: ImportBatch/ImportRow/ImportProfile models + adapter protocol + registry | Opus | 25 min |
| 02 | FILE_02_FILE_READER.md | Streaming xlsx/csv reader, header + sample extraction, encoding repair | Sonnet | 20 min |
| 03 | FILE_03_DETECT_AND_MAP.md | Dataset detection + header recognition (ar/en synonyms, fuzzy, AI fallback) | Opus | 30 min |
| 04 | FILE_04_NORMALIZERS.md | Cleaning: dates, currencies, units, taxes, phones, emails, tax-ids, Arabic text | Sonnet | 30 min |
| 05 | FILE_05_MASTER_ADAPTERS.md | Adapters: customers, suppliers, items, categories, warehouses, UoM, price lists, contacts | Sonnet | 30 min |
| 06 | FILE_06_ANALYZE_VALIDATE.md | Existing-data diff stats + row validation engine + missing-reference detection | Opus | 25 min |
| 07 | FILE_07_DUPLICATES.md | Fuzzy duplicate detection + merge/create/ignore decisions (never auto-merge) | Opus | 25 min |
| 08 | FILE_08_AUTO_MASTERS.md | Auto-create missing masters with configurable defaults, confirm-first | Sonnet | 20 min |
| 09 | FILE_09_EXECUTION_ENGINE.md | Strategies (create/update/upsert/skip), chunked transactions, resume, rollback, audit | Opus | 30 min |
| 10 | FILE_10_BACKGROUND_RUNNER.md | **DECISIONS gate** → background jobs, progress, pause/resume/cancel | Opus | 25 min |
| 11 | FILE_11_IMPORT_API.md | REST endpoints: upload/analyze/mapping/preview/execute/batches/profiles + permissions | Sonnet | 25 min |
| 12 | FILE_12_WIZARD_UPLOAD_MAP_UI.md | Wizard steps 1–2: upload → detected type → mapping table → save profile | Opus | 30 min |
| 13 | FILE_13_PREVIEW_FIX_UI.md | Preview grid, inline error editing, auto-fix, duplicate review, summary + strategy | Opus | 30 min |
| 14 | FILE_14_RUN_REPORT_HISTORY_UI.md | Progress screen, import report + download, history page, rollback UI | Sonnet | 30 min |
| 15 | FILE_15_DOCUMENT_ADAPTERS.md | Multi-row documents: quotations, sales orders, sales/purchase invoices, purchase orders | Opus | 30 min |
| 16 | FILE_16_FINANCE_ADAPTERS.md | Journal entries (balanced), payments/receipts, inventory opening balance + transactions | Opus | 30 min |
| 17 | FILE_17_ACCEPTANCE.md | Full acceptance + regression + gates + DECISIONS entries + sign-off | Opus | 30 min |

Merge checkpoints (`---` boundaries): after **04** (parsing core), after **10** (backend engine
complete), after **14** (masters importable end-to-end through the UI — the demo point), after
**17** (documents + finance + acceptance).

## Affected files (exhaustive at planning time; verify at build time)

Backend — new app `erp/imports/`:
- `apps.py`, `models.py`, `migrations/`, `registry.py`, `readers.py`, `detect.py`,
  `mapping.py`, `normalize.py`, `validate.py`, `duplicates.py`, `engine.py`, `runner.py`,
  `adapters/` (one file per module), `api/views.py`, `api/urls.py`, `tests/`
- `config/settings/base.py` (INSTALLED_APPS + `IMPORTS_*` settings), root `api/urls.py` include
- READ-ONLY use of: module `services/` write-paths, `erp/audit/services`, `erp/identity` RBAC,
  `erp/assistant/services/llm.py`, `erp/assistant/services/files.py`

Frontend (`apps/web/src/`):
- `pages/imports/` (new: wizard, history, report pages) + routes + nav entry
- `api/imports.ts` (new), `i18n/locales/ar.json` + `en.json` (`imports.*` keys)
- module CSS for the wizard (tokens only, logical CSS)

## Never touch

- `erp/audit/models.py` — append-only; write only via `erp.audit.services.record(...)`
- Existing module service write-path signatures — adapters CALL them, never modify them
- `apps/web/src/styles/tokens.css` — no new raw hex
- The assistant event protocol and existing assistant endpoints
- **No new npm or pip dependencies without a written DECISIONS entry first.**

## Ground Rules (every session)

1. **Read before write** — the named reads, literally; code drift → intent wins, note it.
2. **Additive** — nothing existing breaks; every module keeps working untouched.
3. **Engine runs as the actor** — permissions and data scope by construction, server-side.
4. **Never trust the file** — every row re-validated server-side at execute, not just preview.
5. **Frontend hard rules** — tokens only, logical CSS, ar/en parity, designed
   empty/error/loading states, monochrome chrome, settled motion, human blame-free errors.
6. **Gates before "done"** — `apps/web`: `node scripts/check-i18n-parity.mjs` +
   `npx tsc --noEmit`; repo root: `python scripts/gates/gate03.py`; backend:
   `pytest erp/imports`. UI sessions also run the `conductor-brand` brand-feel checklist.
7. **Done means renamed** — green + committed → rename the file with `_done`.

## How to use this plan

1. New Claude Code session → load this index + the next `FILE_NN` (lowest number without `_done`).
2. Model check (Model column above) → suggest `/model` switch in one line if Sonnet fits.
3. Do the reads → tasks → smoke test → gates → commit → rename `_done` → update `erp-status`
   → tell the user to start a fresh session. One file = one session.

## After all sessions complete

- FILE_17 acceptance in both languages (ar RTL first) on a realistic messy workbook.
- DECISIONS.md entries: adapter registry architecture, background runner choice, .xls posture,
  rollback-as-reversal, AI-proposes-code-disposes.
- Update `Docs/plan/arp-roadmap.md` Phase A status; update the `erp-status` skill; the
  migration-agent conversational layer (assistant ↔ this engine) is scoped THEN as a short
  follow-up plan if still wanted.

*Generated by ag-plan skill. Do not edit this index manually.*
