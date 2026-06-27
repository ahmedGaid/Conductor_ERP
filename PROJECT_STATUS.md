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

## Active work — Growth Phase 1: self-serve Setup Wizard
Strategy pivot (2026-06-26, see `GROWTH_PLAN.md`): **postpone AI, win on speed + one-day self-serve
setup.** Pitch: *"Sign up in the morning, send your first real invoice before lunch."* Building the
first-run **Setup Wizard** so a brand-new org can set itself up with no seed script. Branch
`growth/setup-wizard` (off `main`, pushed). Backend `erp/setup/` (wraps existing seed/COA/tax/user
services, SYSTEM_ADMIN-gated); frontend `apps/web/src/pages/SetupWizardPage.tsx`. `gate:all` (00–13)
GREEN. **PR open → `main`: github.com/ahmedGaid/Conductor_ERP/pull/14** (bundles Setup Wizard 1.0–1.6
+ chrome identity rework + Phase 1.5 backup/restore).
- **1.0** first-run gate + `POST /setup/*` group + route guard (`53415ec`).
- **1.2** one-click chart of accounts (reuses `seed_accounting`) (`57a68a8`).
- **1.3** company profile → writes to the same OrgPreferences edited later in Settings (`fbc2d36`).
- **1.4** tax step — VAT rate + e-invoicing toggle (`e127dbd`).
- **1.5** invite-team step — `POST /setup/users` wraps identity `create_user`; status now carries
  `available_roles`; optional step shows each invitee's one-time temp password. Reuses the lexicon
  `admin.invite.*` labels. 11/11 setup tests; i18n 1057 keys. (`d7e96e3`)
- **1.6** Finish → Dashboard "what to do next" checklist. Frontend-only `GettingStarted` panel on the
  Dashboard (Finish already lands there via `LandingRedirect`): 5 steps (company profile, COA, first
  customer, first product, first order) that auto-check off real data (defensive module-list fetches,
  like the attention panel), admin-only, dismissible, and self-retiring once all done. i18n 1065 keys.
  **Phase 1 (Setup Wizard) COMPLETE.**
- **Chrome identity rework (`3661c34`, on `growth/setup-wizard`):** the app frame's identity surfaces
  split into three tiers — a **workspace/company chip** at the sidebar foot (`SidebarIdentity` → org
  settings + admin; shows `company_name`, collapses to its initial in the compact rail), a personal
  **UserMenu** in the top bar (avatar+name → settings, sign out), and a product **AppMenu** ("⋮" →
  theme, language, cheat-sheet, help). `ShortcutsContext`+`ShortcutsHost` mount one cheat-sheet driven
  by both `?` and the menu; `Popover` flips upward near the viewport bottom; `effective_preferences`
  now exposes `company_name`; `--color-surface-sunken` token added. Drive-by: setup invite flushes a
  filled-but-unsent invite on Finish; org/profile text fields save on blur not per keystroke. i18n
  1067 keys; `tsc -b` clean; **`gate:all` (00–13) GREEN.** Not yet eyes-on in a browser.
- **Phase 1.5 backup/restore — DONE (`3044b02`):** the Docker `docker compose` self-host path now
  has one-command backup/restore at parity with the bare-metal Windows PS kit. `deploy/docker/backup.sh`
  (pg_dump custom-format out of the `db` container → timestamped host folder + MANIFEST + retention,
  best-effort storage archive) and `deploy/docker/restore.sh` (pg_restore into a SCRATCH db by default,
  `--force` for the live db). RUNBOOK §5 documents the Docker path; gate13 gained a Docker-kit coherence
  check; the previously-untracked Docker packaging (Dockerfile/compose/entrypoint/`.env.docker.example`)
  is now committed. `gate:all` (00–13) GREEN. **Not yet exercised against a live `docker compose` stack.**
- **Phase 2 CSV import — COMPLETE** (branch `growth/csv-import`, merged into `growth/combined`):
  **2.0** friction decisions written before code (`DECISIONS.md`, 2026-06-27); **2.1/2.2** generic
  importer engine `erp/core/imports.py` + `ImportDialog`, proven on Customers + template download
  (`856fcea`, 10 tests); **2.3** Suppliers + shared DRF glue `erp/core/import_api.py` (`905640e`);
  **2.4** Items with `category_code`→Category FK resolution (missing = row error), choice/decimal
  validation (`6fb8504`). `gate:all` 00–13 GREEN. **Eyes-on browser click-through DONE (2026-06-27):**
  all three lists verified live — auto-column-map, preview summary (add/skip/problem counts), row-level
  errors (`required`, `category 'RAW' not found`, choice, `not a number`), commit + "Imported N rows"
  toast + new rows appear. Two minor polish findings (not blockers): (a) DRF choice-field error returns
  Arabic text even in EN mode — untranslated default message leaks through; (b) "Import 1 rows" isn't
  singularized.
- **Phase 3.0 friction walk — DONE (2026-06-27).** Walked Quote → SO → Invoice → e-invoice → paid as a
  real user (admin, demo data); friction list written to `DECISIONS.md` "Phase 3.0 — Daily money loop
  friction list". Headlines: (A) no smart defaults — customer/warehouse/tax-code start empty, **unit
  price isn't prefilled from the item**, qty has no `1` default; (B) up to 5 sequential single-button
  steps draft→paid with no cash-sale fast-path; (C) payment always full-amount, no date/method/partial;
  (D) **e-invoice is a context switch** — no submit link from the order; (E) **no printable/PDF invoice
  exists** (that's all of 3.3); (F) "Warehouse code" label + minor i18n snags.
- **Phase 3.1 smart defaults — frontend slice DONE (2026-06-27).** New `lib/lastUsed.ts` (per-key
  localStorage memory, best-effort) + `hooks/useSmartDefault.ts` (seed a select once from last-used if it
  still exists, else the only option; never overrides a user pick; single-option fallback opt-out). Wired
  into `NewOrderPage` (customer/warehouse/tax) + `NewQuotationPage` (customer/warehouse, shares the
  memory); line **qty now defaults to 1**. Order date is already server-defaulted (no input). Verified
  live: qty=1, last-used customer/warehouse pre-fill on a fresh form, no false default when there are
  multiple options + no memory. i18n 1100 keys (no new strings); `tsc -b` + `npm run build` clean.
  - **SPLIT OUT — unit-price prefill needs a backend decision.** Finding A's biggest item ("prefill unit
    price from the item") can't be frontend-only: **`Item` has no price field** (model/serializer/import
    all lack it). Adding it is a schema change (field + migration + serializer + importer + template) with
    a real modelling question (single price? tax-inclusive? per-currency?). Left for an explicit decision
    before building — see the daily-loop friction list in `DECISIONS.md` finding A.
- **Pricing engine (Growth 3.1b) — decided + P1 DONE (2026-06-27).** Decision (user): build a small
  **Oracle-EBS-*core* pricing module** instead of a single price on Item — price lists + tiers,
  per-customer assignment + overrides, effective dates, tax-inclusive, resolved by a precedence engine.
  Full design + the P1–P5 phase plan in `DECISIONS.md` "Pricing engine — Oracle-EBS-core model".
  - **P1 (backend foundation) DONE:** new `erp/pricing/` app (registered in `base.py`), 4 domain models
    (`PriceList`, `PriceListLine`, `CustomerPriceList`, `CustomerItemPrice`) + migration `0001`,
    repositories, and `services/resolve.py` — `resolve_unit_price(customer, sku, on, quantity, currency)`
    with precedence customer-item → customer-list → default-list → None, qty-breaks, effective dates,
    currency filter, tax-agnostic (returns price + `tax_inclusive` flag). Public `contracts/`. **9 resolver
    tests pass; `gate:all` 00–13 GREEN.** No API/UI yet.
  - **P2a (API) DONE:** DRF endpoints under `/api/pricing` — price-lists (CRUD + single-default enforce),
    nested lines (add/patch/delete), customer-assignments (upsert/delete), customer item overrides, and
    `GET /resolve` (backs VAT out of a tax-inclusive price via `accounting.contracts.find_tax_code` +
    `net_of_tax`). Management Branch-Manager-gated; resolve needs only auth. 15 pricing tests; `a900f2f`.
  - **P2b (management UI) DONE:** **Pricing** section (admin-gated, under ADMINISTRATION) — `PriceListsPage`
    (create + browse, default/tax-inclusive/inactive tags) + `PriceListDetailPage` (lines editor with
    qty-break, list toggles). New `api/pricing.ts`, single-stroke price-tag icon, sidebar entry, routes,
    bilingual help guides, i18n 1128 keys (ar/en parity), `pricing.css` (tokens + logical CSS). Verified
    live (create list, add line, toggle default → "تم الحفظ"). `gate:all` 00–13 + gate03 GREEN; build clean.
    *(Per-customer assignment/override management UI deferred to P5 — the API + resolver already support it.)*
  - **NEXT → P3:** wire the order/quotation line — on (customer + item) call `/pricing/resolve` to prefill
    the net unit price + show its source ("from Retail"). **This delivers finding A's price-prefill via the
    engine.** Then P4 (price-list CSV import + demo seed) and P5 (assignment/override + effective-date UI).

## Active work (earlier) — Linear-quality frontend UX overhaul
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
    `useListKeyboardNav` gained opt-in `persistKey`+`getItemId`. **Now wired on all 11 keyboard lists**
    (PR #11 extended PR #7's 5 to the remaining 6: crm campaigns, workflows, stock counts, budgets,
    bank-reconciliation, fixed assets — the last keys on `code`).
  - **#8 settled confirmation beat**: success toasts draw a monochrome check in over the existing
    `toast-in` (decelerating, no bounce; reduced-motion collapses it). No button "working" state —
    optimistic actions vanish on commit, so it would never render.
  - **#9 spacing rhythm**: snapped the off-scale, density-frozen `*-meta__row` gaps (`0.125rem`) onto
    `var(--space-1)` to match the summary-item rhythm. Deliberately surgical (no blind token churn).
  - **#10 Arabic nativeness**: lexicon audit found `ar.json` clean except the **approve** concept —
    six اعتماد-root stragglers (incl. a `مُعتمَد` next to `بانتظار الموافقة` in one block) unified onto
    the موافقة root (§6.1, 2026-06-23): `اعتمدها`→`وافق عليها`, `مُعتمَد`→`مُوافَق عليه`. 1029 keys.

### NEXT ACTION
PRs #1–#11 are **merged to `main`**; working tree clean (only the unrelated `erp_questionnaire_v4.html`).
List-cursor restore now covers all 11 keyboard lists; the success-check toast beat is global. Open
options: **eyes-on spacing/rhythm tuning** at both densities (the one pass that needs a browser, not
blind edits); more inline-edit fields (each needs a small backend PATCH opening); deeper palette work
(recent *items*, scoped actions); add j/k + cursor-restore to lists that don't yet have keyboard nav
(customers, suppliers, items, leads, tickets, …).

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
