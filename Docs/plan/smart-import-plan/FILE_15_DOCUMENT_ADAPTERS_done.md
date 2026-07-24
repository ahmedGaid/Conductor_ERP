# SESSION 15 — Document Adapters: Sales & Purchasing
# Files: erp/imports/adapters/sales.py, adapters/purchasing.py (extend), erp/imports/engine.py (group support), erp/imports/tests/test_document_adapters.py (new)
#
# STATUS: Task A (group engine) + Task B (all 5 adapters) + Task C (tests) done, pytest green.
# Not renamed _done — the smoke test's "preview UI shows grouped document" bullet is apps/web
# (Agent A territory) and unverified by this (backend-only) session. sales_orders/purchase_orders
# reuse the sales_invoices/purchase_invoices draft-create path (no separate order/invoice model
# exists), distinguished only by a notes tag prefix (import-so:/import-po: vs import:) so natural-key
# matching never collides on the shared table.
#
# CORRECTION (2026-07-23, impeccable shape session): the "session 13 grid renders group headers"
# claim above is FALSE — checked PreviewGrid.tsx directly, it has zero group logic, purely flat
# per-row rendering. Bigger finding: `_build_groups`/group-level issues (total_mismatch,
# inconsistent_document, missing_group_key) only run in engine.py at EXECUTE time — analyze/
# validate.py never touches group_key, so the pre-execution Review step cannot show documents
# grouped or preview a total mismatch today, no matter what the frontend does. This is not a
# CSS fix. Founder confirmed (via impeccable shape) the full fix: CONFIRMED SCOPE below is the
# brief for whoever opens this file next.
#
# STATUS 2 (2026-07-23/24, CONFIRMED SCOPE session): DONE, renamed _done. Board note — this file's
# remaining work (both halves) was board-assigned to Agent B (PARALLEL_PLAN row B22, ERP-B
# worktree, not started); founder explicitly reassigned it to A for this session (row flipped to
# `doing(A)`, note left in the row). Backend: new `erp/imports/grouping.py` — one shared module
# (`build_groups`, `header_conflict_issue`, `forward_filled_header`, `compute_subtotal_minor`,
# `total_mismatch_issue`, `annotate_groups`) used by BOTH `validate.py` (new preview pass, wired
# into `validate_batch`+`revalidate_rows`) and `engine.py` (execute path refactored to call the same
# functions instead of its own private copies) — preview and execute can't disagree by construction.
# All 5 adapters' `write()` methods refactored onto the shared `total_mismatch_issue` comparison
# (execute-time behavior unchanged, verified byte-identical issue shape against existing tests).
# `ImportRow.group_meta` new JSONField (migration 0002) carries group_id/is_first/header/
# computed_total_minor/line_count per row — empty `{}` for every master adapter, zero regression.
# API: `_batch_row` exposes `group_by`/`header_fields`; `_row_row` exposes `group_meta`;
# `BatchRowsView` paginates by whole DOCUMENT (never splits one across a page) for the unfiltered
# "all" tab on a grouped entity — filtered tabs (valid/error/duplicate/skipped) keep the original
# row-based paging, tab counts unchanged in meaning, per spec. Frontend: `PreviewGrid.tsx` renders
# header fields once in a tinted full-width group-header row (clean/warning/error/orphan tones,
# reusing the existing status vocabulary) instead of repeating them as mostly-blank per-line
# columns; `DuplicateReview.tsx` shows the document's header/line-count/total context alongside its
# one natural-key row (document adapters can only ever surface ONE row per document in the
# duplicate tab — confirmed by reading `duplicates.find_candidates`/`adapter.exists`, so no separate
# group-aware layout was needed there). New i18n keys `imports.issues.{missingGroupKey,
# inconsistentDocument,totalMismatch}` (previously referenced by the backend but never actually
# translated — a real pre-existing gap, fixed) + `imports.review.group.lines` (ar full 6-form
# plural). Also found+fixed a related gap in `analyze.py`'s early `_flag_in_file_duplicate` pass: it
# only checked ``adapter.natural_key`` against ALREADY-normalized rows, blind to `group_by` —
# a document adapter's natural_key IS its group_by field, so a file that repeats the doc/entry
# number on every one of a document's lines (a valid, common real-world shape, distinct from the
# blank-continuation "merged-cell" shape every other fixture here used) had every line after the
# first misflagged `duplicate_in_file`, which would make any real multi-line document unexecutable
# without a bogus duplicate decision. Fixed: `_flag_in_file_duplicate` is now skipped entirely for
# `adapter.group_by` entities — `grouping.py`'s own header-conflict/missing-key checks are the
# document-shaped equivalent. Regression test added: `test_validate.py::
# test_analyze_does_not_flag_a_documents_own_repeated_key_as_duplicate_in_file`.
# Tests: `erp/imports/tests/test_grouping_preview.py` (new, 10 tests) — preview issues
# match execute issues exactly, idempotent re-annotation, group-aware pagination API-level, pure
# total estimate matches the real posted `subtotal_minor`, ungrouped entities untouched. Gates:
# i18n parity 2643 keys, `tsc -b` clean, `gate03` exit0, targeted `pytest` (test_grouping_preview +
# test_document_adapters + test_engine + test_validate + test_api + test_finance_adapters) 77
# passed twice. **Full-directory `pytest erp/imports` and `gate:all` could NOT complete — a
# pre-existing, unrelated environment issue** (the live public demo's `serve_waitress.py`
# process, PIDs found holding :8000, contends for the shared `test_erp` DB exactly as a prior
# session already documented; confirmed NOT caused by this diff — reproduces identically with
# `test_grouping_preview.py` excluded, and gate 04's failure is inside `erp/workflow` tests,
# untouched by this file). Live-verified in a REAL running browser (isolated Django :8010 + a
# throwaway Vite instance on :5180, proxying to it — the shared :8000/:5173 dev servers were never
# touched): all four group states rendered correctly in Arabic/RTL with real seeded data — orphan
# (red, "no document to attach"), total_mismatch (orange, both totals shown, file total struck
# through), inconsistent_document (red, names the disagreeing field), and clean (green, computed
# total only). English keys verified via the i18n parity gate + language-agnostic component code,
# not pixel-verified live (no time spent forcing the server-backed language preference in this
# session — low risk, flag if a follow-up wants the EN screenshot too). Verification DB rows and
# throwaway files/servers all cleaned up after.

## CONFIRMED SCOPE — pre-execution document-group preview (impeccable shape, 2026-07-23)

**Problem:** accountant reviewing a multi-line import (e.g. 3 invoices/7 lines) sees 7 flat,
seemingly-disconnected rows before Import — no group identity, no computed-vs-file total, no
group-level issue — because those only exist post-execute. Must catch bad data before commit,
not after (matches the product's "see tomorrow's books before you post them" trust bar).

**Backend:**
- Lift the grouping key + header-consistency + total-comparison logic out of `engine.py` into
  one shared, adapter-agnostic helper (`registry.py` or new module). Both the analyze/validate
  path and the execute path call THIS ONE COPY — do not fork a second implementation.
- Analyze/validate gains a grouping pass for any `group_by`-set entity, computing the same
  issues execute already produces (`total_mismatch`, `inconsistent_document`,
  `missing_group_key`) so they're visible pre-execution.
- API exposes, per row, ONLY for grouped entities: group key, "is this row a group's first
  line" flag, and a forward-filled header snapshot (customer/date/currency etc.) — so a row
  can render a correct group header even when it lands at the top of a paginated page without
  seeing its group's earlier rows. Ungrouped entities (5 master adapters, already `_done`):
  zero change, zero regression risk.

**Frontend (`PreviewGrid.tsx` / `ReviewStep.tsx` / `DuplicateReview.tsx`):**
- Group header row: full-width tinted `<tr>` before each group's lines — doc number, party,
  date/currency, line count, computed total (+ file total struck through beside it only when
  mismatched), one worst-of-group status chip reusing the existing `STATUS_ICON`/status-color
  vocabulary. Line rows unchanged (own status dot, per-cell issue underline); header-only field
  columns dim/blank on line rows (not that row's data).
- No collapse/accordion-by-default — lines stay visible always; hiding them defeats the reason
  this exists (accountants are here to catch line-level issues).
- Pagination for grouped entities becomes group-aware: a page holds whole documents, never
  splits one across the page boundary. Ungrouped entities keep today's flat row-based paging.
- Tab counts (`all/valid/error/duplicate/skipped`) stay row-based, unchanged in meaning.
- Duplicate decisions on grouped entities apply to the WHOLE document, not per line — one
  merge/create/ignore decision per document in a group-aware `DuplicateReview` variant.
  Ungrouped `DuplicateReview` untouched.

**States:** clean (green, computed total shown) / warning `total_mismatch` (orange, both
totals shown) / error `inconsistent_document` (red, names the exact disagreeing field) /
orphan `missing_group_key` (red, one-row group, explicit "no document to attach to" message) /
single-line group (still gets a header row, never special-cased away).

**Constraints:** tokens/logical-CSS only, i18n both locales, gates green
(`check-i18n-parity`, `tsc -b`, `gate03`, `pytest erp/imports`). Exact tint value and exact
header-row column layout are the builder's call (pull tint from tokens, don't invent one) —
everything else above is decided, do not re-litigate.

---

## Before You Start

1. Open the module write-paths for: quotations + orders (`erp/sales/services/`), sales
   invoices (find where invoices are created — sales or accounting), purchase orders +
   invoices (`erp/purchasing/services/`). Note EXACTLY how lines are passed (list-of-dicts
   arg? separate calls?) and what "draft" means per document — **imports create DRAFTS;
   posting stays on module screens** (STRATEGY §3 mechanic 3).
2. Open `erp/imports/registry.py` → `group_by` (session 1 planted it) and `engine.py`'s
   per-row loop — this session teaches the engine about row GROUPS.

"Do not write anything yet."

---

## Task A — Group support in the engine

Flat Excel reality: one row per LINE, document fields repeated (or filled only on the first
line). Add to analyze/engine:

```python
# adapter.group_by = "invoice_number" → rows bucketed by normalized group key.
# Header fields (customer, date, currency…) taken from first row of group; conflicting
# header values within one group → group-level issue "inconsistent_document".
# Blank group key rows → attached to the previous group IF header fields empty
# (merged-cell export pattern), else error.
# Execution: one group = one write call = one document, atomic within the chunk;
# group fails → whole group's rows → error, not a half-document.
# Duplicate detection for documents: natural key = document number (+ party) vs DB → the
# strategy decides (skip_existing default); in-file same number+different content → error.
```

## Task B — Five adapters

`sales_quotations`, `sales_orders`, `sales_invoices`, `purchase_orders`, `purchase_invoices`.
Each: header FieldSpecs (doc number, party ref, date, currency, warehouse?, payment terms?) +
line FieldSpecs (item ref, qty, unit, unit_price money, discount?, tax token) — refs resolve
via existing adapters' lookups (customer/supplier/item/warehouse/unit); tax tokens resolve to
configured tax records (normalize_tax + accounting lookup). `write(actor, group)` builds the
service call for a DRAFT document. Totals: NEVER trust file totals — the module service
computes; if the file HAS a total column, compare and attach a `total_mismatch` WARNING
(not error) with both numbers — the classic dirty-data catch.

## Task C — Tests

Fixture: 3 invoices / 7 lines, repeated headers + one merged-cell-style blank block. Groups
build right; draft invoices created with computed totals; mismatched file total → warning;
inconsistent customer within one invoice number → group error; group atomicity on line-3
failure; existing invoice number honored per strategy.

---

## Smoke Test

- [ ] Real-shaped invoice sheet → 3 draft sales invoices, lines exact, totals computed
- [ ] Preview UI shows the grouped document (session 13 grid renders group headers — verify, small CSS fix allowed)
- [ ] Purchase invoice path same, supplier-side
- [ ] Rollback deletes the drafts (they're unposted)
- [ ] `pytest erp/imports` green

---

## After This Session

```
Smoke test passed?
→ Rename with _done. Update erp-status. /compact.
→ Open FILE_16_FINANCE_ADAPTERS.md in a FRESH session.
```
