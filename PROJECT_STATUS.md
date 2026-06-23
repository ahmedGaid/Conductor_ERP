# PROJECT STATUS — Conductor ERP (Django)

> Living resume anchor — current state only. The `/erp-resume` skill reads this file.
> Keep it lean (< 200 lines); the full stage/phase/increment build log is archived in the
> **`erp-history`** skill, and apps/web conventions live in the **`erp-frontend`** skill.
> **Last updated: 2026-06-22.**

## What this project is
Customer-hosted, single-tenant **Django modular-monolith ERP** (Python 3.13 + DRF), React + TS
frontend, **Arabic/RTL-first**. Product name **"Conductor"**. Built foundation-first, then ERP modules
(Accounting → Inventory → Sales → Purchasing → CRM). Strict per-module layout
`{api,domain,services,repositories,contracts,events,tests,docs}`; cross-module calls go **only via
public `contracts`** (boundaries enforced by gates). Money is always integer minor units + currency.

## Current position
**Roadmap COMPLETE — release candidate.** All five priority modules (Accounting, Inventory, Sales,
Purchasing, CRM) + accounting/operational depth + VAT (output+input) + ETA e-invoicing + report
builder/exports + notifications + the full RBAC system + Phase 10 hardening + Phase 11 deployment
packaging are all delivered. **`gate:all` spans 00–13, all GREEN.** No active blocker.

Repo: `C:\AhmedGaid\ERP` (git, `main`), pushed to `github.com/ahmedGaid/Conductor_ERP`.
For how any piece was built (and the commit that delivered it) → recall the **`erp-history`** skill.

## Active work — Linear-quality frontend UX overhaul
**Branch `ui/speed-optimistic`** (off `main`, pushed, NOT yet merged/PR'd). apps/web only — the Python
`gate:all` is untouched. A focused pass to lift the React UI to Linear's bar (fast, calm,
keyboard-driven), worked one priority area at a time. Full patterns + primitives → **`erp-frontend`** skill.

- **Speed — DONE** (`5ae900e`): `lib/optimistic.ts` (`runOptimistic`/`optimisticCreate`), `lib/prefetch.ts`
  (hover-prefetch), `ToastContext`/`Toaster`. Optimistic mutations + toasts + hover-prefetch across all ~32 pages.
- **Low-friction creation — DONE** (`5ae900e`+`a8b5aa0`): 9 list-creates → optimistic insertion; 12
  navigate-away/inline create forms → success toast (survives navigation) + errors via toast, validation inline.
- **Keyboard-first — IN PROGRESS**: Slice 1 (`50a37a2`) global shortcut layer (`useGlobalShortcuts`:
  `g`+key nav, `/`, `c`, `?` cheat-sheet) on top of the existing ⌘K palette; Slice 2 (`514d6f2`)
  route-change focus to the page heading; sidebar shortcut tips (`65f860b`, `Tooltip.shortcut`);
  Slice 3 (`00232f7`) `j`/`k`/`Enter` list navigation (`useListKeyboardNav` + `lib/keyboard.ts`
  shared guards) wired across all 11 index→detail lists + "Lists" cheat-sheet section.
- **i18n: 1017 keys** (ar/en parity). Branch commits newest→oldest: `00232f7 65f860b 514d6f2 50a37a2 a8b5aa0 5ae900e`.

### NEXT ACTION
**Keyboard-first Slice 4** — form key conventions: **Esc to cancel**, **⌘/Ctrl+Enter to submit** across
the create/edit forms (reuse the `lib/keyboard.ts` guards). After that, the remaining Linear priority areas.

## How to resume
1. Read this file (live state) + recall **`erp-history`** / **`erp-frontend`** skills as needed.
2. Clear any blocker (Redis after a reboot — see below), then continue from NEXT ACTION.
3. To continue the frontend work: `git checkout ui/speed-optimistic`.
4. Keep this file current as steps complete (and let the `erp-history` skill absorb anything historical).

## Verify / gates
- **Python suite** (source of truth for backend): from repo root
  `\.venv\Scripts\python.exe scripts\gates\_run.py all` (00–13; or a single `NN`). Green = approval to
  advance (no separate sign-off). React-touching gates (03/04/05) build the frontend — need Node + an
  `apps/web` `npm install`. If a deliberate UX move trips a UI-placement gate, update the gate to the new intent.
- **apps/web JS checks** (no Python gate covers them; NO JS unit runner): from `apps/web`
  `node scripts/check-i18n-parity.mjs` (ar/en parity) + `npx tsc --noEmit`.

## Active blocker → none
Redis runs as the auto-start **`Redis`** service (winget `Redis.Redis` port; Memurai abandoned — see
DECISIONS.md), so `gate:00` is green. Only common post-reboot hiccup is the service not having started:
```
Get-Service Redis
& 'C:\Program Files\Redis\redis-cli.exe' ping   # expect PONG
# if stopped: Start-Service Redis
```

## Environment facts (local dev)
- Python venv: `C:\AhmedGaid\ERP\.venv\Scripts\python.exe` (3.13). Manage cmds:
  `\.venv\Scripts\python.exe manage.py <cmd>` (settings `config.settings.dev`).
- PostgreSQL 16: service `postgresql-x64-16`; superuser `postgres`/`postgres`; app DB `erp`, role
  `erp`/`erp` (CREATEDB for pytest). psql at `C:\Program Files\PostgreSQL\16\bin\psql.exe`.
- Redis: `redis://localhost:6379/0`; `redis-cli` at `C:\Program Files\Redis\redis-cli.exe`.
- Node 24 + npm 11 (frontend). `.env` at repo root (gitignored) has DATABASE_URL/REDIS_URL.

## Run the app (live demo)
```
cd C:\AhmedGaid\ERP
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_identity      # demo users (admin/manager/accountant/auditor, pw Dev12345!)
.\.venv\Scripts\python.exe manage.py seed_accounting    # baseline COA + current fiscal year + 12 periods
.\.venv\Scripts\python.exe scripts\seed_demo.py         # demo Sales/Purchasing/CRM data (standalone script; run after the two seeds)
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
cd apps\web; npm install; npm run dev                    # frontend :5173, proxies /api -> :8000
```
Sign in at http://localhost:5173 as `admin` / `Dev12345!`. (`run-dev.ps1` starts both servers together.)
Sections: Dashboard, Sales, Purchasing, Inventory, Accounting, E-invoicing, CRM, Workflows,
Notifications, Settings, Admin (Users/Roles). Light/dark toggle in the command bar; Arabic/RTL default.

## Pointers
- Full build history + commit map → **`erp-history`** skill.
- apps/web conventions + UX patterns + JS gates → **`erp-frontend`** skill.
- Roadmap/plan: `C:\Users\Rw\.claude\plans\cd-c-ahmedgaid-erp-files-read-thosse-bubbly-puddle.md`
  (RBAC increments: `…\plans\happy-napping-jellyfish.md`).
- Decisions & rationale: `C:\AhmedGaid\ERP\DECISIONS.md` · Completion plan: `COMPLETION_PLAN.md` ·
  Operator runbook: `Docs\RUNBOOK.md` · Source specs (input only): `C:\AhmedGaid\ERP\files\`.
