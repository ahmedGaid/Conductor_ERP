# Conductor ERP (ERP-B lane) — Project Status

![Status](https://img.shields.io/badge/status-active_development-brightgreen)
![Progress](https://img.shields.io/badge/progress-90%25-blue)
![Stack](https://img.shields.io/badge/stack-Django%205.1%20%2B%20React%2018%2FTS-informational)

> **Last Updated:** 2026-07-18 · **Updated By:** agent · **Branch analyzed:** `feat/sec-hardening`
> (== `origin/main` @ `cd99366`)
> 🤖 **AI agents:** read [Executive Summary](#executive-summary) +
> [AI Agent Quick Context](#ai-agent-quick-context) first — 2 minutes gets you 90% of the picture.

## Executive Summary

Conductor ERP ("ARP — Agentic Resource Planning") is a customer-hosted, single-tenant ERP for
Egyptian SMBs: Django modular-monolith backend + React/TS frontend, Arabic/RTL-first, bilingual.
Core modules (Sales, Purchasing, Inventory, Accounting, CRM) plus VAT, Egyptian e-invoicing (ETA),
workflow engine, AI assistant, RBAC, and audit trail are built and gated green (`v1.0.0`,
2026-07-16). **This specific checkout is `C:\AhmedGaid\ERP-B`** — a separate git worktree used by
"Agent B" to run backend work in parallel with "Agent A" (main checkout `C:\AhmedGaid\ERP`,
`feat/a-*` branches) against the same GitHub repo. Current focus: the pre-handover hardening set
(security hardening confirmed done and re-verified 2026-07-18) plus the "twenty-harvest" (Twenty
CRM parity) and "smart-import" (zero-prep Excel migration) plans — backend for both is now almost
entirely done; **Agent B's lane is IDLE** (no eligible backend-only task left per the 2026-07-18
board audit) and the remaining backlog is nearly all `apps/web` UI, Agent A's territory. B only
picks up new work when the founder opens a backend-only task or takes an explicitly-authorized
cross-territory `apps/web` file.

## AI Agent Quick Context

- **Current goal:** Ship customer handover readiness. Lane B's backend queue (twenty-harvest +
  smart-import) is now almost entirely done — **lane B is IDLE** as of 2026-07-18; remaining work
  is nearly all `apps/web` UI (lane A's territory) or founder-gated (handover-gate sections C/D/E
  need a real customer box).
- **Architecture:** Django 5.1 + DRF modular monolith (`erp/*` apps) + React 18/TS/Vite
  (`apps/web`), Postgres 16, Redis (Celery broker + throttling), Arabic/RTL-first, JWT auth.
- **⚠️ You are in a worktree, not the primary checkout.** `C:\AhmedGaid\ERP-B` is Agent B's lane
  (own `.venv`, own `.env` → DB `erp_b`/test DB `test_erp_b`, Redis db `/1`, Django port 8001,
  Vite 5174). The sibling checkout `C:\AhmedGaid\ERP` is Agent A's lane (DB `erp`/`test_erp`,
  ports 8000/5173). **Never run pytest/gates/git commit/runserver/npm from the wrong checkout** —
  a 2026-07-16 incident had both agents in one checkout and it corrupted the shared test DB.
- **Lane B territory (this checkout should mainly touch):** `erp/core/**`, `erp/imports/**`,
  `scripts/gates/**`, `VERSION`, `CHANGELOG.md`, `Docs/RUNBOOK.md`. Lane A owns `apps/web/**`
  (incl. i18n keys) and `erp/workflow/**`/`erp/webhooks/**`. Cross-territory edits wait for a
  merge checkpoint — see `Docs/plan/PARALLEL_PLAN.md`.
- **Hard constraints:** raw hex colour only in `apps/web/src/styles/tokens.css`; logical CSS only
  (no physical left/right); every user string in BOTH `ar.json`/`en.json`; money as integer minor
  units on the wire; no new dependencies without asking; no third font/icon library/CDN assets.
- **Key conventions:** one plan `FILE_NN.md` = one task = one session; a done file gets `_done`
  appended and is never reopened; every session ends with a "How to test" block + an
  `erp-status`-skill update at merge checkpoints only.
- **Do NOT:** touch `apps/web/**` from this lane without a coordination note on the board; reopen
  a `_done` plan file (fix forward in code instead); run destructive git ops on `main`.
- **Current priorities:** delivery-readiness FILE_07 handover gate sections C/D/E (founder + real
  customer box, not solo). Backend queue is otherwise drained — admin panel backend (FILE_19),
  AI usage/cost backend (FILE_20), draftable payments, and reconciled inventory opening are all
  done. Remaining twenty-harvest/smart-import work is `apps/web` UI (lane A) for those same
  features, plus TH FILE_18 (Kanban pipeline) and SI FILE_12–15 (wizard/preview/report UI).
- **How to continue safely:** read `Docs/plan/PARALLEL_PLAN.md` (board) and
  `Docs/plan/EXECUTION_ORDER.md` (queue authority) first; recall the `erp-status` skill for live
  state; run `pytest erp/<app>` + `.\.venv\Scripts\python.exe scripts\gates\_run.py all`.
- **Likely next files to edit:** none default-claimed — lane B is idle. If picking up
  founder-authorized cross-territory `apps/web` work (as happened once already, see FILE_12/16),
  **check `Docs/plan/PARALLEL_PLAN.md` first for a `doing(A)` row on the same file** — two agents
  independently built the same FILE_16 UX-states-batch task in parallel on 2026-07-18 because the
  board hadn't been flipped yet; the duplicate was discarded in favor of Agent A's version.
- **Deeper truth lives in:** `erp-status` skill (live pointer), `DECISIONS.md` (160K, full
  rationale log), `Docs/plan/EXECUTION_ORDER.md` (queue order), `Docs/plan/PARALLEL_PLAN.md`
  (this lane's board), `Docs/ARP_STRATEGY.md` (category/scope), `Docs/Brand/*` (brand triad).

## What Is This Project?

Conductor ERP is a Django-based, single-tenant, customer-hosted ERP built for Egyptian SMBs, with
an Arabic-first bilingual UI. It bundles accounting, inventory, sales, purchasing, and CRM with
Egyptian tax/e-invoicing (ETA) compliance, plus an AI assistant that can answer questions and
propose scoped actions over the business's own data. Internally the product category is "ARP —
Agentic Resource Planning" (adopted 2026-07-02); externally still marketed as an Arabic-first ERP
until the claims gate opens.

**Maturity:** beta / pre-launch — v1.0.0 tagged 2026-07-16, all core-module gates green, currently
in a "delivery-readiness" hardening pass before the first real customer handover.

## Progress Overview

> ⚠️ Percentages are **estimates** inferred from plan-file `_done` status, gate count, and
> `erp-status`/DECISIONS.md — not measurements.

| Area | Progress | Status |
|---|---|---|
| **Overall** | `█████████░ 90%` | Core ERP + Twenty-harvest/Smart-import backend done; remaining work is mostly `apps/web` UI + founder-gated handover steps |
| Backend (Django/DRF) | `█████████░ 90%` | 5 core modules + accounting depth + workflow + identity/RBAC + admin-panel + AI-usage + draftable-payments + inventory-opening backends all done; lane B idle, no backend-only task left |
| Frontend (React/TS) | `████████░░ 85%` | Core UI + Linear-polish + custom-fields UI + API-keys UI + activity-timeline UI + list-UX + Arabic user guide done; Kanban pipeline UI, admin-panel UI, AI-usage UI, import wizard/preview UI still open |
| Database | `█████████░ 90%` | Postgres 16, migrations current per app; no known pending schema debt |
| Infrastructure | `████████░░ 80%` | Docker/Compose + `provision_customer` go-live command done; production hardening ongoing |
| Authentication | `█████████░ 90%` | JWT + HttpOnly refresh cookie, 2FA, RBAC, API keys — backend AND Settings UI both done |
| API | `█████████░ 90%` | DRF surface broad + gate17 API-schema snapshot kept current; admin-panel/AI-usage/imports endpoints all landed |
| Testing | `████████░░ 80%` | pytest + pytest-django, ~1300+ tests reported green in `erp-status`; Playwright E2E for Tier-1 flows done; **no JS unit-test runner** |
| Documentation | `█████████░ 90%` | Extensive `Docs/plan/*`, `DECISIONS.md`, brand docs, RUNBOOK, in-app Arabic user guide |
| Deployment | `███████░░░ 70%` | Dockerfile + waitress/whitenoise prod profile; handover gate (FILE_07) sections A+B done, C/D/E not yet run on a real customer box |
| AI Integration | `███████░░░ 70%` | AI workspace (chat/actions/tool catalog) + usage/cost tracking backend done; AI-reliability roadmap Phases 3–8 (retrieval v2, memory, orchestration, guardrails) not started |

## Architecture & Stack

**Stack:** Python 3.13, Django 5.1, DRF 3.15, Postgres 16 (via psycopg 3), Celery 5.4 + Redis 5,
Pydantic 2.8, Argon2 password hashing, SimpleJWT, pyotp (2FA); React 18.3 + TypeScript 5.7 + Vite
6, react-router-dom 7, i18next/react-i18next, `@xyflow/react` (workflow canvas), Playwright (E2E).
AI: `anthropic` + `google-genai` SDKs, optional at runtime (off without an API key).

- Modular monolith: each business domain is a Django app under `erp/`, isolated by app boundary,
  not microservices.
- `erp/core` is the cross-cutting kernel: correlation IDs, structured logging, error catalog,
  events, repository base, custom-fields engine, import/export/search APIs.
- Background work: DB-backed job queue for Smart Import (`ImportBatch` row + `manage.py
  run_imports`), Celery used elsewhere (monitoring, notifications) — deliberately NOT reused for
  imports (see `DECISIONS.md` 2026-07-17 entry).
- Machine gates (`scripts/gates/gate00.py` … `gate17.py`) are the definition-of-done per stage;
  `_run.py all` runs every implemented gate in order.
- Frontend: Arabic/RTL-first, logical CSS only, design tokens in `apps/web/src/styles/tokens.css`,
  single icon set (`apps/web/src/app/icons.tsx`), i18n key-parity enforced by a checked-in script.

### Folder Structure

```
config/          Django project: settings split (base/dev/prod), urls, wsgi/asgi, celery.py
erp/             modular-monolith apps: core, identity, audit, monitoring, workflow, forms,
                 accounting, inventory, sales, purchasing, crm, notifications, pricing, setup,
                 einvoice, imports, assistant (AI)
apps/web/        React + TS frontend (src/app shell, api, auth, pages, i18n, styles, hooks)
apps/web/e2e/    Playwright E2E suite
scripts/gates/   gate00.py .. gate17.py — machine-checked definition of done per stage
scripts/sql/     DB bootstrap SQL
Docs/plan/       every feature plan, one FILE_NN.md per session-scoped task
Docs/Brand/      brand triad: Brief (words), Directive (in-app behaviour), Visual Identity System
architecture/    auto/maintained docs (modules, events, database, api, error-catalog)
storage/         runtime file storage root (reports, exports; STORAGE_ROOT env-configurable)
```

### Main Modules

- `erp/core` — cross-cutting kernel (correlation, logging, errors, events, custom fields, imports
  glue, search/resolve/export APIs).
- `erp/identity` — auth, users, RBAC, 2FA, branches, API keys (`ApiKeyAuthentication`).
- `erp/imports` — Smart Import engine: parsing, mapping, dedupe, auto-masters, adapters
  (sales/purchasing/finance documents), execution engine, job runner.
- `erp/accounting`, `erp/inventory`, `erp/sales`, `erp/purchasing`, `erp/crm` — the five core
  business modules.
- `erp/workflow` — workflow/automation engine + webhooks (Agent A territory).
- `erp/assistant` — AI chat/actions backend (conversations, tool catalog, safe actions).
- `erp/audit` — immutable audit trail + activity timeline read API.
- `apps/web/src/app` — app shell (AppShell, CommandPalette/CommandBar, InboxPanel, action
  feedback/receipt UI).

### Central Files (handle with care)

| File | Why it matters | Safe to edit casually? |
|---|---|---|
| `DECISIONS.md` (160K) | Full rationale log for every non-obvious call — read before re-deciding something | ✅ append-only, don't rewrite history |
| `Docs/plan/EXECUTION_ORDER.md` | Queue authority — what to work on next, in what order | ⚠️ only at plan-session boundaries |
| `Docs/plan/PARALLEL_PLAN.md` | This lane's coordination board vs. Agent A | ⚠️ flip status in the same commit as the work |
| `apps/web/src/styles/tokens.css` | Only place raw hex colour is allowed | ⚠️ No |
| `config/settings/base.py` / `prod.py` | Security posture (CSP, HSTS, cookies, CORS) | ⚠️ No |
| `.env` (gitignored) | DB/Redis URLs, ports — differ per lane (`erp` vs `erp_b`) | ⚠️ No — never commit |

## Features

### ✅ Completed
- [x] Core modules — Sales, Purchasing, Inventory, Accounting, CRM
- [x] VAT + Egyptian e-invoicing (ETA)
- [x] Workflow engine + outbound webhooks
- [x] AI assistant (chat/ask over scoped business data, safe actions)
- [x] Identity — JWT + HttpOnly refresh cookie, 2FA, RBAC, branches, API keys (backend)
- [x] Arabic/RTL-first UI, full ar/en parity, light/dark theming
- [x] Audit trail + activity timeline (read API)
- [x] Custom fields backend (fields only, not objects)
- [x] Partial payments (UI + API)
- [x] `provision_customer` go-live command
- [x] Release versioning (`VERSION`, `manage.py upgrade` command, upgrade-drill + API-schema
      snapshot gates)
- [x] Playwright E2E for Tier-1 write flows
- [x] Smart Import: parsing/mapping/dedupe/auto-masters/execution-engine/background runner/REST
      API/document adapters (sales, purchasing docs) + finance adapters (journal entries,
      account opening)
- [x] Security hardening — scope enforcement (`scope_queryset` on every module), SSRF egress guard,
      auth/JWT hardening, import/backup file-handling caps, `check --deploy` clean — confirmed done
      + re-verified twice (2026-07-16, 2026-07-18)
- [x] Custom fields UI (Settings CRUD + customer/item/supplier forms) — twenty-harvest FILE_12
- [x] Activity timeline — read API + tab UI + AI/import source glyph — twenty-harvest FILE_13
- [x] API keys — backend + Settings → Developers UI + generated reference page — twenty-harvest FILE_14
- [x] List UX — peek-card audit (zero gap found) + Pipeline stage inline edit — twenty-harvest FILE_17
- [x] Arabic-first in-app User Guide + 38-term glossary, reachable via ⌘K/App Menu — twenty-harvest FILE_15
- [x] Admin panel backend (`GET /api/system/status/` — version/uptime/DB+Redis/storage/backups) —
      twenty-harvest FILE_19 Task A/C (Settings UI still open)
- [x] AI usage & cost backend (`GET /api/assistant/usage/`) — twenty-harvest FILE_20 Task A/C
      (Settings UI still open)
- [x] Draftable payments (`PendingPayment`) + reconciled inventory opening (`PendingStockEntry`,
      suspense-account posting) backend + API — review/apply screens (apps/web) still open

### 🟡 Partially Complete
- [ ] Smart Import finance adapters — journal entries + opening entries done; payments/receipts
      and inventory-opening/transactions are documented blockers (no unallocated-payment model,
      no as-of-date WAC) — see `DECISIONS.md`
- [ ] Smart Import document/finance adapters — backend done (SI FILE_15/16); wizard/preview/
      report + suspense-approval UI (SI FILE_12–14) unbuilt (Agent A territory)
- [ ] Twenty-harvest FILE_16 UX states batch (empty-state taxonomy, skeletons, `?` cheatsheet) —
      reportedly completed by Agent A 2026-07-18 in the sibling `C:\AhmedGaid\ERP` worktree, but
      **not yet visible on `origin/main`** as of this update; treat as unconfirmed until the board
      or a commit shows it merged
- [ ] Admin panel + AI usage Settings UI (FILE_19/20 Task B) — backend/API done, UI unbuilt
- [ ] Delivery-readiness FILE_07 HANDOVER GATE — sections A+B done; C/D/E need the founder on a
      real customer box (provisioning, ETA day-one invoice, restore drill)

### ⬜ Not Started
- [ ] Twenty-harvest FILE_18 Kanban pipeline UI, FILE_21 acceptance
- [ ] Smart-import FILE_17 acceptance (blocked on FILE_12–14 UI landing first)
- [ ] AI-reliability roadmap Phases 3–8 (retrieval v2, memory, agent orchestration v2,
      guardrails/security, perf/cost, production hardening)
- [ ] ARP roadmap phases A2, B, B2, C–F (strategic roadmap, gated behind queue positions 1–10)
- [ ] Mobile app plan (shelved)

## Roadmap & Next Steps

Authority: `Docs/plan/EXECUTION_ORDER.md` (global queue) + `Docs/plan/PARALLEL_PLAN.md` (this
lane's board). Do not reorder without reading both.

**High Priority**
1. Delivery-readiness FILE_07 HANDOVER GATE sections C/D/E (founder + real customer box — the only
   hard blocker left before customer handover)
2. Twenty-harvest FILE_18 Kanban pipeline UI, FILE_19/20 Settings UI (admin panel, AI usage) —
   all Agent A territory, backend already done for all three

**Medium Priority**
1. Twenty-harvest FILE_21 acceptance (after Tier-2/3 UI lands)
2. Smart-import FILE_12–15 (wizard/preview/report/adapter-review UI — Agent A territory, backend
   done for all of it) → FILE_17 acceptance

**Low Priority**
1. ARP roadmap phases A2/B/B2/C–F (after queue positions 1–10 are fully `_done`)
2. AI-reliability roadmap Phases 3–8

**Current blockers:** none active for lane B (lane is idle — no eligible backend-only task).
Historical: 2026-07-16 both-agents-one-checkout incident (fixed — worktrees now separate, see Hard
Constraints above); 2026-07-18 both agents independently built the same `apps/web` file (FILE_16)
in parallel because the shared board hadn't been flipped yet — no data lost, the duplicate was
discarded, but it's a reminder to re-check `PARALLEL_PLAN.md` immediately before any cross-territory
pickup, not just at session start.

## Recent Work

- 2026-07-18 — gate17 API-schema snapshot regenerated (was stale since `91da71a`, flagging a real
  route replacement as a false break) (`98c8878`)
- 2026-07-18 — Security hardening (B18) confirmed already done from the 2026-07-02 session,
  re-verified twice, docs-only (`b503df7`, `03fa32c`, `dbe2f81`)
- 2026-07-18 — Arabic-first in-app User Guide + 38-term glossary, ⌘K/App-Menu reachable
  (twenty-harvest FILE_15) (`733ec81`)
- 2026-07-18 — CRM Pipeline stage inline edit + list-page peek-card audit (twenty-harvest FILE_17)
  (`00e3a36`)
- 2026-07-18 — API keys Settings page + generated reference docs page (twenty-harvest FILE_14
  Task B/C) (`f01fc57`)
- 2026-07-18 — Activity timeline tab UI + AI/import source glyph (twenty-harvest FILE_13 Task B/C)
  (`1081e22`)
- 2026-07-18 — Supplier added as a third custom-fields entity (`cca1093`)
- 2026-07-18 — Custom fields UI: Settings CRUD + customer/item form rendering (twenty-harvest
  FILE_12) (`3a52111`)
- 2026-07-18 — Admin panel backend (`GET /api/system/status/`), AI usage/cost backend
  (`GET /api/assistant/usage/`), draftable payments, reconciled inventory opening — all backend
  done this window, review/apply UI still open (see `Docs/plan/PARALLEL_PLAN.md` B14–B17)
- earlier (2026-07-16/17): Smart Import engine complete (parsing → execution → background runner →
  REST API → document + finance adapters), activity-timeline read API, custom-fields backend,
  release versioning (`VERSION`/`manage.py upgrade`)

**Recent architectural changes:**
1. Smart Import background jobs use a DB-backed queue (`ImportBatch` status + `manage.py
   run_imports`), not Celery — deliberate choice despite Celery already being installed/in-use
   elsewhere (2026-07-17).
2. `execute_batch`/`resume_batch` gained an `on_chunk` callback seam for pause/cancel control,
   backward-compatible with existing callers.
3. Two-worktree parallel-agent setup (`C:\AhmedGaid\ERP` = lane A, `C:\AhmedGaid\ERP-B` = lane B)
   with disjoint DBs/ports/Redis-db, established 2026-07-16 after a shared-checkout incident.
4. API keys authenticate as a hidden auto-created "principal" user riding existing RBAC/scoping/
   audit — no parallel permission system.

## Known Issues & Technical Debt

- Smart Import finance adapters: `payments`/`receipts` and `inventory_transactions` are explicitly
  unbuilt (documented blockers — no unallocated-payment model, no as-of-date WAC). `inventory_opening`
  was later solved separately via `PendingStockEntry` (suspense-account posting, B17) — only
  `inventory_transactions` remains an open blocker now. See `DECISIONS.md`.
- `erp/workflow/tests/test_api.py` — pre-existing broken test flagged separately in `erp-status`
  (excluded from the "1146/1146 green" count as of 2026-07-16).
- `seed_identity` creates 3 demo users with a shared known password (`Dev12345!`) — fine for dev,
  flagged as needing a customer-safe provisioning path (no demo users) before real handover.
- `ask.py` router is blind to attachments (filed, not scheduled).
- `sales._next_customer_code` can mis-detect the max on non-numeric codes (filed, low priority).
- No `TODO`/`FIXME`/`HACK` markers found in `erp/` — debt is tracked in `DECISIONS.md`/plan files
  instead of code comments.
- **Uncommitted local noise:** 1,100+ (growing) untracked `assistant/2026/07/data_*.csv` files at
  repo root (small generated CSVs, e.g. import/export test artifacts) — not part of the tracked
  project; worth `.gitignore`-ing before it grows further, not currently a functional issue.

## Design Decisions & Business Rules

Full log: `DECISIONS.md` (160K, append-only). Highlights relevant to this lane:
- **ARP category** adopted 2026-07-02 as the internal product category name; public-facing copy
  still says "Arabic-first ERP" until a claims gate opens (`Docs/ARP_STRATEGY.md`).
- **Delivery-readiness pivot** (user, 2026-07-15): roadmap queue paused in favor of hardening for
  a real customer handover; AI explicitly out of scope for that track.
- **Two-agent parallel lanes**: `ERP-B` worktree exists solely to let Agent B work backend
  (`erp/core`, `erp/imports`, gates) concurrently with Agent A's frontend/workflow work, without
  sharing a checkout or test DB. Territory boundaries and merge checkpoints are in
  `Docs/plan/PARALLEL_PLAN.md` — treat that file, not tribal knowledge, as authoritative.
- **Import job queue**: DB-backed (`ImportBatch` + `run_imports` command), not Celery, per founder
  decision even though Celery was already available (2026-07-17).
- Money: integer minor units on the wire; format/parse only at the edges.
- One canonical Arabic word per business concept (see Identity System §6 in `Docs/Brand/`).

## How to Build / Run / Test / Deploy

```bash
# Build (frontend)
cd apps/web && npm run build          # tsc -b && vite build (+ i18n-parity and bundle-size checks)

# Run (dev) — from repo root
.\.venv\Scripts\python.exe manage.py runserver 8001   # this lane uses port 8001
cd apps/web && npm run dev                              # this lane's Vite runs on 5174 per board
# convenience script (Agent A's default ports 8000/5173):
run-dev.ps1

# Test
.\.venv\Scripts\python.exe -m pytest erp/<app>          # per-app; full suite before merge checkpoints
cd apps/web && npx playwright test -c e2e/playwright.config.ts   # Tier-1 E2E (no JS unit runner exists)

# Gates (definition of done per stage)
.\.venv\Scripts\python.exe scripts\gates\_run.py all     # 00–17, must be green before merging
cd apps/web && node scripts/check-i18n-parity.mjs && npx tsc -b
python scripts/gates/gate03.py                           # brand gate (repo root)

# Deploy
# manual — see Docs/RUNBOOK.md; Dockerfile + docker-compose.yml for containerized deploy,
# waitress + whitenoise for the pure-Windows-friendly prod profile
```

**Environment requirements:** Python 3.13, Node LTS (24/npm 11), PostgreSQL 16, Redis-compatible
service (Memurai on Windows). Required env vars (names only, see `.env.example`):
`DJANGO_SETTINGS_MODULE`, `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`,
`DATABASE_URL`, `REDIS_URL`, `CELERY_TASK_ALWAYS_EAGER`, `STORAGE_ROOT`, `API_PORT`, `WEB_PORT`,
`DJANGO_COOKIE_SECURE`, `DJANGO_SSL_REDIRECT`, `DJANGO_CSP_POLICY`, `DRF_THROTTLE_*`,
`WORKFLOW_EGRESS_ALLOWLIST`, `EMAIL_*`. This lane's `.env` points at DB `erp_b` (test DB
`test_erp_b`), Redis logical db `/1` — do not copy Agent A's `.env`.

## Integrations & Services

- **Anthropic / Google Gemini** — AI assistant providers, optional at runtime, off without an API
  key (`anthropic`, `google-genai` SDKs).
- **Egyptian Tax Authority (ETA)** — e-invoicing integration (`erp/einvoice`).
- **Celery + Redis** — background tasks (monitoring, notifications); NOT used for Smart Import
  jobs (deliberate — DB-backed queue instead).
- **Outbound webhooks** — workflow engine can call external HTTP endpoints
  (`WORKFLOW_EGRESS_ALLOWLIST` gates destinations).

## Database Overview

PostgreSQL 16. Each `erp/<app>` owns its own Django models/migrations (modular monolith, one
schema). Core cross-cutting tables live in `erp/core` (custom fields, events). No ORM sharding —
single-tenant per deployment (customer-hosted). Migrations tracked per-app under
`erp/<app>/migrations/`; `manage.py upgrade` is the registry-driven release-step runner for
customer upgrades (not raw `migrate`).

## Auth & API

- **Authentication:** JWT (SimpleJWT) with HttpOnly refresh cookie; TOTP 2FA (`pyotp`); API keys
  authenticate as a hidden auto-created principal user riding the same RBAC path as a human login.
- **Authorization:** role-based (RBAC) — roles, permissions, approval limits, branches; scoped
  per-module.
- **API surface:** DRF, one router/viewset set per `erp/<app>`; `gate17.py` snapshots the API
  schema to catch accidental breaking changes.

## Quality: Testing, Performance, Security

- **Testing status:** pytest + pytest-django, ~1300 backend tests reported green as of 2026-07-16
  (per `erp-status`, excluding one pre-existing broken workflow test); Playwright E2E covers
  Tier-1 write flows. **No JS unit-test runner** — frontend correctness relies on `tsc`, i18n
  parity check, and manual/E2E verification.
- **Performance:** no known open performance issues recorded; bundle-size gate
  (`check-bundle-size.mjs`) runs on every frontend build.
- **Security:** prod settings profile sets HSTS (1y), strict CSP, secure cookies, SSL redirect;
  `manage.py check --deploy --settings=config.settings.prod` reports no issues (verified
  2026-07-16, re-verified 2026-07-18). Argon2 password hashing, DRF throttling on anon/user/login.
  `Docs/plan/00-security-hardening.md` (scope enforcement via `scope_queryset` on every module,
  SSRF egress allowlist, JWT/auth hardening, import/backup file-size caps) is **done and
  re-verified twice** — no longer outstanding. Still owed before real customer handover: demo-user
  default-credential cleanup (`phase1d_qa` test user pending suspend/delete in the dev DB).

---

> 📄 Maintained by the `ag-project-md` skill. Update it after meaningful changes —
> stale status is worse than no status. Manual edits welcome; the skill preserves them.
