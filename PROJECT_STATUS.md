# Conductor ERP (ARP) — Project Status

![Status](https://img.shields.io/badge/status-active--development-brightgreen)
![Progress](https://img.shields.io/badge/progress-90%25-blue)
![Stack](https://img.shields.io/badge/stack-Django%20%2B%20React-informational)

> **Last Updated:** 2026-07-16 · **Updated By:** agent · **Branch analyzed:** main
> 🤖 **AI agents:** read [Executive Summary](#executive-summary) +
> [AI Agent Quick Context](#ai-agent-quick-context) first — 2 minutes gets you 90% of the picture.
> **Live truth is the `erp-status` skill** (recall via `/erp-resume`); this file is the umbrella
> summary, not a second source of truth — when they differ, `erp-status` wins.

## Executive Summary

Conductor is a customer-hosted, single-tenant **ERP for Egyptian SMBs**, internally categorized as
**ARP — Agentic Resource Planning** (AI-native ERP). Django modular monolith (Python 3.13 + DRF) +
React 18/TS/Vite frontend, **Arabic/RTL-first** and bilingual. Quality bar: "Linear's craft,
Telegram's calm." The core ERP is **built and gate-green**: five business modules
(Accounting, Inventory, Sales, Purchasing, CRM) plus accounting/ops depth, Egyptian VAT + ETA
e-invoicing, reports, notifications, workflow/forms engine, RBAC, an AI assistant, and a unified
Linear-grade UI. All machine gates 00–15 pass. **As of 2026-07-15 the team is on a DELIVERY TRACK**
(founder pivot): hand the app to a real customer to run as a live business — every non-AI feature
verified end-to-end (drive → fix → report), with the strategic roadmap queue **paused**. Phase 0
(ground-truth) and Phase 1a (Sales+Inventory E2E) are done and all-PASS; **next is Phase 1b
(Purchasing+Accounting E2E)**. AI/reliability and smart-import work is parked mid-stream behind the
delivery track.

## AI Agent Quick Context

- **Current goal:** DELIVERY TRACK Phase 1b — drive Purchasing+Accounting write-flows E2E in the browser (PR→PO→receive→invoice→3-way match→payment + manual journal + trial balance re-check). See `Docs/plan/delivery-readiness/FILE_00_ASSESSMENT.md` + `FILE_01_E2E_RESULTS.md`.
- **Architecture:** Django modular monolith (`erp/<module>` apps, `config/` project) + DRF API; React 18 + TS + Vite SPA (`apps/web`) behind WhiteNoise; PostgreSQL 16; Redis + Celery; JWT auth. Arabic/RTL-first, bilingual, integer-minor-unit money.
- **Hard constraints (build-blocking):** i18n ar/en key-parity; tokens only (raw hex only in `apps/web/src/styles/tokens.css`); logical CSS only (`inline-start/end`, never `left/right`); monochrome app chrome (colour lives inside pages, always paired with word/icon); one type voice (IBM Plex Sans Arabic + Inter) + one own icon set, no CDN/imported icon libs; one canonical Arabic word per concept; money = integer minor units on the wire; **no new dependencies without asking.**
- **Key conventions:** writes go through the module **service contract** (`create_customer`/`create_item`/…), never raw ORM `.create()`; AI uses tool-calls (never free-text-to-SQL), human-in-the-loop, runs as the user; every empty/error/loading state is designed; settled motion only. Frontend has no JS unit runner — gates are parity + `tsc`.
- **Do NOT:** reopen a `_done` plan file; skip ahead in a plan; blindly paste a plan snippet that contradicts live code (intent wins, note the drift); add a dependency, a second Arabic word, or a physical-direction CSS rule; grow the `erp-status` banners.
- **Current priorities:** (1) delivery-track E2E phases (roadmap queue PAUSED), (2) when resumed: queue pos 8 smart-import FILE_06, then arp-roadmap phases. `Docs/plan/EXECUTION_ORDER.md` is the queue authority.
- **How to continue safely:** recall `erp-status` (via `/erp-resume`) → it names the exact NEXT ACTION + any blocker; load the target plan's `FILE_00_INDEX.md` + one `FILE_NN` only; run gates before "done" (`scripts/gates/_run.py all`; `apps/web`: `check-i18n-parity.mjs` + `tsc -b`). One file = one session.
- **Likely next files to touch:** `Docs/plan/delivery-readiness/FILE_01_E2E_RESULTS.md` (append PASS/FAIL), plus whatever `erp/purchasing/` or `erp/accounting/` code a failure root-causes.
- **Deeper truth lives in:** `erp-status` skill (live NEXT ACTION/blockers), `Docs/plan/EXECUTION_ORDER.md` (queue), `Docs/ARP_STRATEGY.md` (category/scope authority), `DECISIONS.md` (why, 150KB+ decision log), `erp-history` skill (how each module was built), `erp-frontend` + `conductor-brand` skills (UI + brand rules), `Docs/RUNBOOK.md`.

## What Is This Project?

Conductor is an Arabic-first, single-tenant ERP that a customer hosts themselves (no SaaS
multi-tenancy). It targets Egyptian small/medium businesses and covers the standard ERP surface —
general ledger accounting, inventory, sales, purchasing, CRM — with Egypt-specific compliance
(VAT, ETA / e-invoicing "einvoice"). The differentiator is the **ARP thesis**: an embedded AI
assistant that can read and *act on* the business (draft documents, simulate the effect of a
posting before it's committed, import messy Excel data with zero prep), always human-in-the-loop
and running as the user. The bar is Linear-grade craft with a calm, trustworthy, monochrome feel.

**Maturity:** beta / pre-handover — core modules built and gate-green; now being hardened
end-to-end for a first real customer via the delivery track. Not yet running a live business.

## Progress Overview

> ⚠️ Percentages are **estimates** inferred from module completeness, gates, and plan position — not measurements.

| Area | Progress | Status |
|---|---|---|
| **Overall** | `█████████░ 90%` | Core ERP + AI + unified UI built and gate-green; delivery-track E2E hardening + remaining roadmap phases outstanding |
| Backend (Django modules) | `█████████░ 92%` | 5 business modules + accounting/ops depth + VAT/ETA + workflow/forms all built; imports (smart-import) 4/8 adapters |
| Frontend (`apps/web`) | `█████████░ 90%` | React/TS SPA, unified Linear-grade UI, assistant surface, RTL/bilingual; some polish follow-ups shelved |
| Accounting / VAT / ETA | `█████████░ 90%` | GL, journals, trial balance, Egyptian VAT + e-invoice (einvoice) module built; E2E verify in progress |
| AI Assistant (ARP) | `████████░░ 80%` | Assistant, tool-actions, RAG knowledge, reliability gateway (routing/failover/caching/budgets), simulation engine; long reliability track (FILE_03–08) pending |
| Smart Import | `███░░░░░░░ 35%` | FILE_01–05 done (reader, detection, cleaning, 4/8 master adapters); FILE_06–17 pending (paused for delivery track) |
| Auth / RBAC | `██████████ 100%` | JWT + TOTP 2FA, roles/permissions, immutable audit trail |
| API | `█████████░ 90%` | DRF across modules; 48/48 non-AI endpoints verified correct in Phase 0 |
| Testing | `███████░░░ 75%` | pytest per module (206 imports tests alone) + machine gates 00–15 green; **no JS unit runner**; E2E regression harness exists, live E2E in progress |
| i18n (ar/en) | `██████████ 100%` | Key-parity enforced + build-blocking |
| Deployment | `██████░░░░ 60%` | Docker + docker-compose + WhiteNoise/Waitress; customer-hosted; not yet on a live customer box |
| Documentation | `█████████░ 90%` | Strategy, decisions (150KB+), per-plan FILE_NN, runbook, growth plan, owner manual, status skills all maintained |

## Architecture & Stack

**Stack:** Python 3.13, Django 5.1 + Django REST Framework 3.15, PostgreSQL 16 (`psycopg` 3),
Celery 5.4 + Redis 5, `pydantic` 2, `djangorestframework-simplejwt` (JWT), `pyotp` (TOTP 2FA),
`whitenoise` + `waitress` (serve the built SPA behind Django, Windows-friendly), `openpyxl` (XLSX),
`anthropic` + `google-genai` (AI assistant providers — optional at runtime, off without an API
key). Frontend: React 18.3, TypeScript 5.7, Vite 6, `react-router-dom` 7, `i18next`,
`@xyflow/react` (workflow canvas), self-hosted `@fontsource` fonts (no CDN).

- **Modular monolith:** each business/platform concern is a Django app under `erp/`; `config/` holds settings (split: `config.settings.dev`), urls, wsgi/asgi, celery.
- **Service-contract writes:** callers (including AI actions and import adapters) go through module service functions (`create_customer`, `create_item`, `create_lead`, …), never raw ORM `.create()`; RBAC is enforced at that layer.
- **AI:** tool-use only (never free-text-to-SQL), propose → confirm → execute, human-in-the-loop, runs as the user; reliability gateway adds routing/failover/caching/token+cost budgets; a simulation engine shows "tomorrow's books before you post them."
- **Money:** integer minor units on the wire; format/parse only at the edge (`apps/web/src/lib/money.ts`).
- **Frontend:** single React SPA, Arabic/RTL default (LTR must read identically), design tokens + logical CSS + monochrome chrome enforced by gates; optimistic updates, toasts, hover-prefetch, keyboard/⌘K primitives.
- **Gates as definition-of-done:** `scripts/gates/gateNN.py` (00–15) — scaffold/health, brand (gate03), module gates; a phase can't advance until its gate exits 0.
- **Observability:** correlation IDs, structured JSON logging, health + system-check endpoints, monitoring app, immutable audit trail.

### Folder Structure

```
config/           Django project — settings split, urls, wsgi/asgi, celery
erp/              modular monolith (one Django app per concern)
  core/           cross-cutting: correlation IDs, logging, errors, events, repository base
  identity/       auth, users, RBAC, TOTP 2FA
  audit/          immutable audit trail
  monitoring/     health + system-check
  accounting/     GL, journals, trial balance, VAT
  einvoice/       Egyptian ETA e-invoicing
  inventory/  sales/  purchasing/  crm/   the five business modules
  pricing/        price lists / pricing resolution
  workflow/  forms/   workflow + dynamic-forms engine
  assistant/      AI assistant (gateway, actions, RAG, simulation)
  imports/        smart-import engine (readers, detection, cleaning, adapters, registry)
  notifications/  setup/                    supporting modules
apps/web/         React + TS + Vite SPA (api/ app/ assistant/ auth/ components/ pages/ i18n/ lib/ …)
scripts/gates/    machine gates 00–15 (_run.py orchestrates)
architecture/     auto-maintained docs (modules, events, database, api, error-catalog)
deploy/           deployment configs;  Dockerfile + docker-compose.yml at root
Docs/
  plan/           EXECUTION_ORDER.md (queue authority) + per-program FILE_NN plans
                  (delivery-readiness/, smart-import-plan/, ai-reliability-roadmap/, arp-roadmap.md, …)
  ARP_STRATEGY.md · ARP_DEEP_VISION.md · Brand/ · RUNBOOK.md · testing/E2E_MASTER_PROMPT.md
DECISIONS.md      150KB+ decision + rejected-paths log (the project's "why")
```

### Main Modules

- `erp/core` — cross-cutting foundation (events, errors, correlation IDs, repository base).
- `erp/identity`, `erp/audit`, `erp/monitoring` — auth/RBAC/2FA, immutable audit, health.
- `erp/accounting`, `erp/einvoice`, `erp/pricing` — ledger/VAT, ETA e-invoicing, pricing resolution.
- `erp/inventory`, `erp/sales`, `erp/purchasing`, `erp/crm` — the five business modules.
- `erp/workflow`, `erp/forms` — the workflow + dynamic-forms engine (frontend canvas via `@xyflow/react`).
- `erp/assistant` — the AI/ARP surface: gateway, tool-actions, RAG knowledge, simulation engine.
- `erp/imports` — smart-import: streaming xlsx/csv reader, dataset detection, cleaning, master adapters, registry.
- `apps/web` — the React SPA consuming all of the above.

### Central Files (handle with care)

| File | Why it matters | Safe to edit casually? |
|---|---|---|
| `Docs/plan/EXECUTION_ORDER.md` | The queue authority — what to work on and in what order | ⚠️ No (edited in the same commit that adds a plan) |
| `DECISIONS.md` | 150KB+ log of decisions + rejected paths — the project memory | ⚠️ No (append, never rewrite) |
| `Docs/ARP_STRATEGY.md` | Category + scope (build/remove) authority — read before scoping anything | ⚠️ No |
| `apps/web/src/styles/tokens.css` | The ONLY place raw hex is allowed; everything else uses `var(--color-*)` | ⚠️ No |
| `apps/web/src/app/icons.tsx` | The single own icon set — no imported icon library allowed | ⚠️ No |
| `config/settings/*` | Django settings split (`dev`/prod); env-driven | ⚠️ No |
| `requirements.txt` / `apps/web/package.json` | No new dependencies without asking | ⚠️ No |
| `erp/*/services*` (service contracts) | All writes route here; bypassing them skips RBAC | ⚠️ No |

## Features

### ✅ Completed
- [x] Platform foundation — Django modular monolith, core (events/errors/correlation IDs), config split, gates 00+
- [x] Identity — JWT auth, RBAC roles/permissions, TOTP 2FA, immutable audit trail
- [x] Accounting — GL, journals, trial balance, Egyptian VAT
- [x] Inventory, Sales, Purchasing, CRM — the five business modules (create/confirm/deliver/invoice/collect flows)
- [x] Egyptian ETA e-invoicing (`einvoice`), pricing/price-lists (`pricing`)
- [x] Workflow + dynamic-forms engine (backend + React canvas)
- [x] Reports + XLSX export, notifications
- [x] React/TS frontend — unified Linear-grade UI (sticky header bar, unified print/export/share, meta columns), RTL/bilingual, optimistic/toast/prefetch/keyboard/⌘K primitives
- [x] AI assistant (ARP) — assistant surface, tool-actions (per-module drafts), RAG knowledge base, reliability gateway (retry/circuit-breaker/failover/caching/token+cost budgets), os-foundations (action graph v2, verifier packs, simulation engine + diff card)
- [x] Smart-import FILE_01–05 — imports app + adapter registry, streaming xlsx/csv reader, dataset detection + header mapping, data-cleaning normalizers, 4/8 master adapters (customers/suppliers/items/contacts)
- [x] Delivery track Phase 0 (ground-truth: gates green, 48/48 non-AI endpoints correct, frontend boots) + Phase 1a (Sales+Inventory E2E, all PASS)

### 🟡 Partially Complete
- [ ] Smart Import — FILE_06–17 pending (analyze/validate, import, rollback, dedupe, documents/finance, UI, acceptance); paused for delivery track. 4 of 8 master adapters built (item_categories/warehouses/price_lists/units blocked — no module service create-path exists yet)
- [ ] Delivery track — Phase 1b (Purchasing+Accounting E2E) next; later phases decide smart-import defer-vs-finish
- [ ] AI reliability long track — FILE_03–08 (retrieval v2, memory, agent orchestration v2, guardrails/security, perf/cost, production hardening) not started
- [ ] Deployment — Docker/compose ready; not yet running on a live customer box

### ⬜ Not Started
- [ ] arp-roadmap strategic phases A2, B, B2, C–F (gated behind queue positions 1–8)
- [ ] Mobile app — plan rebuilt on Flutter (2026-07-10, drift/dio/bloc, store-only, FCM); needs a DECISIONS entry to activate (shelved)
- [ ] master-roadmap reservoir (13-domain blueprint) — floor tasks slot into gaps as founder paces

## Roadmap & Next Steps

Queue authority: [`Docs/plan/EXECUTION_ORDER.md`](Docs/plan/EXECUTION_ORDER.md). Live NEXT ACTION:
the `erp-status` skill. **The strategic queue is currently PAUSED for the delivery track.**

**High Priority (delivery track — active)**
1. Phase 1b — Purchasing+Accounting write-flow E2E (drive in browser as admin; append PASS/FAIL to `Docs/plan/delivery-readiness/FILE_01_E2E_RESULTS.md`)
2. Remaining delivery-track phases per `FILE_00_ASSESSMENT.md`
3. Clean the demo cash −1.1M EGP seed artifact before customer handover (books still balance; flagged in Phase 0)

**Medium Priority (roadmap — resumes when delivery track done)**
1. Queue pos 8 — smart-import FILE_06 (analyze/validate; Opus-fit) → FILE_07–17
2. Queue pos 9 — arp-roadmap phases A2/B/B2/C–F
3. Queue pos 10 — ai-reliability FILE_03–08

**Low Priority / Shelved**
1. Mobile app (Flutter) — needs a DECISIONS entry to activate
2. unified-ui follow-ups; perceived-performance plan; business-cycles harvest

**Current blockers:** none active (per `erp-status`). Standing dev note: Redis must be running
(`Get-Service Redis` → `Start-Service Redis`; `redis-cli ping` → PONG). Smart-import's remaining
4 adapters are blocked on module owners adding service create-paths for
item_categories/warehouses/price_lists/units (STOP-rule, not this session's work).

## Recent Work

- 2026-07-15 — feat(imports): smart-import FILE_05 — master adapters (customers/suppliers/items/contacts) (`fd2be96` / `87d1208`)
- 2026-07-1x — feat(imports): FILE_04 data-cleaning normalizers (`61a2e7d`); FILE_03 dataset detection + header mapping (`0fc17b6`); FILE_02 streaming xlsx/csv reader (`9f6d332`); FILE_01 imports app + adapter registry (`a2680e6`)
- 2026-07-12 — feat(assistant): os-foundations L2 — diff card + phase W+ acceptance (`82eeb86`); L2 simulation engine (`9af03c2`); L1 verifier wired (`c245db5`); L1 verifier packs (`a8f8b1c`); L0 action graph v2 schema (`f245020`)
- 2026-07-1x — feat(assistant): ai-reliability Phase 2 close — degraded mode (`4c3be91`), semantic cache (`4e24e0c`), token/cost budgets (`93c275e`), streaming resilience (`56de701`), exact-match cache (`13cdec1`), model routing report (`2b0876c`), circuit breaker/failover (`d96befe`)
- 2026-07-10 — docs(mobile): rebuild mobile-app-plan on Flutter (`80149c1`)
- earlier: ai-reliability Phase 1 (traces/eval harness/ops view), agent-actions FILE_01–06, unified-ui, linear-polish, rag-knowledge, ai-workspace (see `erp-history` skill for the full build history).

**Recent architectural changes:**
1. Smart-import adapters call the real module service contract (`create_*`), never ORM `.create()`; a shared `_rbac.require_role` gates `write()` because contract fns don't self-check permission.
2. AI reliability gateway inserted in front of all model calls — retry policy + typed failures, circuit breaker + failover chain, exact-match + semantic caching, token/cost budgets, degraded mode.
3. os-foundations Action Graph v2 + verifier packs + simulation engine — "see tomorrow's books before you post them"; smart-import preview UI is meant to reuse `SimulationDiffCard`.
4. Delivery-track program added (2026-07-15) — E2E-verify every non-AI feature for a real customer; roadmap queue paused.

## Known Issues & Technical Debt

- **Smart-import is mid-stream** — 4 of 8 master adapters built; item_categories/warehouses/price_lists are model-only (inline `Model.objects.create` in API views, no service fn), `units` has no model (`Item.uom` is free text), "contacts" mapped to `crm.Lead` (no Contact model). Blocked until module owners add service create-paths.
- **Zero live customer usage yet** — the delivery track exists precisely because most write-flows haven't been driven E2E on real data; only Sales+Inventory (Phase 1a) verified so far.
- **No JS unit-test runner** — frontend correctness rests on `tsc`, i18n parity, the brand gate, and manual/E2E checks. A green gate = "not mechanically off-brand," not "correct."
- **Demo seed artifact:** demo cash shows −1.1M EGP (books balance) — must be cleaned before handover.
- **Backlog (filed, not scheduled):** `ask.py` router blind to attachments; `sales._next_customer_code` max mis-detect on non-numeric codes (low pri); business-cycles harvest; perceived-performance plan; live-data grounding sliver (accepted gap).
- **Two identical FILE_05 commits** (`fd2be96`, `87d1208`) in history — cosmetic, no action needed.
- **Uncommitted / untracked at analysis time:** `Docs/plan/EXECUTION_ORDER.md` + `erp/imports/registry.py` modified (working tree); untracked `Docs/plan/delivery-readiness/` (new program docs — likely to commit), a `.modeer/` dir, and a large pile of `assistant/2026/07/data*.csv` import-test artifacts (cruft — should be gitignored/cleaned, not committed).
- **Docs vs code:** README's build-plan link points at a local `~/.claude/plans` path that won't resolve for other agents — the real plan authority is `Docs/plan/EXECUTION_ORDER.md`.

## Design Decisions & Business Rules

_Full log: `DECISIONS.md` (150KB+). Highlights:_

- **Category = ARP (Agentic Resource Planning)** — internal until the claims gate opens; publicly still "Arabic-first ERP." Scope authority = `Docs/ARP_STRATEGY.md`.
- **Customer-hosted, single-tenant** — not SaaS multi-tenancy; customer runs their own box (WhiteNoise/Waitress serve the SPA behind Django; no CDN, fonts/icons self-hosted).
- **AI = tool-use, never free-text-to-SQL; writes are human-in-the-loop; the AI runs AS the user** (its actions respect the user's RBAC). Optional at runtime — the app works with no API key.
- **Service-contract writes** — all mutations go through module service fns so RBAC + validation live in one place; import adapters and AI actions both obey this.
- **Money = integer minor units** on the wire; format/parse only at the edge.
- **Brand is build-blocking, not cosmetic:** tokens-only, logical-CSS-only, monochrome chrome (colour only inside pages, paired with word/icon), one type voice + one icon set, one canonical Arabic word per concept, designed states, settled motion, reduced-motion honoured.
- **Zero new dependencies without asking.**
- **One file = one session; a `_done` plan file is never reopened;** the plan folders are the progress bar (no separate tracker). Queue yields to the user always, then resumes where it was.
- **Delivery track supersedes the roadmap queue** while active (founder pivot 2026-07-15): ship to a real customer first, AI out of scope for now.

## How to Build / Run / Test / Deploy

```powershell
# --- Backend (repo root, venv Python 3.13) ---
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python manage.py migrate
.\.venv\Scripts\python manage.py seed_identity --demo-users; .\.venv\Scripts\python manage.py seed_accounting
.\.venv\Scripts\python scripts\seed_demo.py

# Run the full live dev env (Django :8000 + Vite :5173)
.\run-dev.ps1                     # login admin / Dev12345!

# --- Frontend (apps/web) ---
npm install
npm run dev                       # Vite
npm run build                     # tsc -b && vite build  (prebuild runs i18n parity)

# --- Gates (definition of done) ---
.\.venv\Scripts\python scripts\gates\_run.py all      # backend gates 00-15, must exit 0
cd apps\web; node scripts\check-i18n-parity.mjs; npx tsc -b   # frontend gates (use -b, not --noEmit)
python scripts\gates\gate03.py    # mechanical brand gate (repo root)
pytest erp\<app>                  # per-module backend tests

# --- Deploy ---
# Docker: Dockerfile + docker-compose.yml at repo root (customer-hosted, single-tenant)
```

**Environment requirements:** Windows dev box. Python 3.13 venv at `.venv`; Django settings
`config.settings.dev`. PostgreSQL 16 service `postgresql-x64-16` (app DB `erp`, role `erp`). Redis
at `redis://localhost:6379/0` (winget `Redis.Redis` or Memurai; must be running). Node 24 / npm 11.
`.env` at repo root (gitignored) — key NAMES: `DATABASE_URL`, `REDIS_URL`, `ANTHROPIC_API_KEY`
(optional), `GEMINI_API_KEY` (optional), JWT/2FA secrets. Demo login: `admin` / `Dev12345!`.

## Integrations & Services

- **PostgreSQL 16** — primary datastore (`psycopg` 3).
- **Redis + Celery** — task queue / async jobs / caching.
- **Egyptian Tax Authority (ETA)** — e-invoicing via the `erp/einvoice` module (VAT compliance).
- **Anthropic Claude + Google Gemini** — AI assistant providers, selected via API-key env vars; entirely optional (app runs fully without AI).
- **Cloudflare "Workers Builds"** — appears red on PRs #12/#13 but is pre-existing/ignored per `erp-status`.

## Database Overview

**Engine:** PostgreSQL 16 (Django ORM, `psycopg` 3). Schema is per-module (Django migrations in each
`erp/<app>/migrations/`). Core entities span the modules: users/roles/permissions (identity),
chart of accounts + journals + VAT (accounting), items/warehouses/stock (inventory),
customers/sales-orders/invoices (sales), suppliers/POs/GRNI (purchasing), leads (crm),
price lists (pricing), e-invoices (einvoice), workflows/forms definitions, immutable audit log.
Writes flow through module service contracts, not raw ORM. Money stored as integer minor units.

## Auth & API

- **Auth:** JWT (`djangorestframework-simplejwt`) + TOTP 2FA (`pyotp`); RBAC roles/permissions in `erp/identity`, enforced at the service-contract layer (`require_role` / `HasAnyRole`). AI actions run under the acting user's permissions.
- **API:** Django REST Framework across all modules; 48/48 non-AI endpoints verified correct in delivery-track Phase 0. Health (`GET /health` → `{ok:true}`) + `GET /system-check` (DB/Redis/storage).
- **API surface detail:** per-module DRF viewsets/routers under each `erp/<app>/`; the React SPA (`apps/web/src/api`) is the primary consumer.

## Quality: Testing, Performance, Security

- **Testing:** pytest + pytest-django per module (e.g. 206 imports tests); machine gates 00–15 (`scripts/gates/`) are the definition-of-done and are green. **No JS unit runner** — frontend rests on `tsc -b`, i18n parity, the brand gate, and the E2E harness (`Docs/testing/E2E_MASTER_PROMPT.md`, self-maintaining, runs daily). Live E2E verification is the current delivery-track focus.
- **Performance:** Redis caching + Celery async; AI gateway adds response caching (exact-match + semantic) and token/cost budgets; a `perceived-performance-plan` is filed (backlog). Frontend uses optimistic updates + hover-prefetch.
- **Security:** JWT + 2FA, RBAC at the service layer, immutable audit trail, correlation-ID structured logging, human-in-the-loop AI (no autonomous writes), tool-use only (no free-text-to-SQL). Secrets via gitignored `.env` (names only in `.env.example`). No secrets found in tracked files during this scan.

---

> 📄 Maintained by the `ag-project-md` skill. The **`erp-status` skill is the live source of
> truth** (recall via `/erp-resume`) — update it after meaningful changes; this file is the
> umbrella summary. Manual edits welcome; the skill preserves them.
