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
| B3 | `manage.py upgrade` — `twenty-harvest/FILE_02` | B | erp/core models+migration, upgrade command, tests, RUNBOOK §upgrade | B2 | 1 session | M1 | todo |
| B4 | gate16 drill + gate17 API snapshot — `twenty-harvest/FILE_03` | B | `scripts/gates/gate16.py`, `gate17.py`, `_run.py`, snapshot | B3 | 1 session | M1 | todo |

**M1 (sync):** merge A1 + B1–B4 to main → `gate:all` 00–17 green → **D7 = HANDOVER GATE**
(`delivery-readiness/FILE_07`): founder + Either agent, dev dry run then real customer box.
A2/A3 merge at M1 if ready, else M2 — they never block the gate.

### Wave 2 — post-gate (fully parallel lanes)

| ID | Task | Agent | Files/modules | Deps | Est | Checkpoint | Status |
|---|---|---|---|---|---|---|---|
| A4 | Saved views backend — `TH/FILE_06` | A | erp/core SavedView model+API (**coordinate: B is out of erp/core after B4**) | M1 | 1 | M2 | todo |
| A5 | Saved views UI — `TH/FILE_07` | A | apps/web list pages, ar/en.json | A4 | 1 | **M2 = TH Tier 1 merge** | todo |
| A6 | ⌘K actions — `TH/FILE_08` | A (started ahead of A5 — founder override, palette/registry/role-filter/context-inject already shipped by unified-ui; this session found+fixed a duplicate-action bug across 5 detail pages) | apps/web command menu | A5 | 1 | M3 | done(32c054b) |
| B5 | Auto-masters — `SI/FILE_08` | B | erp/imports | M1 (queue priority only — may start early if B-lane idles in wave 1) | 1 | M2 | todo |
| B6 | Execution engine — `SI/FILE_09` | B | erp/imports | B5 | 1 | M2 | todo |
| B7 | Background runner — `SI/FILE_10` | B | erp/imports + Celery task | B6 | 1 | **M2 = SI engine merge** | todo |
| B8 | Import API — `SI/FILE_11` | B | erp/imports/api | B7 | 1 | M3 | todo |

### Wave 3+ — continuation by ownership (summarized; scope = each plan file, as written)

- **A:** TH FILE_09 approval node → FILE_10 AI agent node (erp/workflow + canvas UI) →
  FILE_12 custom-fields UI (needs B's FILE_11) → SI FILE_12–14 wizard/preview/report UI →
  TH FILE_16–18 UX batch.
- **B:** TH FILE_11 custom-fields backend (JSONB on Customer+Item) → TH FILE_13 activity
  timeline backend → SI FILE_15/16 document+finance adapters → TH FILE_14 API keys, FILE_19
  admin panel backend.
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
