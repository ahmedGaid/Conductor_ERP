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
| Frontend + i18n | **A** (see override below) | `apps/web/**` (incl. `ar.json`/`en.json`), gate03 surface |
| Workflow + webhooks | **A** | `erp/workflow/**`, new `erp/webhooks/**` |
| Core infra + gates | **B** | `erp/core/**`, `scripts/gates/**`, `VERSION`, `CHANGELOG.md`, `Docs/RUNBOOK.md` |
| Imports | **B** | `erp/imports/**` |
| Shared, checkpoint-only | merging agent | `EXECUTION_ORDER.md`, `DECISIONS.md`, `erp-status` skill, plan `_done` renames of the merged wave |

Cross-territory need → the OWNER does it, or the task waits for a checkpoint. Locale keys are
A-only until a checkpoint lands; B backend tasks must not add UI strings (plan files already
split backend/UI into separate FILEs, so this costs nothing).

### ⚠️ Founder override (2026-07-18) — B takes most remaining apps/web work

Reason: B has more token budget than A right now. B-lane was IDLE (per M3 audit, all remaining
undone plan files are `apps/web`) while A carries the whole frontend backlog alone — founder
wants that rebalanced. `apps/web/node_modules` already exists in B's worktree (installed for A7),
so B can run `tsc -b`/gate03 there.

**New split (supersedes the row above until reversed):**
- **B** takes the named UI hand-off files it already has backend-complete: TH FILE_19 (System
  settings page), TH FILE_20 (Settings → AI usage page), SI FILE_12–15 (import wizard/preview/
  adapter-review screens), and the review/apply screens for B16 (draftable payments) + B17
  (reconciled inventory opening). One FILE per session, same rules as any other task (i18n
  parity + `tsc -b` + gate03 + live verify where possible).
- **A** keeps: any interrupt/bug work, the paused dynamic-help rollout (H), and anything
  newly opened by the founder — plus first refusal on any file that touches `erp/workflow`/
  `erp/webhooks` even if its UI half is apps/web (that stays A's, cross-territory rule unchanged).
- **Anti-conflict:** each hand-off file above touches a disjoint page/route (Settings→System,
  Settings→AI, import wizard steps, payments/stock review panels) — no two rows below share a
  file. Before starting, B still does the Setup §HARD STOP checks (own worktree/branch) and
  `git pull` first, since A may have pushed frontend infra changes (e.g. the gate03 bundle-size
  fix flagged in the B health check below) that a new B session would otherwise miss.
- Reversion: if B's queue empties again or founder says otherwise, ownership map row above
  resumes as written.

### ⚠️ Founder override (2026-07-18, evening) — B is now PRIMARY lane for the QA-audit plans

Reason: **A hits its usage limit sooner than B.** Founder wants the four new QA-audit plans
(`pre-handover-hardening`, `einvoice-eta-live`, `post-handover-v1_1`, `brand-philosophy-review`)
carried by **B**, so work continues after A is spent. This SUPERSEDES both rows above for these
plans until reversed.

**Handoff precondition (do FIRST, before B takes apps/web work):** A commits + pushes any in-flight
`apps/web` work and tells B; B `git pull` in its worktree so it owns a clean frontend base. While A
still has budget it does only interrupts/bugs; once A is spent, **B is solo on everything**. The
A-only locale-key rule is LIFTED for these plans — B owns `ar.json`/`en.json` edits here (no
concurrent A editing them). HARD STOPS unchanged: B stays in `C:\AhmedGaid\ERP-B` on `feat/b-*`,
never in A's checkout.

**Assignments (all → B unless noted):**

| Task (= plan file) | Agent | Files | Status / note |
|---|---|---|---|
| pre-handover-hardening FILE_01 ETA decision | A | DECISIONS.md | done 2026-07-18 (Branch A) |
| pre-handover-hardening FILE_02 CI safety net | A | `.github/workflows/ci.yml` | done 2026-07-18 (main red = bundle-size, see below) |
| **bundle-size fix** (blocks CI green) | ~~B~~ **A** | `apps/web` route-split/lazy-import | done 2026-07-18 by A (user-directed session) — main chunk 260.7kB → 203.4kB gzip, gate03 green |
| pre-handover-hardening FILE_03 error boundary | ~~B~~ **A** | `apps/web` + ar/en.json | done 2026-07-18 by A — B: `git pull` before continuing to FILE_04 |
| pre-handover-hardening FILE_04 gate-run artifact | **B** | run gates, save log | needs green gate03 first |
| pre-handover-hardening FILE_05 LICENSE+terms | **B** | root `LICENSE`, README, pyproject | founder picks license (FILE_05 asks) |
| pre-handover-hardening FILE_06 loose ends | **B** coord | DB user delete = B; canvas smoke + partial-pay Q = **human/founder** (not an agent task) | **DB user delete done 2026-07-19 by A** — `phase1d_qa` (pk 9) suspended on A's dev DB `erp`; the real target B couldn't reach under the HARD STOP. Canvas smoke + partial-pay Q still open, human-only. |
| einvoice-eta-live FILE_01→05 | **B** | `erp/einvoice/**` (B's native territory) | ⛔ STOP-gated: needs customer ETA creds + tax profile before FILE_01 there starts |
| post-handover-v1_1 FILE_01→05 | ~~B~~ **A** | CI/backend + one `apps/web` (FILE_04 Vitest) | **done 2026-07-19 by A** — founder redirected an A session onto B's backlog after browser-dependent B-scope work (twenty-harvest FILE_21, brand-philosophy-review) turned out unrunnable in that session's harness (no screenshot/JS-eval tool). Founder approved all 4 new dev tools (bandit/pip-compile/pytest-cov/Vitest) in one batch. Detail in `DECISIONS.md`. B: `git pull` before continuing. |
| brand-philosophy-review sessions A→H | **B** | read-only UI review; appends to `scorecard.html` + findings | low conflict (no product-code edits in the review pass). ⚠️ **Needs a harness with screenshot/JS-eval tooling** — confirmed 2026-07-19 that a plain VSCode-extension session has neither; check before assigning a session here. |

**A keeps:** live interrupts/bugs, `erp/workflow`+`erp/webhooks` first-refusal (cross-territory
rule holds), and the paused dynamic-help rollout (H) only if A has spare budget. Otherwise A idles.

**Anti-conflict:** since A is winding down, B being sole owner of `apps/web` removes the concurrent-
edit risk entirely — the split above is about SEQUENCING B's own sessions (one FILE per session),
not about A/B contention. B still `git pull` before each session in case A pushed an interrupt fix.

**Reversion:** founder says so, or A's budget refreshes and founder rebalances.

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
| A4 | Saved views backend — `TH/FILE_06` | A | erp/core SavedView model+API (**coordinate: B is out of erp/core after B4**) | M1 | 1 | M2 | done(c4c8e0d) |
| A5 | Saved views UI — `TH/FILE_07` | A | apps/web list pages, ar/en.json | A4 | 1 | **M2 = TH Tier 1 merge** | done(c4c8e0d) |
| A6 | ⌘K actions — `TH/FILE_08` | A (started ahead of A5 — founder override, palette/registry/role-filter/context-inject already shipped by unified-ui; this session found+fixed a duplicate-action bug across 5 detail pages) | apps/web command menu | A5 | 1 | M3 | done(32c054b) |
| B5 | Auto-masters — `SI/FILE_08` | B | erp/imports | M1 (queue priority only — may start early if B-lane idles in wave 1) | 1 | M2 | done(849a30f) |
| B6 | Execution engine — `SI/FILE_09` | B | erp/imports | B5 | 1 | M2 | done(68642c3) |
| B7 | Background runner — `SI/FILE_10` | B | erp/imports (DB-backed queue, not Celery — see DECISIONS.md) | B6 | 1 | **M2 = SI engine merge — DONE 2026-07-18, merged to `main` at `d271c58`** | done(b1a3a70) |
| B8 | Import API — `SI/FILE_11` | B | erp/imports/api | B7 | 1 | M3 | done(91da71a) |

**M2 (sync, 2026-07-18):** B merged `feat/b-lane` → `main` (fast-forward, `d271c58`) — brings all
of B1–B17 (SI engine + wave-2/3 backend halves) onto `main` alongside A's work through the same
point (TH FILE_09 approval node, saved-views UI, ⌘K dedupe, ComboBox/DatePicker rollout, Popover
reflow fix). gate:all 00-02/04-17 green on the merged tip before push (gate03 N/A on B); full
`pytest` green (1369 passed, 1 pre-existing skip). A must `git pull origin main` (or rebase
`feat/a-partial-payments`) before its next task. SI FILE_17 acceptance is now unblocked (was
waiting on this merge); the apps/web review/apply screens B left unbuilt (TH FILE_12–20, SI
FILE_12–15) are A's next backend-complete territory to pick up.

**Reconciliation (2026-07-18, B session):** discovered local `main` (checked out in A's `ERP`
worktree, un-pushed) and `origin/main` had diverged since `8ab8476` — A's TH FILE_10
(assistant-action node, `8e78a45`/`8a0f6ea`) never reached GitHub while B's M2-sync docs
(`d2ff732`/`a109c3f`) had. Verified clean merge (`git merge-tree`, no conflicts), pushed a merge
commit (`f7ebf47`) straight to `origin/main` as plumbing — A's local `main` ref/worktree untouched,
next `git pull` there fast-forwards cleanly. **Lesson: commit task work to `feat/a-*`/`feat/b-*`
and push per-task, never straight to local `main`** — that's what let this drift happen unseen.

### Wave 3+ — continuation by ownership (summarized; scope = each plan file, as written)

| ID | Task | Agent | Files/modules | Deps | Status |
|---|---|---|---|---|---|
| B9 | Custom fields backend — `TH/FILE_11` | B | `erp/core/custom_fields.py` (+api), Customer/Item `custom_data`, sales+inventory API hooks | M1 | done(eab66b5) |
| B10 | Activity timeline — Task A only (read API) — `TH/FILE_13` | B | `erp/audit/api`, `erp/audit/history.py` — Task B (tab UI) + Task C (verifiability link) deferred to A, apps/web+i18n untouched | B9 | done(1b0a9b2) |
| A8 | Activity timeline — Task B (tab UI, load-more pagination) + Task C (AI/import source glyph) — `TH/FILE_13` | A | `apps/web/src/components/RecordTimeline.tsx`, `apps/web/src/api/audit.ts`, `apps/web/src/components/recordTimeline.css`, `ar.json`/`en.json`; also fixed a real bug found during integration: `erp/audit/api/views.py` returned pagination metadata as siblings of `data` instead of nested inside it, so `apiFetch`'s generic `{data}` envelope unwrap silently discarded `page`/`page_size`/`total` and the tab always rendered empty — nested it (`data: {items, page, page_size, total}`), updated `test_timeline_api.py`. Also retired the now-superseded non-paginated `RecordHistoryView`/`getRecordHistory`/`record_timeline` (only caller was the old `RecordTimeline.tsx` this session replaced) and deleted `test_history_api.py`. The 4 highest-dispute surfaces (SalesOrder, PurchaseOrder, Customer/Supplier via `PartyDetailView`, Invoice via `JournalDetailPage`) already had `RecordTimeline` mounted from linear-polish FILE_07 — no call-site changes needed, just upgraded the component + backend underneath. Source glyph (sparkle=AI, download=import) verified end-to-end against a real dev server with a synthetic `module="assistant"` audit row (added then removed). `pytest erp/audit erp/sales erp/purchasing erp/accounting` (244) + i18n parity + `tsc -b` + gate03 all green. FILE_13 renamed `_done`. | B10 | done(HEAD) |
| B11 | Document adapters — Task A (group-by engine) + Task B all five adapters — `SI/FILE_15` | B | `erp/imports/engine.py`, `registry.py`, `adapters/sales.py`, `adapters/purchasing.py`, `tests/test_document_adapters.py` | B10 | done(03791cc) then done(b385831) — 5/5 adapters, `pytest erp/imports` green (305 passed), gate:all 00-02/04-17 green (gate03 N/A on B — no apps/web node_modules). FILE_15 stays open, not `_done` — smoke test's "preview UI shows grouped document" bullet is apps/web, A's territory, unverified by B |
| B12 | Finance adapters — `journal_entries` + `account_opening` only — `SI/FILE_16` | B | `erp/imports/adapters/accounting.py`, `engine.py` (new `validate_group` group-level hook + rollback dedup fix), `config/settings/base.py` (IMPORTS_DEFAULTS suspense), `tests/test_finance_adapters.py` | B11 | done(HEAD) — 2 adapters: draft journal entries (per-entry balance guard) + whole-file opening entry with HITL suspense-correction proposal (approval flag on batch.stats). **BLOCKER, not built:** `payments`/`receipts` (only order-attached write-paths, POST GL, need posted invoice, no unallocated model) + `inventory_opening`/`inventory_transactions` (no draft/GL-correct opening service; WAC has no as-of-date; would double-count the Inventory control account). `pytest erp/imports erp/accounting erp/inventory` green (441), gate:all 00-02/04-17 green. FILE_16 stays open, not `_done` — suspense-approval creation-plan PANEL is apps/web (A), unverified by B |
| B13 | API keys backend — Task A (model+authclass+service) + Task D (tests) only — `TH/FILE_14` | B | `erp/identity/models.py` (ApiKey), `erp/identity/authentication.py` (new — `ApiKeyAuthentication`, `ApiKeyRateThrottle`), `erp/identity/api_keys.py` (new — create/revoke/list, admin-only), `erp/identity/views.py` + `roles_admin.py` (exclude hidden key-principal from Users list / role member counts), `config/settings/base.py`+`dev.py` (auth class + `api_key` throttle scope), migration `0011_apikey`, `erp/identity/tests/test_api_keys.py` | B12 | done(e64191d) — a key authenticates as a hidden, auto-created "principal" user (unusable password, excluded from the human Users list) added to the bound role's group, so it rides the exact same RBAC/scoping/audit path a human login uses — no parallel permission logic. `pytest` full suite green (1296 passed, 1 pre-existing skip), gate:all 00-02/04-17 green (gate03 N/A on B — no apps/web node_modules). FILE_14 stays open, not `_done` — Task B (Settings → Developers keys UI) + Task C (reference page) are apps/web, A's territory, unbuilt |
| B14 | Admin/system panel — Task A (backend endpoint) + Task C (tests) only — `TH/FILE_19` | B | `erp/monitoring/status_api.py` (new — `GET /api/system/status/`, admin-only), `config/urls.py` (mount), `config/settings/base.py` (`BACKUP_DIR`), `.env.example`, `erp/monitoring/tests/test_status_api.py` | B13 | done(HEAD) — version/uptime/DB+Redis latency/storage free space/Celery worker count+queue depth/backup freshness/env-var NAMES (set/unset only, values never serialized — asserted aggressively in tests), overall status rolls up the worst component. `pytest` full suite green (1304 passed, 1 pre-existing skip), gate:all 00-02/04-17 green (gate03 N/A on B — no apps/web node_modules). FILE_19 stays open, not `_done` — Task B (Settings → النظام UI page) is apps/web, A's territory, unbuilt |
| B15 | AI usage & cost page — Task A (read endpoint) + Task C (tests) only — `TH/FILE_20` | B | `erp/assistant/api/usage.py` (new — `GET /api/assistant/usage/?month=`, admin-only), `erp/assistant/api/urls.py` (mount), `erp/assistant/tests/test_usage.py` | B14 | done(HEAD) — straight aggregation over existing `Trace`/`Budget`/`SpendRollup` records, zero new tracking: month totals (requests, tokens in/out, cost microcents, cache-hit share, degraded-minutes), per-provider split, per-user table, budget-vs-consumed (org scope pairs its monthly `SpendRollup` row exactly; request/user-daily scopes expose config only — no monthly "consumed" figure invented for ceilings that reset per-call/per-day). Cost stays in microcents (same USD convention as `api/ops` — no EGP/FX conversion fabricated). `degraded_minutes` = exact count of distinct calendar-minutes with stored `routing.skipped` evidence, not a live-state estimate replayed onto the past. `pytest` full suite green (1318 passed, 1 pre-existing skip), gate:all 00-02/04-17 green (gate03 N/A on B — no apps/web node_modules; gate17 confirms the new route as non-breaking). FILE_20 stays open, not `_done` — Task B (Settings → AI page UI) is apps/web, A's territory, unbuilt |
| B16 | Draftable payments — `PendingPayment` (smart-import FILE_16 Task B follow-up) | B | `erp/sales/domain/models.py`+`services/pending_payments.py`, `erp/purchasing/domain/models.py`+`services/pending_payments.py`, `erp/imports/engine.py` (row-warning support), `erp/imports/adapters/{sales,purchasing}.py` (`receipts`/`payments`), both modules' `api/` (list/apply/discard/match) | B15 | done(d8ba38c) — backend + API + tests only; review screen is apps/web, Agent A's territory, unbuilt. Sub-project 2 (inventory opening) specced in `DESIGN_PENDING_PAYMENTS_AND_STOCK.md`, not yet built. |
| B17 | Reconciled inventory opening — `PendingStockEntry` (smart-import FILE_16 sub-project 2, follow-up to B16) | B | `erp/inventory/domain/models.py` (+migration), `erp/inventory/services/pending_stock.py`, `erp/imports/adapters/inventory.py` (`inventory_opening`), `erp/imports/adapters/accounting.py` (`inventory_double_booked` guard on `account_opening`), `config/settings/base.py` (`IMPORTS_DEFAULTS`), `erp/accounting/services/seeding.py` (COA `3110`) | B16 | done(d8904c8) — TDD throughout; `PendingStockEntry` posts to a dedicated suspense account (3110), never GRNI; new `MovementType.OPENING`; `account_opening` blocks with `inventory_double_booked` when an `inventory_opening` batch exists (checked via `erp.imports.models.ImportBatch`, no circular import into `erp.inventory`). `inventory_transactions` stays the documented, explicitly-descoped blocker. `FILE_16_FINANCE_ADAPTERS.md` renamed `_done` — nothing left to build against it. Review/apply screen is apps/web, Agent A's territory, unbuilt (mirrors B12–B16 precedent). Full regression (`erp/imports erp/inventory erp/accounting erp/sales erp/purchasing`) green (611 passed), gate:all 00-02/04-17 confirmed green (gate03 N/A on B — no apps/web node_modules). |
| A7 | Custom fields UI — `TH/FILE_12` | **B (cross-territory, founder-authorized 2026-07-18)** | `apps/web/src/pages/settings/**`, customer/item forms, unified table kit column model, `i18n/locales/ar.json`+`en.json`, `api/customFields.ts` (new client) | B9 (done) | done(HEAD) — Task A settings CRUD (entity picker, inline create/edit, up/down reorder via position swap — no drag, matches existing DashboardSettingsPage precedent, no new dependency), Task B (dynamic field rendering + client-side validation mirroring the backend on the customer/item CREATE forms only — no PATCH/edit endpoint exists for either base record today, so edit was out of scope), Task C (custom fields as extra table columns + non-empty detail facts; "saved views" in this codebase only persists filter query params, not a column set, so there is no column-picker to wire — drift noted, extra columns just render whenever active defs exist). Verified end-to-end against the real running API (not just tsc): created CHOICE/DATE/MONEY defs, position-swap reorder, deactivate-hides-but-keeps-old-values, required/choice validation error shapes — all matched the frontend code exactly. `node scripts/check-i18n-parity.mjs` + `npx tsc -b` + `python scripts/gates/gate03.py` all green. No browser was available in this session to visually drive the UI — data-contract verified at rung 2, not rung 3. |
| A9 | API keys + developer docs UI — `TH/FILE_14` Task B (keys settings page) + Task C (reference page) | A | `apps/web/src/pages/settings/ApiKeysPage.tsx` (new), `apps/web/src/api/apiKeys.ts` (new), `SettingsNav.tsx`, `App.tsx` route, `ar.json`/`en.json`; also built the missing HTTP surface B13 (Task A/D) never wired: `erp/identity/views.py` (`ApiKeysView`, `ApiKeyRevokeView`, `ApiDocsView` — the last reuses gate17's `_routes()` inventory so the reference page is generated, never hand-maintained), `erp/identity/urls.py`, `erp/identity/serializers.py` (`CreateApiKeySerializer`), `erp/identity/tests/test_api_key_views.py` (new, 6 tests: admin-only 403, create/list/revoke round-trip, unknown-role 400, unknown-key-on-revoke 404, docs admin-only) | B13 (done) | done(HEAD) — discovered B13 shipped model+service+tests but no view/url layer at all (every `/api/identity/api-keys*` request 404'd), so this session added that layer as necessary plumbing, matching the A8 precedent of fixing an integration gap found mid-build. Added Arabic lexicon entries for "API key"/"Developers" (Identity System §6, 2026-07-18) before the i18n keys, per the lexicon-first rule. Verified end-to-end in a real browser against the real running API (rung 3): created a System-Admin-role key, copied the one-time secret, confirmed it authenticated on `/api/sales/orders` (200), revoked it via the UI confirm dialog, confirmed the same secret now 401s. Reference panel renders the live route inventory (200+ routes) correctly. `pytest erp/identity` (83 passed) + i18n parity (1992 keys) + `tsc -b` + gate03 all green. Found and fixed an unrelated environment issue while cleaning up test data: the dev server on port 8020 (a stray local `vite.config.ts` proxy override, left untouched per founder instruction) had a stale Django process that hadn't picked up any of this session's code via autoreload — restarted it; also had to restart the vite dev server itself since `server.proxy` isn't hot-reloaded. Left the test API key + hidden principal user in the dev DB (already revoked, harmless) — cleanup via shell hit an unrelated pre-existing migration gap (`workflow_approval_request` table missing on that DB), not touched this session. Task A/D (backend) was B13, Task B/C (UI) is this session — all four tasks now done, file renamed `_done`. |
| B18 | Security hardening — `Docs/plan/00-security-hardening.md` (master-roadmap D5.P1.T1, off-queue but outranks feature work at any gap) | B | `erp/identity/scoping.py` (new), every module's list/detail API views (sales/purchasing/inventory/crm/accounting/einvoice/pricing) wrapped in `scope_queryset(...)`, `erp/workflow/adapters/egress.py` (new, SSRF guard) + `adapters/rest.py`, login-throttle on token-obtain view, `AUTH_PASSWORD_VALIDATORS`, import/backup file-handling limits, `manage.py check --deploy` cleanup. **Branch `feat/sec-hardening`** (plan's own name, not `feat/b-*` — pre-dates the lane convention; keep it, just push it). | none (unblocked, B idle after A7) | done(b503df7) — all 5 tasks were already merged into `feat/b-lane` from the 2026-07-02 session (scope enforcement, SSRF egress, auth hardening incl. memory-only JWT, import caps, CSP/`check --deploy`) and already re-verified once (2026-07-16, DECISIONS.md). B re-ran the suite on `feat/sec-hardening` anyway: 31 scope/egress/auth tests + 7 pricing import tests green, `check --deploy` clean. Zero code changes needed — no JWT-storage edit required, `apps/web/src/api/client.ts` untouched. `00-security-hardening.md` renamed `_done`. |
| A11 | Arabic-first User Guide + glossary — `TH/FILE_15` | A | `apps/web/src/help/content/journeys.ts` (new), `apps/web/src/help/content/glossary.ts` (new), `apps/web/src/pages/UserGuidePage.tsx`+`.css` (new), `apps/web/src/help/types.ts`, `apps/web/src/help/registry.ts`, `apps/web/src/help/content/platform.ts`, `App.tsx`, `AppMenu.tsx`, `CommandPalette.tsx`, `ar.json`/`en.json` | A10 (done) | done(733ec81) — checked dynamic-help rollout overlap first (erp-status: 12/77 guides, off critical path): confirmed no conflict — dynamic-help is the existing per-page contextual Live-tab checklist (`HelpCenter.tsx`/`HelpSignalsContext.tsx`), this is a separate standalone cross-page reference guide at `/help/guide`, both coexist untouched. Built 10 task-based journeys (create first invoice, receive goods, record payment, opening balances, trial balance, e-invoice, add user+role, take a backup, fix a rejected approval, ask the assistant safely) ar-first with "what can go wrong" pitfalls + related-page links, plus a 38-term glossary mirrored 1:1 from Identity System Sec6.1. Reachable three ways (Task C, mechanic-6 spirit): App Menu "User Guide" item, ⌘K "Help: <journey>" entries (10 new palette rows), direct route. All bundled TS content, zero images, works fully offline. `node scripts/check-i18n-parity.mjs` (2001 keys) + `npx tsc -b` + `python scripts/gates/gate03.py` all green. Verified end-to-end in a real running browser: journey content, glossary, ⌘K deep-links (accessibility-tree confirmed), App Menu item, related-link navigation, and full ar/RTL + en/LTR parity (language switched live, structure identical). `FILE_15_ARABIC_USER_DOCS.md` renamed `_done`. A's next unstarted file: TH FILE_16 (UX states batch), FILE_18 (Kanban pipeline), FILE_19 (admin panel UI), FILE_20 (AI usage UI), or SI FILE_12-15 (wizard/preview/adapter-review screens). |
| A12 | UX states batch: empty-state taxonomy + skeletons + `?` cheatsheet — `TH/FILE_16` | A | `apps/web/src/components/EmptyState.tsx`, `ErrorState.tsx`, `hooks/useAsync.ts`, `app/ShortcutsDialog.tsx`, `pages/inventory/StockOnHandPage.tsx`, `pages/UserGuidePage.tsx`+`.css`, 21 FilterBar list pages, `ar.json`/`en.json` | A11 (done) | done(HEAD) — audited first per the file's "Before You Start": no-data/no-match taxonomy was already correctly split across ~30 list pages (reused pattern, zero gap there), and the loading/skeleton primitive (`ListSkeleton`, reduced-motion honoured, independent per-pane use in `RecordTimeline`) was also already correct — zero gap. Real gaps found and fixed: (1) the no-match empty state had no actual "Clear filters" action (just a text hint) — extended `EmptyState.action` to accept `onClick` (not just `to`), added `filter.clearAll` key, batch-wired `action={{ onClick: () => setFilters([]) }}` into all 21 FilterBar pages that render `filter.noMatch`/`filter.noMatchHint`; (2) `StockOnHandPage` rendered a bare muted table-cell string instead of the designed component — converted to the same `EmptyState` no-data/no-match split as every other list page; (3) the no-permission variant didn't exist at all (RBAC failures fell through to the generic retry-styled `ErrorState`, which is misleading since retrying can't grant a role) — `useAsync` now exposes `errorStatus` (parsed from `ApiError.status`), `ErrorState` renders a calm blame-free lock-icon variant on `status === 403` with no Retry button, wired into 6 real admin/settings pages (RolesPage, UsersPage, ApiKeysPage ×2, WebhooksSettingsPage ×2, CustomFieldsPage, BranchesPage) as concrete proof — **not fan-out to the remaining ~50 `ErrorState` call sites this session** (infra is reusable, threading `status={errorStatus}` into the rest is a mechanical follow-up, not attempted here to stay in scope/budget); (4) the `?` cheat-sheet had drifted from the real keyboard hooks — `useListKeyboardNav` has Space=peek and `useRowSelection` has ⌘A=select-all, neither was listed — added both rows, plus the plan's required "one line in the help page points to it" (User Guide header now has a `?`-hint line with a button that calls `openShortcuts()` directly, verified opens the real dialog). Verified end-to-end in the real dev server: filtered a populated list to zero via URL params, confirmed the no-match `EmptyState` + its `.empty-state__action` button, clicked it, confirmed `setFilters([])` restored all rows; mocked a 403 on `/api/identity/roles` (temporary `window.fetch` patch, restored after) and confirmed the permission `ErrorState` renders with no Retry button; confirmed the cheat-sheet opens from the User Guide link and Escape closes it (twice). `node scripts/check-i18n-parity.mjs` (2009 keys) + `npx tsc -b` + `python scripts/gates/gate03.py` all green. `FILE_16_UX_STATES_BATCH.md` renamed `_done`. A's next unstarted file: TH FILE_18 (Kanban pipeline), FILE_19 (admin panel UI), FILE_20 (AI usage UI), or SI FILE_12-15 (wizard/preview/adapter-review screens). |
| A10 | List UX: peek audit + inline stage edit — `TH/FILE_17` | A | `apps/web/src/pages/crm/PipelinePage.tsx`, `apps/web/src/pages/crm/crm.css`, `ar.json`/`en.json` | A9 (done) | done(HEAD) — **peek audit (Task C): zero gap.** Every list page that renders a customer/supplier/item/warehouse/journal code already routes it through `EntityLink`/`PartyLink` (OrdersPage, PurchaseOrdersPage, EInvoicesPage, ItemsPage, BatchesPage, StockOnHandPage, CustomerPricingPage, MovementsTable, StockMovementPage) — the small hover-card "peek" pattern (`components/PeekCard.tsx`) is already universal on every page that has a peekable entity column. CRM list pages (Leads/Tickets/Pipeline) don't render customer/supplier/item codes as list columns at all, so there was nothing to wire there. **Inline edit (Task A/B): 3 of the plan's 4 named candidates had no service path and were dropped per the file's own STOP rule** — draft-document line qty/note (orders/quotations have no line-PATCH endpoint at all, only status transitions after create), lead owner (server-assigned, no set-owner endpoint), item reorder level (no update endpoint on `Item` exists anywhere in `api/inventory.ts`). The 4th, "lead stage", doesn't exist as a settable field on `Lead` either — substituted the real analog: **Opportunity.stage in the Pipeline list**, which already has `advanceStage(id, stage)` (the exact same endpoint `OpportunityDetailPage`'s "advance" button uses). Click the stage badge → native `<select>` limited to the 3 open stages (qualifying/proposal/negotiation) → optimistic flip + undo-window toast (`crm.toast.stageAdvanced`, already existed) → server 200 confirmed via network tab. Won/Lost rows never enter edit mode (won/lost is the separate, consequential win/lose flow) — clicking one shows a one-line reason toast (`crm.opp.stageClosed`, new key, ar+en). Cell affordance is `.crm-stage-cell`/`.crm-stage-edit` in `crm.css` — transparent border by default, `var(--color-border-strong)` on hover/focus-visible, no colour fill, confirmed via `getComputedStyle`. Verified end-to-end against the real running API (rung 3): flipped OPP-2026-000027 qualifying→proposal (`POST .../stage` 200), confirmed the closed-row toast fires with zero network call for OPP-2026-000001 (Won), then reverted the test row back to qualifying so the dev DB is unchanged. Native `<select>` open state hung the Browser pane's screenshot tool (known headless-Chrome limitation, unrelated to this code) — verified via `read_page`/`form_input`/`read_network_requests` instead of pixels. `node scripts/check-i18n-parity.mjs` (1993 keys) + `npx tsc -b` + `python scripts/gates/gate03.py` all green. `FILE_17_LIST_UX.md` renamed `_done`. |

- **A:** TH FILE_09 approval node → FILE_10 AI agent node (erp/workflow + canvas UI) →
  FILE_12 custom-fields UI (done — B took it directly, see A7) → SI FILE_12–14 wizard/preview/report
  UI → TH FILE_16–18 UX batch.
- **B:** TH FILE_13 activity timeline backend (done, B10) → SI FILE_15 all 5 adapters (done, B11) →
  SI FILE_16 finance adapters (done, B12 — journals + GL-opening only; payments + inventory-opening
  are documented blockers) → TH FILE_14 API keys backend (done, B13 — Task A+D only, keys UI/docs
  page deferred to A) → TH FILE_19 admin panel backend (done, B14 — Task A+C only, System page UI
  deferred to A) → TH FILE_20 AI usage/cost backend (done, B15 — Task A+C only, Settings → AI page
  UI deferred to A) → B16 draftable payments (done — see above) → B17 reconciled inventory opening
  (done — see above) → **B-lane now IDLE (2026-07-18 M3 sync).**

**M3 sync (2026-07-18, B session):** re-audited every plan folder pos 1–10 for undone (non-`_done`)
files. Pos 1–7 + ★agent-actions + os-foundations: fully `_done`. Pos 8 (delivery-readiness) FILE_07
sections C/D/E: founder + real customer machine only, not solo. Pos 9/10 (twenty-harvest,
smart-import): every remaining undone file is `apps/web` — A's territory exclusively (locale keys,
canvas UI, Settings pages). **Conclusion: B has zero eligible backend-only task left in the active
queue.** Ran full B-lane gate suite as a checkpoint sanity pass: gate:all 00-02/04-17 green on
`feat/b-lane` tip (gate03 N/A — no `apps/web/node_modules` on B), Redis/DB/venv healthy. No code
changes this session — docs-only sync. `main` has moved ahead via the standing E2E job (⟳) plus A
committing fix/test passes straight to main (`13358b2`, `c89de0e`, `83d4a59`, `96a517f`, `699a7c8`
— assistant language-adherence, mobile reliability); board/erp-status now reflect that tip.
**Drift noted for A:** `twenty-harvest/FILE_10_AI_AGENT_NODE.md` is done in substance (per
erp-status, `b832ba7`) but was never renamed `_done` on disk.
**B's next move (2026-07-18, A7 done):** the one-off `apps/web` hand-off is closed — A7 (TH
FILE_12 custom fields UI) shipped, plan file renamed `_done`. B returns to backend-only per the
ownership map; no unstarted backend-only twenty-harvest/smart-import file remains (per the M3
audit below) unless the founder opens new backend-only work. `apps/web/node_modules` now exists
in B's worktree (installed for A7) — harmless to leave, but B still has no standing reason to run
JS gates day-to-day.

**A8 done (2026-07-18, A session):** FILE_13 Task B/C (activity timeline tab UI + AI/import
source glyph) shipped — see A8 row above. FILE_13 fully `_done`.

**A9 done (2026-07-18, A session):** FILE_14 Task B/C (API keys settings page + reference docs
page) shipped — see A9 row above. FILE_14 fully `_done`.

**A10 done (2026-07-18, A session):** FILE_17 (peek audit — zero gap found — + Pipeline stage
inline edit) shipped — see A10 row above. FILE_17 fully `_done`. A's next unstarted file per the
ownership map: TH FILE_15 Arabic user docs (check overlap with the paused dynamic-help rollout
first) or FILE_16 UX states batch, then FILE_18 Kanban pipeline, FILE_19 admin panel UI,
FILE_20 AI usage UI, SI FILE_12-15 wizard/preview/adapter-review screens, or B16/B17 draftable-
payments + inventory-opening review screens.

**A7 follow-up (2026-07-18, same session):** founder delegated whether to widen custom-fields
scope beyond customer/item; B added `purchasing.supplier` as a third entity (Customer's exact
structural mirror — see DECISIONS.md "Custom fields: Supplier added as a third entity"), deliberately
stopped there (leads/orders stay out — scope brake). `erp/purchasing` suite green, i18n+tsc+gate03
green, live API round-trip verified. Commits `cca1093`/`ddacdce`, already an ancestor of
`origin/main` (tip `71d64d9` after A's subsequent merges/fixes). **B-lane still idle** — no new
backend-only task opened by this.

**B health check (2026-07-18, later same day):** ran `gate:all` on `feat/b-lane` tip (`ddacdce`,
= `origin/main` ancestor). 00–02 + 04–17 all PASSED. **Gate 03 FAILED** — main chunk
`index-*.js` 251.8 kB gzip > 250 kB budget (was green at A7's check). apps/web bundle-chunking,
A's territory (gate03 surface) — flagging here, not fixing; A is concurrently mid-session on
A8 (unpushed) so didn't touch the shared erp-status skill for this. Needs a route-split/
lazy-import pass whenever A picks it up.

**B18 reconciliation (2026-07-18, later session):** the B18 row above was added to `origin/main`
(`03fa32c`) after this branch had already split off and closed it out independently — same
conclusion reached twice in parallel (all 5 tasks pre-existing from the 2026-07-02 session,
commits 945f9ee/46010f1/84264a8/8e10b08/c446a9a/97af941/03f0216, re-verified 2026-07-16 and again
here: 31 scope/egress/auth + 7 pricing import tests green, `check --deploy` clean, zero code
changes). Merged `origin/main` into `feat/sec-hardening`, folded the result into the B18 row
above instead of leaving two write-ups. Pushed straight to `origin/main`.

**Gate17 snapshot was stale (2026-07-18, same session):** post-merge `gate:all` sanity pass found
`api_schema.json` hadn't been regenerated since `91da71a` — flagged `api/audit/history`'s
intentional replacement by `api/audit/timeline/` (TH FILE_13) as a false-positive break, and was
silently missing every route added since (custom fields, API keys, system status, AI usage,
pending payments/stock). Regenerated and committed (`98c8878`) — gate maintenance is B's
territory per the ownership map above. Gates 00–02, 04–17 all green on the merged tip; gate03
still red on the known pre-existing bundle-budget regression (253.2 kB gzip, A's territory).

**A7 pushed straight to `origin/main`** (2026-07-18, founder asked to see it on main): `feat/b-lane`
was a clean 1-commit fast-forward ahead of `origin/main`, so B pushed
`feat/b-lane:main` directly (remote ref only — **A's local `main` in `C:\AhmedGaid\ERP` was never
touched**, per the 2026-07-16 incident rule). `origin/main` tip is now `3a52111`. **A: `git pull`
(or fast-forward your local `main`) before your next task** — same pattern as the M2/M3 syncs.
Full `gate:all` (00–17) was NOT re-run for this push — zero backend files touched by A7, backend
`custom_fields` tests were already green and untouched, and the frontend gates
(parity/tsc/gate03) plus a direct API smoke test were already green pre-push. FILE_12 is not one
of twenty-harvest's designated merge-checkpoint files (those are FILE_07/13/21) — this merge was
user-requested, ahead of the plan's own checkpoint schedule.
- **M3:** TH Tier 2 merge after FILE_13; SI Phase-A demo merge after FILE_14. TH FILE_21 +
  SI FILE_17 acceptances run single-agent (Either) on merged main.

### Wave 4 — founder override, B takes the apps/web hand-off backlog (2026-07-18)

| ID | Task | Agent | Files/modules | Deps | Est | Checkpoint | Status |
|---|---|---|---|---|---|---|---|
| B19 | System settings page — `TH/FILE_19` Task B (consumes B14's `/api/system/status/`) | B | `apps/web/src/pages/settings/SystemPage.tsx` (new), `SettingsNav.tsx`, `App.tsx` route, `ar.json`/`en.json` | B14 (done) | 1 | M3 | todo |
| B20 | Settings → AI usage page — `TH/FILE_20` Task B (consumes B15's `/api/assistant/usage/`) | B | `apps/web/src/pages/settings/AiUsagePage.tsx` (new), `SettingsNav.tsx`, `App.tsx` route, `ar.json`/`en.json` | B15 (done) | 1 | M3 | todo |
| B21 | Import wizard/preview UI — `SI/FILE_12`–`FILE_14` | B | `apps/web/src/pages/imports/**` (new), `api/imports.ts`, `ar.json`/`en.json` | B7 (done) | 2–3 sessions (one FILE each) | Phase A demo point (SI FILE_14) | todo |
| B22 | Document/finance adapter review screens — `SI/FILE_15`–`FILE_16` UI half | B | `apps/web/src/pages/imports/**` (adapter preview + finance suspense-approval panel) | B11, B12 (done) | 1–2 | M3 | todo |
| B23 | Draftable payments review screen — B16 follow-up (apps/web half) | B | `apps/web/src/pages/sales/**`, `apps/web/src/pages/purchasing/**` (pending-payment review/apply), `ar.json`/`en.json` | B16 (done) | 1 | M3 | todo |
| B24 | Reconciled inventory-opening review screen — B17 follow-up (apps/web half) | B | `apps/web/src/pages/inventory/**` (pending-stock review/apply), `ar.json`/`en.json` | B17 (done) | 1 | M3 | todo |

Order within Wave 4 (B's own judgment on resequencing if a dep surfaces): B19 → B20 → B21 → B22 →
B23 → B24. Each is one plan-file scope, one session, gates green, rename `_done`, flip this row,
push, before starting the next.

**A13 (2026-07-19, A session):** twenty-harvest `FILE_21_ACCEPTANCE.md` — **partial pass, not
renamed `_done`.** Full checklist state + verification method per item is in the plan file's own
"Session progress" section. Headline: Tier 1 mostly clean (upgrade no-op, gate16/17, webhooks via
test suite); real gaps found — CHANGELOG stale since v1.0.0, RUNBOOK gate-count stale (says 00–13,
actual 00–17), both B's territory (core infra/gates row), not fixed by A. Tier 2/3 spot-checked
(System panel + AI usage page + Kanban live-verified; rest relied on each item's own prior rung-3
verification). **Session cut short by a lane collision** — mid-session, Agent B was found actively
writing to this checkout (`C:\AhmedGaid\ERP`) instead of `C:\AhmedGaid\ERP-B`, exactly the
2026-07-16 incident pattern; full writeup in `DECISIONS.md` ("Lane collision" entry, 2026-07-19). A
deferred the Playwright suite and a second full `gate:all` run to limit further shared-DB exposure.
**Remainder for a follow-up FILE_21 session:** Playwright suite, saved-views on 2 more pages,
live Kanban drag+RTL check, the visual conductor-brand feel checklist (screenshot tool was
unreliable this session). Did not touch erp-status skill this session (B had just written to it
mid-session, not at a merge checkpoint — avoided adding a second concurrent writer to that file).

**A15 (2026-07-20, A session, browser-tooled):** `twenty-harvest/FILE_21_ACCEPTANCE.md` follow-up
— closed 4 of the 5 remainder items A13 left open: Playwright suite (16/16 green), saved views
live-verified on 2 more pages (Purchase Orders, Inventory Stock-on-hand — full save/set-default/
delete round trip, both cleaned up), Kanban drag-drop verified end-to-end in LTR and RTL (real
API round trip via dispatched DOM drag events since the Browser pane's native drag tool needs a
working screenshot first and that tool still times out; reverted both test moves), brand-feel
checklist run at the computed-style/DOM level (monochrome chrome, one type voice, one icon hand,
Latin digits under Arabic, designed empty states, reduced-motion CSS — all confirmed; not a
pixel/screenshot pass). One self-inflicted false alarm: running Playwright against the shared
dev DB while the browser tab was open threw transient 500s on Purchase Orders — a Retry click
cleared it, no real bug. **File still not `_done`** — the 5th item (CHANGELOG stuck at v1.0.0,
RUNBOOK gate-count stale) is B's territory, untouched. Commit `a4b7670`.

**A14 (2026-07-19, same A session):** `brand-philosophy-review` Session A (app frame + global
states) — spot-check pass, not the full matrix. Both systemic findings seeded in the scorecard
(no error boundary, no code-splitting) are **already fixed** (confirmed in source:
`AppErrorBoundary` wraps the router root, `lazy()` used for routes) — updated scorecard from
"known gap" to "fixed". New finding: notification panel doesn't localize digest content to the
viewer's language (Arabic summary text shown while UI language = English) — logged as P2 in
`Docs/plan/brand-philosophy-review/scorecard.html`, candidate fix lives in the notification
generation service (`erp/notifications`), not the frontend. Did not touch any B-owned path — this
plan folder is read-only-review + its own static `scorecard.html`, zero product-code edits, chosen
specifically because B's own harness can't run it (no browser tooling, per B's erp-status banner)
so there's no scope overlap risk. File left open (not `_done` — no per-session done convention for
this plan; sessions B–H remain). Restored UI language to Arabic before ending.

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
