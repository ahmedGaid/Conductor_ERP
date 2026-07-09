# D1 — Core ERP Foundation

> The money loop (sales → inventory → purchasing → accounting → VAT) made complete and
> correct-by-construction. Scope guard: NO HR / manufacturing / projects (ARP_STRATEGY §5).
> Existing owners: costing → `Docs/plan/03-core-costing.md`; real ETA API →
> `Docs/plan/09-eta-integration.md`; cycle-coverage ideas → `Docs/plan/business-cycles-source/`
> (harvest verdict: take items, don't execute the plan). This file adds the correctness floor
> those plans assume.

---

## Phase D1.P1 — Ledger correctness floor

### D1.P1.T1 — DB-level double-entry invariant
**Status:** todo · **Model:** Sonnet
**Objective:** every posted journal entry is balanced (sum debits == sum credits) enforced by the database, not only service code.
**Rationale:** service-layer checks can be bypassed by new code paths (imports, agents, fixes in shell). Trust is value #1; the ledger must be unbreakable by construction.
**Prerequisites:** none (standalone).
**Steps:**
1. `codegraph_explore` "journal entry posting service and models" → confirm model names in `erp/accounting/domain/` + posting service in `erp/accounting/services/`.
2. Add a deferred DB constraint or trigger-equivalent: simplest portable form = a `CHECK`-backed aggregate is not possible in Postgres per-row, so add `transaction.atomic` posting path assertion PLUS a Postgres trigger (migration with `RunSQL`) that raises on `INSERT/UPDATE` to journal lines when the parent entry is posted and unbalanced.
3. Add a management command `erp/accounting/management/commands/verify_ledger.py`: scans all posted entries, reports any unbalanced/orphan lines, exit code 1 on findings.
4. Wire the command into the gate runner (`scripts/gates/_run.py`) as an accounting invariant gate.
**Architecture decisions:** trigger lives in a migration (versioned, reviewable); command is read-only; no ORM signal-based enforcement (signals skip `bulk_create`).
**Affected files:** `erp/accounting/migrations/NNNN_ledger_trigger.py` (new), `erp/accounting/management/commands/verify_ledger.py` (new), `scripts/gates/_run.py` (modify), `erp/accounting/tests/test_ledger_invariant.py` (new).
**Acceptance criteria:** (a) posting an unbalanced entry via raw SQL fails; (b) `verify_ledger` exits 0 on current data; (c) posting via existing services still passes all module tests.
**Testing:** `pytest erp/accounting` green; new test posts balanced (passes) + attempts unbalanced insert inside `pytest.raises`.
**DoD:** gates green, criteria a–c demonstrated in tests, status flipped, `erp-status` updated.

### D1.P1.T2 — Period locks (hard close)
**Status:** todo · **Model:** Sonnet
**Objective:** a closed accounting period rejects any posting, edit, or deletion dated inside it, across every write path.
**Rationale:** month-close (arp Phase B) is meaningless if a later write can mutate a closed month. Auditors ask this first.
**Prerequisites:** D1.P1.T1.
**Steps:**
1. `codegraph_explore` "accounting period model close status" → find/confirm period model; if none exists, create `AccountingPeriod` (`year`, `month`, `status: open|closed`, `closed_by`, `closed_at`) in `erp/accounting/domain/`.
2. Add `assert_period_open(date)` helper in the accounting services layer; call it in the single posting choke-point (posting service — every module posts through it per contract architecture).
3. Close/reopen endpoints in `erp/accounting/api/` — RBAC: reopen requires a distinct permission; both write `audit.record`.
4. UI: period list + close action under the accounting settings page; closed period shows who/when; Arabic term from Identity System §6 (add before shipping if missing).
5. i18n keys in both `ar.json`/`en.json`; designed empty state ("no closed periods yet").
**Architecture decisions:** enforcement at the posting choke-point ONLY (one way to do each thing); reopen is permission-gated + audited, not forbidden.
**Affected files:** `erp/accounting/domain/` (+model), `erp/accounting/services/` (guard), `erp/accounting/api/` (+endpoints), migration, `apps/web/src/pages/` accounting settings page, locales, tests.
**Acceptance criteria:** (a) posting into a closed period raises a blame-free, actionable error naming the period and who can reopen; (b) imports and AI safe-actions hit the same guard; (c) reopen audited.
**Testing:** `pytest erp/accounting` — tests: post-into-closed fails, reopen+post passes, audit rows exist. Web gates + parity.
**DoD:** gates + brand-feel checklist (UI touched), status flipped, `erp-status` updated.

### D1.P1.T3 — Document sequence integrity audit
**Status:** todo · **Model:** Haiku
**Objective:** one management command reporting gaps/duplicates in every document number sequence (invoices, credit notes, POs, receipts).
**Rationale:** ETA + auditors require gapless sequences; anomaly-watch (arp build item 4) needs this primitive.
**Prerequisites:** none.
**Steps:**
1. `codegraph_explore` "document number sequence generation" → list every numbered document model + its sequence field.
2. Write `erp/core/management/commands/verify_sequences.py`: for each registered model, detect gaps + duplicates per series/year; table output; `--json` flag; exit 1 on duplicates (gaps warn only — voids are legal).
3. Register in gate runner as warn-level.
**Architecture decisions:** registry is a simple list in the command (no new abstraction).
**Affected files:** `erp/core/management/commands/verify_sequences.py` (new), `scripts/gates/_run.py`, `erp/core/tests/`.
**Acceptance criteria:** command runs on dev DB listing all series; seeded duplicate detected in test.
**Testing:** unit test with factory data: contiguous passes, gap warns, duplicate fails.
**DoD:** gates green, status flipped.

### D1.P1.T4 — Opening balances path
**Status:** todo · **Model:** Sonnet
**Objective:** a supported, validated way to enter opening balances (GL, AR/AP per partner, inventory quantities) that produces a single balanced opening entry.
**Rationale:** every migrated company needs this day one; smart-import (queue 8) imports INTO this path — it must exist first as a service.
**Prerequisites:** D1.P1.T1, D1.P1.T2.
**Steps:**
1. Service `erp/accounting/services/opening_balances.py`: accepts typed rows (account, partner?, amount minor-units, currency), validates trial balance balances, posts ONE journal entry flagged `is_opening=True` into the designated opening period.
2. Inventory side: opening quantities via existing inventory adjustment service, valued at provided unit cost (integer minor units).
3. Contract-decorated action so the assistant/import engine can call it (propose→confirm per §3 mechanics).
4. Minimal UI: settings page form with per-row validation + imbalance banner showing the exact difference and a one-click "post difference to opening-equity" fix (proposed, not silent).
**Architecture decisions:** one entry, not per-row entries; imbalance never auto-fixed silently — always proposed (blame-free, actionable).
**Affected files:** `erp/accounting/services/opening_balances.py` (new), `erp/accounting/contracts/`, `erp/accounting/api/`, `erp/inventory/services/` (reuse), web settings page, locales, tests both apps.
**Acceptance criteria:** balanced set posts one opening entry; unbalanced set blocked with actionable proposal; inventory valuation report reflects opening qty×cost.
**Testing:** `pytest erp/accounting erp/inventory`; web gates.
**DoD:** gates + checklist, status flipped.

## Phase D1.P2 — Costing & valuation (owner: `03-core-costing.md`)

### D1.P2.T1 — Execute legacy plan 03 (costing) under current architecture
**Status:** todo · **Model:** Opus (architecture) then Sonnet (rollout)
**Objective:** moving-average cost per item, COGS posted on delivery/invoice per current flow, landed-cost allocation on purchase receipts, valuation report.
**Rationale:** without COGS the P&L lies; reports phase (D8) is blocked on it.
**Prerequisites:** D1.P1.T1; read `Docs/plan/03-core-costing.md` FIRST — it is the spec; this task only re-anchors it post-refactors.
**Steps:** 1. Read plan 03. 2. `codegraph_explore` inventory movement + posting services to re-map its steps onto today's layered accounting app. 3. Split into ≤3 sessions at plan 03's own checkpoints; execute with its acceptance list. 4. Valuation snapshot table + report endpoint.
**Architecture decisions:** moving average only (no FIFO toggle — settings discipline, ARP_STRATEGY §5.2); costs in integer minor units; recompute command for corrections.
**Affected files:** per plan 03 + `erp/inventory/services/costing.py` (new), accounting posting hooks, report endpoint, web report page, locales.
**Acceptance criteria:** plan 03's own acceptance + valuation report total == GL inventory account balance (reconciliation test).
**Testing:** module pytest both apps; golden scenario test: purchase→receipt→sale→COGS numbers exact.
**DoD:** gates + checklist; mark plan 03 `_done` too; status flipped.

## Phase D1.P3 — Tax & compliance

### D1.P3.T1 — Real ETA integration (owner: `09-eta-integration.md`)
**Status:** todo · **Model:** Opus
**Objective:** replace the submit/poll stub with the real ETA e-invoicing API (sandbox first), full signature + status lifecycle.
**Rationale:** the wedge demo must be real (plan README: before any recorded demo).
**Prerequisites:** D1.P1.T3 (sequences); ETA sandbox credentials from founder (BLOCKER if absent — record in erp-status).
**Steps:** read plan 09 and execute it; it is current owner. On completion update `erp/einvoice/` docs section.
**Architecture decisions:** per plan 09; secrets via env only (D5.P2.T2 pattern); retry queue idempotent.
**Affected files:** `erp/einvoice/*` per plan 09.
**Acceptance criteria/Testing/DoD:** per plan 09 + `pytest erp/einvoice` green.

### D1.P3.T2 — VAT return reconciliation check
**Status:** todo · **Model:** Sonnet
**Objective:** VAT return draft cross-checks against GL VAT accounts; any difference itemized line-by-line.
**Rationale:** month-close agent (Phase B) approves this card; number must be verifiable by click (§3 mechanic 4).
**Prerequisites:** D1.P2.T1.
**Steps:** 1. Locate existing VAT return module via codegraph. 2. Add reconciliation service comparing return boxes vs GL account movements for the period. 3. Difference list with per-document drill links. 4. Card in the return page UI.
**Architecture decisions:** read-only; no auto-adjustment.
**Affected files:** `erp/accounting/services/vat_reconcile.py` (new), api, web return page, locales, tests.
**Acceptance criteria:** seeded mismatch shows exact documents; matched period shows designed "all reconciled" state.
**Testing:** pytest scenario with deliberate mismatch; web gates.
**DoD:** gates + checklist, status flipped.

## Phase D1.P4 — Cycle-coverage harvest

### D1.P4.T1 — Harvest list from business-cycles-source
**Status:** todo · **Model:** Opus (judgment) — single session
**Objective:** extract the approved "harvest" items from `Docs/plan/business-cycles-source/` into concrete tasks appended to this file (D1.P4.T2+), each in the standard template.
**Rationale:** verdict (commit cca726e) = harvest, don't execute. Items must not rot in a source folder.
**Prerequisites:** none.
**Steps:** 1. Read the source folder + its verdict doc. 2. For each item passing the ARP test + scope rules: write a task block here. 3. Items failing scope: list under a "refused" note with one-line reason each.
**Architecture decisions:** n/a (planning task).
**Affected files:** this file only.
**Acceptance criteria:** every source item dispositioned (task or refused); no silent drops.
**Testing:** n/a.
**DoD:** commit + status flipped.
