# PARALLEL_PLAN — two-agent execution board (2026-07-16)

**Agents:** A = Claude Code / Claude Desktop (ahmedgaid14@gmail.com) · B = Claude Code / VS Code
(ahmedgaid85@gmail.com). Same machine, same repo — **B works in a separate git worktree, never in
the same checkout** (see Setup). This file is the ONLY shared coordination state: every task row
is flipped (todo → doing → done + commit) **in the same commit as the work**. The `erp-status`
skill is updated only at merge checkpoints, only by the merging agent.

Scope = the live queue (`EXECUTION_ORDER.md` pos 8 → 10): pre-handover set, twenty-harvest (TH),
smart-import (SI). One plan FILE = one task = one session, exactly as the plan files define —
this board only adds WHO and WHEN-IN-PARALLEL. The plan files carry the full context, so either
agent can execute any task.

## Ownership map (the anti-conflict rule)

| Territory | Owner | Files |
|---|---|---|
| Frontend + i18n | **A** | `apps/web/**` (incl. `ar.json`/`en.json`), gate03 surface |
| Workflow + webhooks | **A** | `erp/workflow/**`, new `erp/webhooks/**` |
| Core infra + gates | **B** | `erp/core/**`, `scripts/gates/**`, `VERSION`, `CHANGELOG.md`, `Docs/RUNBOOK.md` |
| Imports | **B** | `erp/imports/**` |
| Shared, checkpoint-only | merging agent | `EXECUTION_ORDER.md`, `DECISIONS.md`, `erp-status` skill, plan `_done` renames of the merged wave |

Cross-territory need → the OWNER does it, or the task waits for a checkpoint. Locale keys are
A-only until a checkpoint lands; B backend tasks must not add UI strings (plan files already
split backend/UI into separate FILEs, so this costs nothing).

**Resume command:** `/erp-resume` is lane-aware (skill step 0): checkout path decides —
`C:\AhmedGaid\ERP` → Agent A, `C:\AhmedGaid\ERP-B` → Agent B (email tie-break: ahmedgaid14 → A,
ahmedgaid85 → B). So Claude Desktop opened at ERP resumes lane A; VS Code opened at ERP-B resumes
lane B — automatically.

## ⚠️ Incident 2026-07-16 — both agents ran in ONE checkout (fixed; rules below are now HARD)

What happened: ERP-B worktree was never created, so B executed in `C:\AhmedGaid\ERP` on A's
branch. Wave-1 commits (A1 54a3662, A3 1b951c7, A2 14ca31a, B1 5e1d7d9) all landed mixed on
`feat/a-partial-payments` (work itself valid — merge together at M1). Worse: both lanes shared
test DB `test_erp`; concurrent pytest runs dropped it mid-run → 78 phantom "database does not
exist" errors. Fix applied: worktree `C:\AhmedGaid\ERP-B` created on branch `feat/b-lane`
(from `376a5c9`, contains all wave-1 work), own `.env` (DB `erp_b` → test DB `test_erp_b`,
Redis `/1`), DB created, own venv.

**HARD STOPS (both agents, before EVERY command batch — not just at session start):**
1. `Get-Location` check: Agent B NEVER executes anything (pytest, gates, git commit, runserver,
   npm) inside `C:\AhmedGaid\ERP`. Agent A NEVER inside `C:\AhmedGaid\ERP-B`. Wrong path →
   STOP, tell the user to reopen the editor at the right folder. No exceptions, no "just this once".
2. Branch prefix = identity: A commits only on `feat/a-*`, B only on `feat/b-*`. About to commit
   on the other prefix → you are in the wrong checkout; stop.
3. Test isolation is automatic ONLY via the right checkout (each `.env` carries its own
   DATABASE_URL). Running pytest from the wrong folder silently attacks the other lane's test DB.

## Setup (P0 — DONE 2026-07-16 during incident fix)

1. ✅ `main` pushed to origin.
2. ✅ Agent B environment: worktree `C:\AhmedGaid\ERP-B` on `feat/b-lane` (from `376a5c9`),
   own `.venv`, own `.env` with **DB `erp_b`** (created, migrated), Redis **`/1`**, Django port
   **8001**, Vite **5174**. `npm install` in `apps/web` only if B ever runs web gates (not done —
   B shouldn't need it). Test DBs now disjoint: `test_erp` (A) vs `test_erp_b` (B).
3. Branches: A stays on `feat/a-*` in ERP, B stays on `feat/b-*` in ERP-B, one branch per task or
   per wave; push after every task; PR or ff-merge to `main` only at checkpoints, gate:all green
   first. Wave-1 mixed branch `feat/a-partial-payments` merges as-is at M1; `feat/b-lane` starts
   from its tip, so M1 = merge `feat/b-lane` (which will contain everything) or both, ff order
   A-branch → B-branch.

## Task table

Status: `todo | doing(<agent>) | done(<commit>) | blocked(<why>)`

### Wave 1 — PRE-HANDOVER SET (both lanes, fully parallel)

| ID | Task (= plan file) | Agent | Files/modules | Deps | Est | Checkpoint | Status |
|---|---|---|---|---|---|---|---|
| A1 | Partial payments UI + API tests — `delivery-readiness/FILE_05` | A | apps/web sales collect + purchasing payment dialogs, api clients, ar/en.json; erp/sales+purchasing tests (extend only) | — | 1 session | M1 | done(54a3662) |
| A2 | Playwright E2E — `twenty-harvest/FILE_04` ⛔ new-dep decision: ask founder FIRST; denied → the file's Option B fallback | A | new `e2e/`, apps/web package.json | A1 (so flows incl. partials) | 1–2 sessions | M1 (not gate-blocking) | done(14ca31a) |
| A3 | Outbound webhooks — `twenty-harvest/FILE_05` | A | erp/notifications (extend), settings, tests | — | 1 session | M2 | done(1b951c7) |
| B1 | `provision_customer` — `delivery-readiness/FILE_06` | A (cross-lane, B idle) | `erp/core/management/commands/provision_customer.py`, erp/core tests, RUNBOOK §install | — | 1 session | M1 | done(5e1d7d9) |
| B2 | Release versioning — `twenty-harvest/FILE_01` | A (cross-lane, B idle) | `VERSION`, `CHANGELOG.md`, version surface | — | 0.5 | M1 | done(9e2b422) |
| B3 | `manage.py upgrade` — `twenty-harvest/FILE_02` | B | erp/core models+migration, upgrade command, tests, RUNBOOK §upgrade | B2 | 1 session | M1 | done(98f1af6) |
| B4 | gate16 drill + gate17 API snapshot — `twenty-harvest/FILE_03` | B | `scripts/gates/gate16.py`, `gate17.py`, `_run.py`, snapshot | B3 | 1 session | M1 | done(3d4d25a) |

**M1 (sync):** merge A1 + B1–B4 to main → `gate:all` 00–17 green → **D7 = HANDOVER GATE**
(`delivery-readiness/FILE_07`): founder + Either agent, dev dry run then real customer box.
A2/A3 merge at M1 if ready, else M2 — they never block the gate.

### Wave 2 — post-gate (fully parallel lanes)

| ID | Task | Agent | Files/modules | Deps | Est | Checkpoint | Status |
|---|---|---|---|---|---|---|---|
| A4 | Saved views backend — `TH/FILE_06` | A | erp/core SavedView model+API (**coordinate: B is out of erp/core after B4**) | M1 | 1 | M2 | todo |
| A5 | Saved views UI — `TH/FILE_07` | A | apps/web list pages, ar/en.json | A4 | 1 | **M2 = TH Tier 1 merge** | todo |
| A6 | ⌘K actions — `TH/FILE_08` | A | apps/web command menu | A5 | 1 | M3 | todo |
| B5 | Auto-masters — `SI/FILE_08` | B | erp/imports | M1 (queue priority only — may start early if B-lane idles in wave 1) | 1 | M2 | done(849a30f) |
| B6 | Execution engine — `SI/FILE_09` | B | erp/imports | B5 | 1 | M2 | done(68642c3) |
| B7 | Background runner — `SI/FILE_10` | B | erp/imports (DB-backed queue, not Celery — see DECISIONS.md) | B6 | 1 | **M2 = SI engine merge (NOT yet merged — needs Agent A coordination + gate:all)** | done(b1a3a70) |
| B8 | Import API — `SI/FILE_11` | B | erp/imports/api | B7 | 1 | M3 | done(91da71a) |

### Wave 3+ — continuation by ownership (summarized; scope = each plan file, as written)

| ID | Task | Agent | Files/modules | Deps | Status |
|---|---|---|---|---|---|
| B9 | Custom fields backend — `TH/FILE_11` | B | `erp/core/custom_fields.py` (+api), Customer/Item `custom_data`, sales+inventory API hooks | M1 | done(eab66b5) |
| B10 | Activity timeline — Task A only (read API) — `TH/FILE_13` | B | `erp/audit/api`, `erp/audit/history.py` — Task B (tab UI) + Task C (verifiability link) deferred to A, apps/web+i18n untouched | B9 | done(1b0a9b2) — FILE_13 stays open, not `_done` |
| B11 | Document adapters — Task A (group-by engine) + Task B all five adapters — `SI/FILE_15` | B | `erp/imports/engine.py`, `registry.py`, `adapters/sales.py`, `adapters/purchasing.py`, `tests/test_document_adapters.py` | B10 | done(03791cc) then done(b385831) — 5/5 adapters, `pytest erp/imports` green (305 passed), gate:all 00-02/04-17 green (gate03 N/A on B — no apps/web node_modules). FILE_15 stays open, not `_done` — smoke test's "preview UI shows grouped document" bullet is apps/web, A's territory, unverified by B |
| B12 | Finance adapters — `journal_entries` + `account_opening` only — `SI/FILE_16` | B | `erp/imports/adapters/accounting.py`, `engine.py` (new `validate_group` group-level hook + rollback dedup fix), `config/settings/base.py` (IMPORTS_DEFAULTS suspense), `tests/test_finance_adapters.py` | B11 | done(HEAD) — 2 adapters: draft journal entries (per-entry balance guard) + whole-file opening entry with HITL suspense-correction proposal (approval flag on batch.stats). **BLOCKER, not built:** `payments`/`receipts` (only order-attached write-paths, POST GL, need posted invoice, no unallocated model) + `inventory_opening`/`inventory_transactions` (no draft/GL-correct opening service; WAC has no as-of-date; would double-count the Inventory control account). `pytest erp/imports erp/accounting erp/inventory` green (441), gate:all 00-02/04-17 green. FILE_16 stays open, not `_done` — suspense-approval creation-plan PANEL is apps/web (A), unverified by B |
| B13 | API keys backend — Task A (model+authclass+service) + Task D (tests) only — `TH/FILE_14` | B | `erp/identity/models.py` (ApiKey), `erp/identity/authentication.py` (new — `ApiKeyAuthentication`, `ApiKeyRateThrottle`), `erp/identity/api_keys.py` (new — create/revoke/list, admin-only), `erp/identity/views.py` + `roles_admin.py` (exclude hidden key-principal from Users list / role member counts), `config/settings/base.py`+`dev.py` (auth class + `api_key` throttle scope), migration `0011_apikey`, `erp/identity/tests/test_api_keys.py` | B12 | done(e64191d) — a key authenticates as a hidden, auto-created "principal" user (unusable password, excluded from the human Users list) added to the bound role's group, so it rides the exact same RBAC/scoping/audit path a human login uses — no parallel permission logic. `pytest` full suite green (1296 passed, 1 pre-existing skip), gate:all 00-02/04-17 green (gate03 N/A on B — no apps/web node_modules). FILE_14 stays open, not `_done` — Task B (Settings → Developers keys UI) + Task C (reference page) are apps/web, A's territory, unbuilt |
| B14 | Admin/system panel — Task A (backend endpoint) + Task C (tests) only — `TH/FILE_19` | B | `erp/monitoring/status_api.py` (new — `GET /api/system/status/`, admin-only), `config/urls.py` (mount), `config/settings/base.py` (`BACKUP_DIR`), `.env.example`, `erp/monitoring/tests/test_status_api.py` | B13 | done(HEAD) — version/uptime/DB+Redis latency/storage free space/Celery worker count+queue depth/backup freshness/env-var NAMES (set/unset only, values never serialized — asserted aggressively in tests), overall status rolls up the worst component. `pytest` full suite green (1304 passed, 1 pre-existing skip), gate:all 00-02/04-17 green (gate03 N/A on B — no apps/web node_modules). FILE_19 stays open, not `_done` — Task B (Settings → النظام UI page) is apps/web, A's territory, unbuilt |
| B15 | AI usage & cost page — Task A (read endpoint) + Task C (tests) only — `TH/FILE_20` | B | `erp/assistant/api/usage.py` (new — `GET /api/assistant/usage/?month=`, admin-only), `erp/assistant/api/urls.py` (mount), `erp/assistant/tests/test_usage.py` | B14 | done(HEAD) — straight aggregation over existing `Trace`/`Budget`/`SpendRollup` records, zero new tracking: month totals (requests, tokens in/out, cost microcents, cache-hit share, degraded-minutes), per-provider split, per-user table, budget-vs-consumed (org scope pairs its monthly `SpendRollup` row exactly; request/user-daily scopes expose config only — no monthly "consumed" figure invented for ceilings that reset per-call/per-day). Cost stays in microcents (same USD convention as `api/ops` — no EGP/FX conversion fabricated). `degraded_minutes` = exact count of distinct calendar-minutes with stored `routing.skipped` evidence, not a live-state estimate replayed onto the past. `pytest` full suite green (1318 passed, 1 pre-existing skip), gate:all 00-02/04-17 green (gate03 N/A on B — no apps/web node_modules; gate17 confirms the new route as non-breaking). FILE_20 stays open, not `_done` — Task B (Settings → AI page UI) is apps/web, A's territory, unbuilt |
| B16 | Draftable payments — `PendingPayment` (smart-import FILE_16 Task B follow-up) | B | `erp/sales/domain/models.py`+`services/pending_payments.py`, `erp/purchasing/domain/models.py`+`services/pending_payments.py`, `erp/imports/engine.py` (row-warning support), `erp/imports/adapters/{sales,purchasing}.py` (`receipts`/`payments`), both modules' `api/` (list/apply/discard/match) | B15 | done(d8ba38c) — backend + API + tests only; review screen is apps/web, Agent A's territory, unbuilt. Sub-project 2 (inventory opening) specced in `DESIGN_PENDING_PAYMENTS_AND_STOCK.md`, not yet built. |
| B17 | Reconciled inventory opening — `PendingStockEntry` (smart-import FILE_16 sub-project 2, follow-up to B16) | B | `erp/inventory/domain/models.py` (+migration), `erp/inventory/services/pending_stock.py`, `erp/imports/adapters/inventory.py` (`inventory_opening`), `erp/imports/adapters/accounting.py` (`inventory_double_booked` guard on `account_opening`), `config/settings/base.py` (`IMPORTS_DEFAULTS`), `erp/accounting/services/seeding.py` (COA `3110`) | B16 | done(HEAD) — TDD throughout; `PendingStockEntry` posts to a dedicated suspense account (3110), never GRNI; new `MovementType.OPENING`; `account_opening` blocks with `inventory_double_booked` when an `inventory_opening` batch exists (checked via `erp.imports.models.ImportBatch`, no circular import into `erp.inventory`). `inventory_transactions` stays the documented, explicitly-descoped blocker. `FILE_16_FINANCE_ADAPTERS.md` renamed `_done` — nothing left to build against it. Review/apply screen is apps/web, Agent A's territory, unbuilt (mirrors B12–B16 precedent). Full regression (`erp/imports erp/inventory erp/accounting erp/sales erp/purchasing`) running; gate:all pending. |

- **A:** TH FILE_09 approval node → FILE_10 AI agent node (erp/workflow + canvas UI) →
  FILE_12 custom-fields UI (needs B's FILE_11, done — see B9) → SI FILE_12–14 wizard/preview/report
  UI → TH FILE_16–18 UX batch.
- **B:** TH FILE_13 activity timeline backend (done, B10) → SI FILE_15 all 5 adapters (done, B11) →
  SI FILE_16 finance adapters (done, B12 — journals + GL-opening only; payments + inventory-opening
  are documented blockers) → TH FILE_14 API keys backend (done, B13 — Task A+D only, keys UI/docs
  page deferred to A) → TH FILE_19 admin panel backend (done, B14 — Task A+C only, System page UI
  deferred to A) → TH FILE_20 AI usage/cost backend (done, B15 — Task A+C only, Settings → AI page
  UI deferred to A) → B16 draftable payments (done — see above) → B17 reconciled inventory opening
  (done — see above) → **next: check board for a new task (smart-import/twenty-harvest wave 3+
  queue, or coordinate an M-checkpoint merge with Agent A).**
- **M3:** TH Tier 2 merge after FILE_13; SI Phase-A demo merge after FILE_14. TH FILE_21 +
  SI FILE_17 acceptances run single-agent (Either) on merged main.

## Critical path

`B1 → B2 → B3 → B4 → M1 merge → D7 handover gate` (~4.5 agent sessions + founder time).
Everything in the A lane is off the critical path — A must never block M1 on A2/A3.

## Fully parallel (no coordination needed)

A1‖B1–B4 (disjoint modules), A2‖B-anything, A3‖B-anything, A4–A6‖B5–B8, wave-3 lanes.

## Requires synchronization

- **M1/M2/M3 merges** — one agent merges, runs `gate:all`, renames `_done`, updates
  EXECUTION_ORDER + erp-status; the other agent `git pull` + rebases before its next task.
- **D7 handover gate** — human-in-the-loop by design.
- **A4** enters `erp/core` — only after B4 is done(…) on this board.
- **TH FILE_12 (A)** after **TH FILE_11 (B)**.
- **⛔ decisions** (A2 Playwright dep; any new dep anywhere) — founder answers once, recorded in
  DECISIONS.md at the next checkpoint.

## Takeover instructions (either agent, cold start)

1. `git pull origin main`; `git fetch --all`; read THIS file top to bottom.
2. Any row `doing(<other agent>)`? Check its branch (`feat/a-*`/`feat/b-*`) last commit: work
   complete but board stale → flip to done and continue; work partial → finish it following the
   plan FILE's own checklist (each FILE is self-contained: Before You Start → Tasks → Smoke Test).
3. No doing rows → claim the lowest-wave `todo` in YOUR lane; your lane empty → claim the other
   lane's next `todo` (flip the Agent column — assignments are preferences, not locks).
4. Solo mode (other agent gone): ignore lanes, execute rows in EXECUTION_ORDER queue order
   (A1, B1, B2, B3, B4, M1, D7, then wave 2), one FILE per session, same checkpoints.
5. Always: flip status in the same commit as the work; push every task; never edit the other
   lane's territory without flipping ownership here first.

*Board created 2026-07-16 by the planning session (commit follows). Authority for WHAT each task
does = the plan FILEs; authority for queue order = EXECUTION_ORDER.md; this board only owns
WHO/WHEN-PARALLEL.*
