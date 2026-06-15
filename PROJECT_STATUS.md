# PROJECT STATUS — Conductor ERP (Django)

> Living resume anchor. The `/erp-resume` skill reads this file. Keep it updated after every
> meaningful step. Last updated: **2026-06-15 (Stages 0–5b + Inventory (5c) + Sales (5d); gate:all 00–07)**.

## PRODUCT NAME
The ERP is branded **"Conductor"** (wordmark + logo tile "C", browser title, i18n `app.title` in both
locales; the localized "ERP" phrase is the tagline). Design reference adopted from
`C:\AhmedGaid\ERP\files\preview.jpg` (modern dashboard: icon sidebar, command-bar topbar, KPI cards
with deltas, panels, status pills). Keep the UI at that bar — modern, clean, RTL-first — as we go.

## CURRENT POSITION
**Stages 0–4 + Accounting (GL core + statements + screens) + UI rebrand to "Conductor" + Inventory
(5c) + Sales (5d) COMPLETE — `gate:all` (00–07) is GREEN.** No active blocker.
Next options: **start Purchasing** (next priority: PR→PO→GRN→bill→payment, 3-way match; mirrors
Sales and clears GRNI), **deepen Inventory/Accounting/Sales**, or **CRM**. See plan.

Stage 5d delivered (`erp/sales`, gate07): the **Sales & Customers** order-to-cash module — the
clearest cross-module flow. It drives Inventory + Accounting **only via their public contracts**
(boundary enforced by gate07). Models: Customer (credit limit), SalesOrder, SalesOrderLine (items
referenced by SKU string, warehouse by code — no cross-module FKs). `services/orders.py` lifecycle
`draft→confirm→deliver→invoice→payment`: confirm enforces credit limit; deliver calls
`inventory.contracts.issue` per line (reduces stock + posts Dr COGS/Cr Inventory at weighted-avg);
invoice posts Dr AR(1100)/Cr Revenue(4000) via `accounting.contracts.post_journal`; payment posts
Dr Cash(1000)/Cr AR. Proven: full flow keeps the **trial balance balanced**, Inventory GL still ==
stock value, credit/oversell/overpayment guards. DRF API `/api/sales/` behind RBAC (Branch Manager);
11 tests. React screens (Orders, New order w/ cross-module item+warehouse pickers, Order detail with
confirm/deliver/invoice/payment actions, Customers); "Sales" now an active sidebar module.

Stage 5c delivered (`erp/inventory`, gate06): the **Inventory & Warehouses** module in the strict
layout, posting to the GL **only via `erp.accounting.contracts`** (module boundary enforced by
gate06). `domain/costing.py` = exact **weighted-average** (Decimal qty + integer-minor value; issue
cost taken proportionally so running value never drifts). Models: Category, Item, Warehouse,
StockBalance, StockMovement. `services/stock.py` receive/issue/transfer — atomic balance + movement
+ GL: receipt Dr Inventory(1200)/Cr GRNI(2150), issue Dr COGS(5000)/Cr Inventory, transfer no GL;
publishes `inventory.Stock*` events. Oversell rejected (`INV-001`). **Core invariant proven: the
Inventory GL account balance always equals total stock value.** DRF API `/api/inventory/` (items,
categories, warehouses, movements receive/issue/transfer, reports/stock-on-hand) behind RBAC (Branch
Manager). 16 tests. React screens (Stock on hand, Items, Warehouses, Stock movement w/ receive/
issue/transfer segmented form) added; "Inventory" now an active sidebar module. Seed: `seed_accounting`
now also creates GRNI (2150).

Stage 5b-2 delivered (gate05): **financial statements** from the posted GL —
`services/statements.py` `income_statement` (revenue−expense over a date range/period),
`balance_sheet` (assets vs liabilities+equity+net income; **always balances** because the ledger
does), `cash_flow` (movement of `is_cash` accounts; opening+in−out=closing and **reconciles** to the
cash GL balance). New `Account.is_cash` flag (migration 0002, seed marks Cash/Bank). Endpoints
`/api/accounting/reports/{income-statement,balance-sheet,cash-flow}`. React screens (Income
Statement, Balance Sheet, Cash Flow) added to the accounting sub-nav. 7 statement tests
(net income, BS balances incl. with a liability, cash-flow reconciles) — accounting suite now 31.
Note: AR/AP aging deliberately NOT built — needs per-customer/vendor open-item sub-ledgers from
Sales/Purchasing; faking it from GL balances would be wrong.

UI overhaul (gate03 build still green): modern token set (slate neutrals, near-black brand, subtle
shadows), redesigned app shell (logo + grouped module nav incl. roadmap "coming" items + user
footer; command-bar topbar with search + actions), redesigned dashboard (time-based greeting, 4 KPI
cards with month-over-month deltas, Top Expenses + Cash Flow panels, recent journals, shortcuts
rail), restyled buttons/cards/tables/status pills, new `StatCard` component, branded login. All
logical-CSS + tokens-only + i18n-parity disciplines still enforced.

Stage 5a delivered (`erp/accounting`, gate05): the **General Ledger core** in the strict module
layout `{domain,repositories,services,contracts,events,api,tests,docs}`. `domain/money.py` =
integer-minor-unit `Money` value object (no floats anywhere in the ledger; default EGP).
`domain/accounts.py` = 5 account types + normal-balance/signed-balance rules. Models: Account (COA
hierarchy, postable flag), FiscalYear, Period (open/closed lock), JournalEntry, JournalLine (DB
check constraints: non-negative, not-both-sides). `services/posting.post_journal` is the single
double-entry invariant point — atomic, balanced (debits==credits, total>0), ≥2 valid lines,
postable accounts only, open period only; stamps posted, writes an immutable audit row, publishes
`accounting.JournalPosted`; `reverse_journal` mirrors (never edit a posted entry).
`services/reports` = trial balance (always balances) + general ledger (running signed balance).
DRF API at `/api/accounting/` (accounts, fiscal-years, periods + close, journals post/list/detail,
reports/trial-balance, reports/general-ledger) behind RBAC (Accountant/Branch Manager). 24 tests
(money, posting invariants, reports, API, RBAC). Dev seed: `manage.py seed_accounting` (baseline
COA + current FY + 12 open monthly periods). Note: `models.py` re-exports from `domain/models.py`
so Django discovers them while keeping the strict layout.

Stage 5b (frontend, gate05 extended) added the **React accounting screens** under `/accounting`
(sidebar "Accounting" + in-page sub-nav): Chart of Accounts (list + add), Journal Entry form
(dynamic lines, live debit/credit totals + balance guard, post), Journal list + detail, Trial
Balance (period filter, balanced indicator), General Ledger (account picker, running balance).
`lib/money.ts` formats/parses at the edge; integer minor units stay on the wire. i18n keys added
with ar/en parity. gate05 also asserts the screens exist and the entry form posts via the API +
guards balance client-side.

Stage 4 delivered (gate04): the **workflow/instance DRF API** + the **React platform screens**.
Backend (`erp/workflow/{serializers,services,views,urls}.py`, mounted at `/api/workflow/`):
list/create/retrieve/update workflows as a full graph (header + nodes + edges, edges referenced by
node **key** so a definition round-trips), `save_graph` upserts nodes by key (running instances
survive an edit) + bumps version, start instance, list/filter instances, instance detail (node-run
timeline + logs), approve/reject (re-enters the engine), dashboard metrics from real data. 9 API
tests (`erp/workflow/tests/test_api.py`) prove round-trip, lifecycle, node-level logs, metrics.
Frontend (`apps/web/src/`): JWT auth (`auth/AuthContext`) + login screen, typed API client
(`api/`), HashRouter, dashboard (real metrics), workflow list, **React Flow canvas** (`@xyflow/react`)
with palette + connect + node/edge inspector (`pages/canvas/NodeConfigPanel`) + save/run, and an
execution viewer (status pills, node timeline, input/output, node logs, approve/reject). The graph
keeps an LTR coordinate space inside an otherwise RTL-mirrored shell. gate03's full `npm run build`
+ i18n-parity + token/logical-CSS scans cover the new screens too.

Stage 3 delivered (`apps/web/`, gate03): React 18 + TS + Vite frontend, **Arabic/RTL by default**
(`index.html` lang=ar dir=rtl; i18next fallback `ar`), live AR↔EN switch that re-applies
`<html dir/lang>` on `languageChanged`. Design tokens (`src/styles/tokens.css`) are the single
hex source; all other styles use `var(--token)` + **logical CSS only** (inline-start/end, no
physical left/right). App shell = sidebar (inline-start) + command bar + language switcher; `<bdi>`
wrapper for LTR tokens. Self-hosted fonts via `@fontsource` (IBM Plex Sans Arabic + Inter, no cloud
dep). i18n **key-parity** enforced both directions: `scripts/check-i18n-parity.mjs` runs as
`prebuild` (build fails on missing key) and gate03 also proves it catches drift via a fixture.
Run frontend: `cd apps/web; npm install; npm run dev` (Vite proxies `/api` → :8000).

Stage 1 delivered: custom `User` (branch FK + TOTP), RBAC via Django Groups + `HasAnyRole` DRF
permission, JWT login with 2FA challenge flow (`/api/identity/*`), audit service (immutable, blocks
update/delete, correlation-stamped) wired into login, event-bus isolation, `/system-check` with
db/redis/storage/workers, `seed_identity` (roles, HQ branch, demo users `admin/manager/accountant/
auditor`, password `Dev12345!`). Tests in `erp/*/tests`, run via `gate01`.

Stage 2 delivered (`erp/workflow` + `erp/forms`, gate02): graph workflow engine — deterministic
edge selection (guards vs else-fallback), crash-resumable state machine (one DB txn per transition,
`select_for_update` on the instance row), external-write idempotency (`sha256(instance|node|attempt)`
ledger + DB UNIQUE `ON CONFLICT DO NOTHING`), node executors (Start/Condition/Approval/Script/
ApiCall/End), self-built JSON-logic (no eval/exec), `{{ctx.path}}` template resolver, REST/SQL/
Webhook adapters behind one interface, simulated `erp_external.purchase_orders` target via RunSQL.
`erp/forms` dynamic Forms Builder (definitions + submissions) triggering workflows. 23 Stage-2 tests
(crash-resume, idempotency, determinism, approval, edges, adapters, forms). gate02 also statically
bans unsafe SQL building, eval/exec, and `random.*` in the engine.

Run gates: `cd C:\AhmedGaid\ERP; .\.venv\Scripts\python.exe scripts\gates\_run.py all`
Note: `erp` Postgres role granted CREATEDB (for pytest test DB).
Note: workflow/instance HTTP API (DRF endpoints) is built (Stage 4) under `/api/workflow/`.

## What this project is
Customer-hosted, single-tenant **Django modular-monolith ERP** (Python 3.13 + DRF), React+TS
frontend, Arabic/RTL-first. Built **foundation-first**, then ERP modules (Accounting → Inventory →
Sales → Purchasing → CRM).

- Full roadmap/plan: `C:\Users\Rw\.claude\plans\cd-c-ahmedgaid-erp-files-read-thosse-bubbly-puddle.md`
- Decisions & rationale: `C:\AhmedGaid\ERP\DECISIONS.md`
- Source specs (input only): `C:\AhmedGaid\ERP\files\`
- Repo root: `C:\AhmedGaid\ERP` (git initialized, branch `main`, no commits yet)

## Environment facts (local dev)
- Python: `C:\Users\Rw\AppData\Local\Programs\Python\Python313\python.exe` (3.13.14)
- Virtualenv: `C:\AhmedGaid\ERP\.venv` — deps from `requirements.txt` INSTALLED ✅
- Run python as: `C:\AhmedGaid\ERP\.venv\Scripts\python.exe`
- PostgreSQL 16: service `postgresql-x64-16` RUNNING ✅. Superuser `postgres` / password `postgres`.
  psql at `C:\Program Files\PostgreSQL\16\bin\psql.exe`.
- App DB: database `erp`, role `erp` / password `erp`, owns `public` schema. Login verified ✅.
- Node 24 + npm 11 installed ✅ (for frontend, Stage 3+).
- Redis: `redis://localhost:6379/0` via winget `Redis.Redis` (MS port). Service `Redis` RUNNING
  (auto-start), `redis-cli ping` → PONG. `redis-cli` at `C:\Program Files\Redis\redis-cli.exe`.
  (Memurai failed — see DECISIONS.md.)
- `.env` exists at repo root (gitignored) with DATABASE_URL/REDIS_URL set.

## Toolchain install status
| Tool | Status |
|---|---|
| Python 3.13 | ✅ installed |
| Node LTS + npm | ✅ installed |
| PostgreSQL 16 | ✅ installed + DB/role created + migrated |
| Memurai (Redis) | ❌ BLOCKED — see below |

## ACTIVE BLOCKER → do this first on resume
Memurai (Redis) install via winget hung on a UAC elevation prompt; killing it left Windows Installer
in a stuck **error 1618 ("another installation in progress")** state. The fix chosen: **reboot the
machine** (clears 1618). After reboot:

1. Reinstall Memurai:
   ```
   winget install --id Memurai.MemuraiDeveloper -e --silent --accept-source-agreements --accept-package-agreements
   ```
   (If a UAC prompt appears, user approves it. If 1618 returns, the reboot didn't fully clear — retry once.)
2. Confirm the Memurai service is running and Redis answers:
   ```
   Get-Service *memurai*
   C:\Program Files\Memurai\memurai-cli.exe ping   # expect PONG
   ```
   (Memurai listens on 6379 by default, Redis-compatible.)
3. Run gate 00 (must print `GATE 00 PASSED`):
   ```
   cd C:\AhmedGaid\ERP
   .\.venv\Scripts\python.exe scripts\gates\_run.py 00
   ```

If Memurai still cannot install, fallback: install `Redis.Redis` via winget, OR (last resort) run
Celery eager + relax gate00's Redis check, recording it in DECISIONS.md.

## Stage 0 progress (scaffold & gate)
DONE:
- Repo + git init; `.gitignore`, `.env.example`, `.env`, `requirements.txt`, `pyproject.toml`, `README.md`.
- Django config package `config/` (settings base/dev/prod, `urls.py`, `wsgi/asgi`, `celery.py`).
- Modules: `erp/core` (correlation, structured JSON logging, errors+catalog, exceptions, event bus,
  repository base), `erp/identity` (custom `User` model), `erp/audit` (immutable `AuditEntry`),
  `erp/monitoring` (`/health` + `/system-check`).
- Gate harness `scripts/gates/_run.py` + `scripts/gates/gate00.py`.
- `DECISIONS.md`, `architecture/` skeleton (modules, dependencies, events, database, api, workflows,
  error-catalog), `scripts/sql/bootstrap_db.sql`.
- Migrations created AND applied to Postgres ✅ (identity.User, audit.AuditEntry, Django core).

REMAINING for Stage 0:
- Get Redis up (blocker above) and make `gate:00` pass green.
- Then: `git add -A && git commit` the Stage 0 baseline (only when user asks / after gate green).

## Next stages
- **Stage 5b — DONE (frontend accounting screens).** Remaining Accounting depth (**Stage 5b-2, NEXT
  option**): cost centers, tax codes + ETA e-invoice records, bank accounts + reconciliation,
  budgets, fixed assets + depreciation, and the statement suite (Income Statement, Balance Sheet,
  Cash Flow, AR/AP aging, VAT return). Reuse the GL core's `post_journal`.
- **Stage 5c+ — remaining modules:** Inventory → Sales → Purchasing → CRM, each isolated under
  `erp/` in the strict `{api,domain,services,repositories,contracts,events,tests,docs}` layout,
  reusing engine + audit + events + i18n + RBAC + the accounting `contracts` (post to GL via events).
  Per-module gate = its acceptance criterion (e.g. posting an invoice atomically updates stock + AR
  + GL). Money always integer minor units + currency.
- Stage 6 — integrations/reporting/exports. Stage 7 — hardening/deploy. (See plan.)

## How to resume
Read this file + the plan + `DECISIONS.md`, clear the active blocker, run `gate:00`, then continue
the roadmap. Update this file as steps complete.
