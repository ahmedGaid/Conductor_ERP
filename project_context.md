# Conductor ERP — Project Context (Single Source of Truth)

> Repo audit at `C:\AhmedGaid\ERP`. Originally 2026-06-23; refreshed 2026-06-28. For an external AI
> Advisor. Reflects the **implemented** system, not the original brief. Live next-steps live in
> `PROJECT_STATUS.md` — this file is the stable overview.

**Brief vs. reality (read first) — corrections so the advisor isn't misled:**
- It is a **web app** (Django backend + React/Vite SPA), **not** Tauri/Electron/Rust desktop.
- DB is **PostgreSQL 16**, **not** SQLite-with-sync. **No offline/local-first sync layer.**
- **Single-tenant, customer-hosted** (one deployment per customer). **No multi-tenant row-level
  security**; isolation is deployment-level, with branch/department/team *scoping* inside a tenant.
- Well past "system of record before AI": all five modules + accounting/ops depth + VAT + ETA
  e-invoicing + reporting + notifications + full RBAC + hardening + deployment packaging are built —
  **release candidate**. AI features are deliberately out of scope.

## 1. Product
**Conductor** — customer-hosted, single-tenant ERP for **Egyptian SMBs**. **Arabic/RTL-first, bilingual
(ar/en)**. Replaces spreadsheets/legacy ERPs with one calm system that "keeps the books correct by
construction" (double-entry enforced, stock value tied to GL, trial balance always balanced).
- **Users:** non-technical Arabic-first ops staff (accountants, branch managers, sales/purchasing
  clerks, warehouse, CRM/support).
- **Brand:** *quiet, precise, trustworthy* — Linear/Telegram bar: near-black monochrome chrome,
  generous space, optimistic response, colour only to *mean* something (status, links, key figures).
- **Thesis (as implemented):** (1) correct-by-construction transactional core, AI later (no LLM
  wrappers present — deferral is real); (2) low-friction onboarding via idempotent seeds + a
  workflow/dynamic-forms engine (structure as data); (3) money = integer minor units + currency,
  cross-module access only via `contracts/`, every write auditable.

## 2. Tech stack
**Frontend** (`apps/web`, SPA, `HashRouter`): React 18 + TS + Vite. i18n via i18next, **1161 keys at
ar/en parity** (build-blocking, `scripts/check-i18n-parity.mjs`). Design-token system (`styles/
tokens.css` only place raw hex allowed), **logical CSS only** (RTL default), own single-stroke icon set,
IBM Plex Sans Arabic + Inter, no CDN/component/icon library. Primitives: optimistic mutations
(`lib/optimistic.ts`), hover-prefetch, toasts, SWR-style caching/skeletons, Arabic-insensitive search
(`lib/arabicSearch.ts`). Keyboard-first: ⌘K palette + global `g`+key nav, `j/k/Enter` list nav,
⌘/Ctrl+Enter submit / Esc cancel. **No JS unit-test runner** — JS gates are i18n parity + `tsc -b`.

**Backend:** Django (Python 3.13) modular monolith + DRF. JWT auth (rotation) + optional TOTP 2FA.
Celery worker+beat on Redis. REST over `/api/...` with a response envelope (`error_id` +
`correlation_id`). No WebSockets; OpenAPI deferred. Prod: single Django process via WhiteNoise (serves
API + DRF static + built SPA from `apps/web/dist`) on Waitress WSGI, fronted by IIS/Nginx for TLS;
Windows services (Conductor-Web/-Worker/-Beat) via NSSM.

**DB & tenancy:** PostgreSQL 16 (app DB `erp`, role `erp`). Single-tenant, customer-hosted — isolation
at the deployment boundary, not RLS. Inside a tenant, scoped by branch/department/team via core
abstract bases (`TimeStampedModel`, `AuditedModel`): UUID PK, timestamps + actor stamps, branch FK,
soft-delete. RBAC enforced in the API layer (`HasAnyRole`), roles = Django Groups.

**Repo/env:** `C:\AhmedGaid\ERP` (git, default `main`, remote `github.com/ahmedGaid/Conductor_ERP`).
Local: venv `.venv` (3.13); PostgreSQL service `postgresql-x64-16`; Redis auto-start `Redis` service;
Node 24 / npm 11. Backend `127.0.0.1:8000`; Vite dev `:5173` proxies `/api` (`run-dev.ps1` runs both).

## 3. Architecture & data flow
- **Client↔server, online request/response — not local-first.** SPA authenticates via
  `POST /api/identity/login` → JWT pair (or `{twofa_required}`), then calls REST with the access token;
  `me` returns user + roles + branch. PostgreSQL is the sole source of truth. The "instant" feel is
  **optimistic UI** (latency-hiding over a live server), not offline persistence.
- **Module boundaries:** no module reads/writes another's tables; cross-module calls only via the
  target's public `contracts/` (gate-enforced).
- **Workflow/forms engine:** stored node graphs (`Workflow`/`Node`/`Edge`) executed deterministically
  server-side with per-node executions, idempotency, execution log; dynamic `FormDefinition` (JSON
  schema) → `FormSubmission` can trigger a workflow. The data-driven "structural" layer.
- **Auditing:** business writes append immutable `audit_entry` (actor, module, action, entity,
  before/after JSON, result, correlation id). **Events:** internal bus decouples side effects
  (notifications, ticket escalation), bus-isolated failures.

## 4. Feature status (✅ built · 🟡 partial · ⬜ absent)
- **Structural engine:** ✅ workflow engine · ✅ dynamic forms · ✅ idempotent seeds (`seed_accounting`
  COA+fiscal year+12 periods, `seed_identity` roles/users, standalone `seed_demo.py`). ⬜ industry-
  specific *template library* (current seeding is one general baseline — closest gap to the brief).
- **Financial ledger:** ✅ double-entry GL (`post_journal`; typed hierarchical `Account`,
  `JournalEntry`/`Line`, `FiscalYear`/`Period`, `TaxCode`) · ✅ statements + saved report builder
  (CSV/XLSX, optional beat scheduling) · ✅ depth (Fixed Assets + depreciation/disposal, Cost Centers,
  Bank Rec, Budgets + variance) · ✅ output **and** input VAT · ✅ immutable audit trail.
- **Modules:** ✅ Inventory (Item/Category/Warehouse/StockMovement/Balance + stock counts + batch/lot;
  invariant *GL == stock value*) · ✅ Sales (Customer, Quotation→SalesOrder) 🟡 standalone AR-invoice
  *document* is thin (revenue posts via accounting — verify before relying) · ✅ Purchasing
  (Supplier, PR→PO, simulated external target) · ✅ CRM (Lead/Opportunity/Activity/Ticket w/ SLA
  escalation/Campaign ROI) · ✅ E-invoicing (ETA adapter, offline-safe; notification adapters: email
  live, WhatsApp/payment stubbed) · ✅ Notifications.
- **Frontend UX:** ✅ keyboard systems + navigation + designed states + density/inline-edit + palette
  recents + brand triad + Arabic search — **all merged to `main`** (PRs #1–#11).
- **Growth (in progress, branch `growth/combined`):** ✅ Setup Wizard (PR #14 open) · ✅ CSV import
  (Customers/Suppliers/Items) · ✅ smart defaults · ✅ Pricing engine P1–P4 (Oracle-EBS-core: lists +
  tiers + per-customer + effective dates + tax-inclusive resolver, API + UI + bulk import) · ✅ module-
  identity headers + party drill-down (customer/supplier → ledger; `JournalEntry.party`). Next: Pricing
  P5 (per-customer assignment/override UI).
- **Cross-cutting:** ✅ RBAC, monitoring (`/health`, `/system-check`), hardening (throttles, TLS/HSTS/
  CORS/cookies, N+1 fix), deployment packaging (WhiteNoise + Waitress + NSSM + backup/restore + runbook).

## 5. Schema summary
UUID PKs throughout; business tables carry created/updated + actor stamps, branch (+dept/team) scope,
soft-delete via core abstract bases. Money = integer minor units + currency. Ownership per-module.

| Module | Primary models |
|---|---|
| **core** | `Branch`; abstract `TimeStampedModel`, `AuditedModel` (scoping + actor stamps) |
| **identity** | `User` (email-unique, TOTP), `UserPreferences`, `Department`, `Team`; roles = Django Groups |
| **audit** | `AuditEntry` (immutable, append-only) |
| **accounting** | `Account` (self-ref hierarchy, typed), `FiscalYear`, `Period`, `JournalEntry`/`Line` (line→Account, optional CostCenter, **optional party**), `TaxCode`, `CostCenter`, `FixedAsset`, `DepreciationEntry`, `BankStatement`/`Line`, `Budget`/`Line`, `ReportDefinition` |
| **inventory** | `Item`, `Category`, `Warehouse`, `StockMovement`, `StockBalance`, `StockCount`/`Line` |
| **sales** | `Customer`, `Quotation`/`Line`, `SalesOrder`/`Line` (quotation→order) |
| **purchasing** | `Supplier`, `PurchaseRequest`/`Line`, `PurchaseOrder`/`Line` (PR→PO; external mirror, unique idempotency_key) |
| **pricing** | `PriceList`, `PriceListLine`, `CustomerPriceList`, `CustomerItemPrice` (precedence resolver) |
| **crm** | `Lead`, `Opportunity`/`Line`, `Activity`, `Ticket`, `Campaign` |
| **einvoice** | `ETAInvoice` (via ETA adapter) |
| **notifications** | `Notification` |
| **workflow** | `Workflow`, `WorkflowNode`, `WorkflowEdge`, `WorkflowInstance`, `NodeExecution`, exec log, idempotency |
| **forms** | `FormDefinition` (JSON schema, optional `trigger_workflow`), `FormSubmission` |

## 6. Limitations & next milestones
**Risks:** AR customer-invoicing *document* depth thin (§4) — verify before positioning as full ·
single-process scaling (one Django/Waitress per customer + Celery; no horizontal-scale/load-balanced
story; no realtime/WebSockets) · OpenAPI/Swagger deferred (contract only in `architecture/api.md`) ·
no JS test runner (frontend "done" = i18n parity + `tsc -b` + brand gate + manual checklist) ·
deferred hardening (broader query-count budgets, dependency-vuln audit, error-catalog audit) ·
reboot fragility: `Redis` service not auto-starting reddens `gate:00` (`Start-Service Redis`).
**Next:** finish Growth (Pricing P5, then merge `growth/combined` → `main`; land PR #14) · keep
`gate:all` 00–13 GREEN · exercise deployment packaging end-to-end per `Docs/RUNBOOK.md` · backlog:
machine-generated OpenAPI, JS test-runner decision, broader query budgets, dependency-vuln audit.

### Source-of-truth pointers
Live status → `PROJECT_STATUS.md` · decisions → `DECISIONS.md` · completion plan → `COMPLETION_PLAN.md`
· brief & brand → `PRODUCT.md`, `Docs/Brand/` · architecture → `architecture/*.md` · runbook →
`Docs/RUNBOOK.md`.
</content>
