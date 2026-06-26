# PROJECT STATUS — Conductor ERP (Django)

> Living resume anchor — current state only. The `/erp-resume` skill reads this file.
> Keep it lean (< 200 lines); the full stage/phase/increment build log is archived in the
> **`erp-history`** skill, and apps/web conventions live in the **`erp-frontend`** skill.
> **Last updated: 2026-06-26.**

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
**Both PRs merged to `main`** (PR #1 `ui/speed-optimistic` → `1103010`; PR #2 `ui/density-typography`
→ `af045f8`). apps/web only — the Python `gate:all` is untouched. A focused pass to lift the React UI
to Linear's bar (fast, calm, keyboard-driven), worked one priority area at a time. Full patterns +
primitives → **`erp-frontend`** skill. (Merged branches still exist on origin; safe to delete.)

- **Speed — DONE** (`5ae900e`): `lib/optimistic.ts` (`runOptimistic`/`optimisticCreate`), `lib/prefetch.ts`
  (hover-prefetch), `ToastContext`/`Toaster`. Optimistic mutations + toasts + hover-prefetch across all ~32 pages.
- **Low-friction creation — DONE** (`5ae900e`+`a8b5aa0`): 9 list-creates → optimistic insertion; 12
  navigate-away/inline create forms → success toast (survives navigation) + errors via toast, validation inline.
- **Keyboard-first — DONE**: Slice 1 (`50a37a2`) global shortcut layer (`useGlobalShortcuts`:
  `g`+key nav, `/`, `c`, `?` cheat-sheet) on top of the existing ⌘K palette; Slice 2 (`514d6f2`)
  route-change focus to the page heading; sidebar shortcut tips (`65f860b`, `Tooltip.shortcut`);
  Slice 3 (`00232f7`) `j`/`k`/`Enter` list navigation (`useListKeyboardNav` + `lib/keyboard.ts`
  shared guards) wired across all 11 index→detail lists + "Lists" cheat-sheet section; Slice 4
  (`124cd05`) `useFormKeys` — **⌘/Ctrl+Enter submit + Esc cancel** across all 5 full-page create
  forms (order, quotation, PO, PR, journal) + "Forms" cheat-sheet section.
- **Brand + Arabic search — DONE this session** (`f5f1396`, `b2daf82`): added the `Docs/Brand` triad
  (Brief · Directive · new **Visual Identity System**), lean root `CLAUDE.md`, and the `conductor-brand`
  skill (recalled by `/erp-resume` + `erp-frontend`). **Arabic-insensitive search folding**
  (`lib/arabicSearch.ts` → `normalizeSearch`) wired into ⌘K / list filters / user search, so "امر البيع"
  finds "أمر البيع" (display text keeps full orthography). Lexicon calls — warehouse → **مخزن**, approve →
  **موافقة** (اعتماد unified) — landed with the Slice 4 i18n commit (`124cd05`).
- **Designed states — DONE**: all three cold-state primitives now exist + applied consistently —
  `EmptyState`, `ErrorState` (retry wired to the loader `reload`, `b2cd887`), and `ListSkeleton`
  (`20e0ef7`) which replaced the inline page-skeleton blob copy-pasted across 49 pages (net −255 lines,
  a11y label now everywhere). Plus the tooltip key-cap colour fix (`fcc4ff2`).
- **i18n: 1023 keys** (ar/en parity). Branch commits newest→oldest: `20e0ef7 b2cd887 c2aa1ca 124cd05
  7f9d489 f5f1396 b2daf82 fcc4ff2 55fac56 00232f7 4a380a1 65f860b 514d6f2 50a37a2 a8b5aa0 5ae900e`
  (pushed; **PR #1** open → `main`: github.com/ahmedGaid/Conductor_ERP/pull/1).
- **Density/typography — DONE** (PR #2, merged `af045f8`): `25a3302` — `--line-height-heading` (1.25)
  for crisp titles + token-driven table density (`--table-pad-inline/-block`) unified across all 9
  module tables (accounting outlier fixed; canonical density now a one-line token flip). Dashboard
  widget table left compact. `88fe4b0` — form-control density (`--field-pad-inline/-block`, built on
  `--space-*`) so inputs/selects/textareas tighten with compact mode too. List/detail vertical rhythm
  already token-driven.

- **Command-palette recents + inline-edit — DONE** (PR #3, **merged `cddd04f`**; commits `ce30535`→`8fe0dc5`):
  - **Palette recents** (`ce30535`): ⌘K with an empty query surfaces recently-visited pages at the top
    under a "Recent" group (`lib/recents.ts` localStorage MRU; recorded by the always-mounted palette
    via `useLocation`). +`command.groupRecent`.
  - **Inline-edit** (`b7e13d4`, redesigned `8fe0dc5`): reusable `InlineEdit` wired to the user detail
    page's **job title + phone**. Reads as a **bordered input box** with a **placeholder suggestion**
    when empty (discoverable, no hover-to-find); display↔input share metrics so no jump; Enter/⌘Enter
    commit, Esc revert, blur commit. Optimistic save via the page's `saveField()` with a **"Saved"**
    toast on success (dropdowns stay silent). **Backend touched (authorized):** `UpdateUserSerializer`
    + `update_user` now accept `job_title`/`phone` (stored on `UserPreferences`, blank clears) over the
    existing `PATCH /identity/users/{id}`; no migration (fields pre-existed); new `test_users` test.
    +`common.editField/saved`, +`admin.detail.*Placeholder`. **`gate:all` (00–13) GREEN.**
  - `1116f54` fixes a palette type error that only `tsc -b` (the real build) caught — see gate note below.
- **Inline-edit extended + focus polish — DONE** (PR #4, **merged `f059381`**; `74a3ef0`): **display
  name** is now inline-editable too (Profile "Name" row, same `saveField`+toast). Backend:
  `update_user`/serializer also accept `display_name` (UserPreferences; blank → falls back to username);
  `test_users` covers it. `InlineEdit` now **returns focus to the field trigger after a keyboard
  commit/cancel** (Enter/Esc), while a blur-commit leaves focus where the user moved it.
  +`admin.detail.namePlaceholder`. **`gate:all` (00–13) GREEN** (1029 keys).
- **Linear polish pass (3 slices) — DONE** (PR #5, **merged `1edef42`**; `27c9963 483ce5c caaa5b8`):
  (1) **palette depth** — ⌘K keeps the arrow-highlighted row scrolled into view; (2) **motion** — audit
  found the system already token-clean except one stray; tokenized the skip-link transition;
  (3) **micro-states** — j/k-selected list rows get a distinct monochrome leading marker (inset shadow,
  direction-aware) so the keyboard cursor reads differently from a mouse hover.
- **"Things 3" craft pass (5 PRs, #6–#10) — DONE** (frontend-only; Python `gate:all` untouched). Eight
  Things-3 brand principles → independently-shippable PRs:
  - **#6 one obvious action** (`134abe4`): order/PO detail showed two primaries in the draft+approval
    state (actionable Approve + a *disabled* Confirm, both `btn--primary`). Confirm is now primary only
    when actionable; otherwise a neutral disabled preview — one obvious primary per state.
  - **#7 list cursor + scroll restore** (`lib/listCursor.ts`): opening a row then returning now restores
    the keyboard highlight (if its row still exists) + scroll position, per route in sessionStorage.
    `useListKeyboardNav` gained opt-in `persistKey`+`getItemId`; wired the 5 high-traffic lists.
  - **#8 settled confirmation beat**: success toasts draw a monochrome check in over the existing
    `toast-in` (decelerating, no bounce; reduced-motion collapses it). No button "working" state —
    optimistic actions vanish on commit, so it would never render.
  - **#9 spacing rhythm**: snapped the off-scale, density-frozen `*-meta__row` gaps (`0.125rem`) onto
    `var(--space-1)` to match the summary-item rhythm. Deliberately surgical (no blind token churn).
  - **#10 Arabic nativeness**: lexicon audit found `ar.json` clean except the **approve** concept —
    six اعتماد-root stragglers (incl. a `مُعتمَد` next to `بانتظار الموافقة` in one block) unified onto
    the موافقة root (§6.1, 2026-06-23): `اعتمدها`→`وافق عليها`, `مُعتمَد`→`مُوافَق عليه`. 1029 keys.

### NEXT ACTION
PRs #1–#10 are **merged to `main`**; working tree clean (only the unrelated `erp_questionnaire_v4.html`).
Open options: **eyes-on spacing/rhythm tuning** at both densities (the one pass that needs a browser, not
blind edits); more inline-edit fields (each needs a small backend PATCH opening); deeper palette work
(recent *items*, scoped actions); broaden list-cursor restore + the success-check beat to the remaining
lists/screens.

> **GATE NOTE (important):** the documented apps/web check `npx tsc --noEmit` at the repo root
> **under-checks** — it doesn't traverse the app's project-referenced tsconfig, so it passed code that
> the real build `tsc -b` (run by `gate03`) rejected. **Use `npx tsc -b` from `apps/web` as the true
> typecheck** before claiming green. (The `erp-frontend` skill now documents `tsc -b`; `npm run build`
> = `tsc -b && vite build` for full certainty before a PR.)

## How to resume
1. Read this file (live state) + recall **`erp-history`** / **`erp-frontend`** skills as needed.
2. Clear any blocker (Redis after a reboot — see below), then continue from NEXT ACTION.
3. To continue the frontend work: `git checkout ui/inline-edit` (latest local branch; off `main`).
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
