# PROJECT STATUS — Conductor ERP (Django)

> Living resume anchor — current state only; `/erp-resume` reads this file. Keep it lean (< 200 lines).
> Full stage/phase/commit history → **`erp-history`** skill. apps/web conventions → **`erp-frontend`**
> skill. "Is this on-brand?" → **`conductor-brand`** skill. **Last updated: 2026-06-28.**

## What this project is
Customer-hosted, single-tenant **Django modular-monolith ERP** (Python 3.13 + DRF) + React/TS/Vite
SPA, **Arabic/RTL-first**. Product **"Conductor"**. Built foundation-first, then modules (Accounting →
Inventory → Sales → Purchasing → CRM). Strict per-module layout `{api,domain,services,repositories,
contracts,events,tests,docs}`; cross-module calls only via public `contracts/` (gate-enforced). Money
is always integer minor units + currency.

## Current position
**Roadmap COMPLETE — release candidate.** All five modules + accounting/ops depth + VAT (output+input)
+ ETA e-invoicing + report builder/exports + notifications + full RBAC + Phase 10 hardening + Phase 11
deployment packaging delivered. **`gate:all` spans 00–13, all GREEN. No active blocker.**
The Linear-quality frontend UX overhaul (speed/optimistic, keyboard-first, designed states, density,
inline-edit, palette recents, brand triad + Arabic search) is **merged to `main`** (PRs #1–#11).
Repo `C:\AhmedGaid\ERP` (git), pushed to `github.com/ahmedGaid/Conductor_ERP`.

## Active work — Growth (branch `growth/combined`)
Strategy pivot (2026-06-26, `GROWTH_PLAN.md`): postpone AI, win on **speed + one-day self-serve setup**.
Pitch: *"Sign up in the morning, send your first real invoice before lunch."* Phases (terse — detail in
`DECISIONS.md` / commit messages):
- **Phase 1 Setup Wizard — DONE.** First-run gate + `POST /setup/*` group; one-click COA, company
  profile, tax/e-invoice toggle, invite-team, Finish → Dashboard "what to do next" checklist. Plus the
  chrome identity rework (workspace chip / UserMenu / AppMenu) and Phase 1.5 Docker backup/restore.
  Bundled in **PR #14 → `main`** (open).
- **Phase 2 CSV import — DONE** (merged into `growth/combined`): generic importer `erp/core/imports.py`
  + `ImportDialog`, live on Customers / Suppliers / Items (FK resolution, choice/decimal validation,
  template download). Eyes-on verified.
- **Phase 3.0 friction walk — DONE.** Quote→SO→Invoice→e-invoice→paid walked; friction list in
  `DECISIONS.md`. **3.1 smart defaults — DONE** (`lib/lastUsed.ts` + `useSmartDefault`, qty defaults 1).
- **Pricing engine (3.1b) — Oracle-EBS-core model, P1–P4 DONE.** Decision + design in `DECISIONS.md`.
  `erp/pricing/` app: price lists + tiers, per-customer assignment/overrides, effective dates,
  tax-inclusive, precedence resolver. API under `/api/pricing` + `GET /resolve` (backs VAT out).
  Management UI (Pricing section), order/quotation line price-prefill from `/resolve`, and **P4** bulk
  price-list-line CSV import + STANDARD demo seed. Latest commit **`4399ca4`** (this session) bundles
  P4 with the module-identity + party-drill-down work below.
- **Module identity + party drill-down — DONE this session (`4399ca4`).** `ModuleHeader` (monochrome
  wayfinding: module glyph + breadcrumb + accent bar; identity by icon+place, not chrome colour) on
  sales/purchasing/accounting detail pages. `PartyLink`/`PartyDetailView` → Customer/SupplierDetailPage
  (summary + transactions + ledger). `JournalEntry` gained a `party` field (migration 0011); posting
  records it from sales/purchasing orders; GeneralLedger filters by party. i18n 1161 keys.

### NEXT ACTION
**Pricing P5:** per-customer assignment + item-override management UI, effective-date scheduling,
tax-inclusive entry affordance (API + resolver already support it). Then decide PR/merge path for
`growth/combined` → `main`. Working tree after `4399ca4` is clean except local-only artifacts
(`erp_questionnaire_v4.html`, `Docs/`, `Images/`, `.claude/`, `project_context.md`).

> **GATE NOTE:** root `npx tsc --noEmit` under-checks (skips the project-referenced tsconfig). Use
> **`npx tsc -b` from `apps/web`** as the true typecheck; `npm run build` = `tsc -b && vite build`.

## Verify / gates
- **Python suite** (backend source of truth): from repo root
  `.\.venv\Scripts\python.exe scripts\gates\_run.py all` (00–13; or a single `NN`). Green = approval to
  advance. React-touching gates (03/04/05) build the frontend — need Node + `apps/web` `npm install`.
  If a deliberate UX move trips a UI-placement gate, update the gate to the new intent.
- **apps/web JS checks** (no Python gate; NO JS unit runner): from `apps/web`
  `node scripts/check-i18n-parity.mjs` (ar/en parity) + `npx tsc -b`.

## Active blocker → none
Redis runs as the auto-start **`Redis`** service (winget `Redis.Redis`; Memurai abandoned — see
DECISIONS.md). Only common post-reboot hiccup is the service not starting:
```
Get-Service Redis
& 'C:\Program Files\Redis\redis-cli.exe' ping   # expect PONG; if stopped: Start-Service Redis
```

## Environment facts (local dev)
- Python venv: `C:\AhmedGaid\ERP\.venv\Scripts\python.exe` (3.13). Manage cmds:
  `.\.venv\Scripts\python.exe manage.py <cmd>` (settings `config.settings.dev`).
- PostgreSQL 16: service `postgresql-x64-16`; superuser `postgres`/`postgres`; app DB `erp`, role
  `erp`/`erp` (CREATEDB for pytest). psql at `C:\Program Files\PostgreSQL\16\bin\psql.exe`.
- Redis: `redis://localhost:6379/0`; `redis-cli` at `C:\Program Files\Redis\redis-cli.exe`.
- Node 24 + npm 11. `.env` at repo root (gitignored) has DATABASE_URL/REDIS_URL.

## Run the app (live demo)
```
cd C:\AhmedGaid\ERP
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_identity      # demo users (admin/manager/accountant/auditor, pw Dev12345!)
.\.venv\Scripts\python.exe manage.py seed_accounting    # baseline COA + fiscal year + 12 periods
.\.venv\Scripts\python.exe scripts\seed_demo.py         # demo Sales/Purchasing/CRM data (standalone; run after the seeds)
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
cd apps\web; npm install; npm run dev                    # frontend :5173, proxies /api -> :8000
```
Sign in at http://localhost:5173 as `admin` / `Dev12345!` (`run-dev.ps1` starts both). Light/dark
toggle in the command bar; Arabic/RTL default.

## Pointers
- Build history + commit map → **`erp-history`** skill.
- apps/web conventions + UX patterns + JS gates → **`erp-frontend`** skill.
- Decisions & rationale → `DECISIONS.md` · Growth strategy → `GROWTH_PLAN.md`.
- Roadmap/plan: `C:\Users\Rw\.claude\plans\cd-c-ahmedgaid-erp-files-read-thosse-bubbly-puddle.md`
  (RBAC increments: `…\plans\happy-napping-jellyfish.md`).
- Operator runbook → `Docs\RUNBOOK.md` · Source specs (input only) → `C:\AhmedGaid\ERP\files\`.
</content>
</invoke>
