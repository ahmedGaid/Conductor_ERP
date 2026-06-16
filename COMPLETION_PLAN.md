# Conductor ERP — Completion Plan

> The road from "all five modules + VAT loop + e-invoicing + exports" to a **shippable, hardened,
> deployable** product. Ordered by dependency + business priority (Accounting is the priority-1
> module, so its depth lands first; deployment hardening is last).
>
> **Working rhythm (per the client's instruction):** each phase is one self-contained, gate-green,
> committable increment. After I finish a phase I **stop and ask you to test it**; once you confirm,
> I **commit + push** and **update `PROJECT_STATUS.md`** (the `/erp-resume` anchor) before starting
> the next phase. Every phase keeps the existing disciplines: strict module layout, money = integer
> minor units, cross-module only via `contracts/`, logical-CSS + tokens-only + i18n ar/en parity,
> and a green gate as the only sign-off.

Last updated: 2026-06-16.

---

## Track A — Accounting depth (finish the priority-1 module)

### Phase 1 — Fixed Assets + Depreciation  ✅ DONE (2026-06-16, committed)
New `erp/accounting` depth (asset sub-ledger, reuses `post_journal`).
- **Domain/models:** `FixedAsset` (code, name, category, acquisition cost minor, salvage minor,
  useful-life months, in-service date, status), `DepreciationEntry` (asset, period, amount, journal ref).
- **Services:** `acquire` (Dr Asset 1500 / Cr Cash|AP), `run_depreciation(period)` — straight-line,
  posts Dr Depreciation Expense (5100) / Cr Accumulated Depreciation (1590, contra-asset), idempotent
  per asset+period; `dispose` (derecognize cost + accumulated dep, book gain/loss vs proceeds).
- **Reports:** asset register + net book value roll-forward.
- **COA/seed:** add 1500 Fixed Assets, 1590 Accum. Depreciation, 5100 Depreciation Expense.
- **API + React:** `/api/accounting/assets` (+ run-depreciation, dispose); asset list / new / detail +
  a "Run depreciation" period screen. Export buttons on the register.
- **Gate:** extend gate05 — straight-line schedule correct, depreciation run balances + is idempotent,
  disposal gain/loss correct, NBV never below salvage.

### Phase 2 — Cost Centers (dimensional accounting)  ✅ DONE (2026-06-16, committed)
- `CostCenter` master; optional `cost_center_code` on journal lines (nullable ⇒ all existing posts
  unaffected). `post_journal` accepts a per-line dimension; P&L-by-cost-center report.
- API + React: cost-center master + a cost-center filter on the income statement.
- Gate: posting with a dimension still balances; the dimensional P&L sums to the un-dimensioned total.

### Phase 3 — Bank Reconciliation  ✅ DONE (2026-06-16, committed)
- `BankStatement` + `BankStatementLine`; match lines against `is_cash`-account GL lines (auto by
  amount+date, manual override); unreconciled report; post adjustment journals for bank-only items
  (fees/interest).
- API + React: import/enter statement, match screen, unreconciled list.
- Gate: a fully matched statement reconciles to the cash GL balance; adjustments post + balance.

### Phase 4 — Budgets + Budget-vs-Actual  ✅ DONE (2026-06-16, committed)
- `Budget` (fiscal year) + `BudgetLine` (account, period, amount minor). Budget-vs-actual report
  (variance vs the posted GL), with export.
- API + React: budget entry grid + variance report.
- Gate: variance = actual − budget per account/period; totals tie out.

## Track B — Operational depth

### Phase 5 — Inventory: stock counts/adjustments + batch/lot  ⬅ NEXT
- Physical **stock count** (snapshot → enter counted qty → post variance adjustment: Dr/Cr Inventory
  vs an adjustment account, keeping `Inventory GL == stock value`). Optional **batch/lot** field on
  movements with expiry, and a batch-balance view.
- API + React: count session screen, adjustment posting, batch report.
- Gate: a counted shortage posts a balanced adjustment and the GL-equals-stock-value invariant holds.

### Phase 6 — CRM: campaigns + ticket escalation
- `Campaign` (target segment, linked leads/opportunities, simple ROI = won value vs cost); **ticket
  escalation** — auto-bump priority/notify when an SLA is breached (event-driven, reuses the bus).
- API + React: campaign list/detail, escalation indicator + activity on tickets.
- Gate: campaign rolls up won value; a breached ticket escalates exactly once.

## Track C — Stage 6 finish (integrations & reporting)

### Phase 7 — Custom report builder + scheduled reports
- User-defined report definitions (pick accounts/dimensions/date range, save, run → table + CSV/XLSX
  via the existing `exports.py` renderer). Optional schedule (Celery beat) writing exports to disk.
- API + React: builder screen, saved-definition list, run/export.
- Gate: a saved definition runs deterministically and exports; schedule registers a beat task.

### Phase 8 — Integration adapters (email / WhatsApp / payment / bank import)
- Pluggable notification adapters behind one interface (email via SMTP first; WhatsApp/payment stubs
  like the ETA adapter — swappable, offline-safe). Wire invoice/ticket events to notifications.
- Gate: an event triggers the adapter through the interface; failures are bus-isolated.

## Track D — Frontend polish

### Phase 9 — Design charter backlog
- Per-report loading skeletons + SWR caching on the filtered statement screens; sticky table headers
  on long lists; density reduction via progressive disclosure on the busiest detail screens; empty
  states on the form+table reference screens. (gate03 stays green: tokens/logical-CSS/i18n parity.)

## Track E — Stage 7 (ship it)

### Phase 10 — Hardening (security + performance)
- Security pass (DRF throttling, prod CORS/CSRF/secure-cookie/HSTS settings, secret handling,
  dependency audit, RBAC coverage review), N+1/query-count checks on the heavy list endpoints,
  structured-log/correlation review, an error-catalog audit.
- Gate: a new `gate11` (security/settings assertions + query-count budgets on key endpoints).

### Phase 11 — Deployment packaging + runbook
- Production serving (Django serving the built React bundle behind WhiteNoise/IIS reverse proxy),
  Celery worker + beat as Windows services, `.env.prod` template, Postgres/Redis prod notes, the
  nightly-backup + tested-restore policy from DECISIONS, and an operator runbook (install, migrate,
  seed, start, upgrade). Final `gate:all` green = release candidate.

---

## Checkpoint protocol (every phase)
1. Build the slice; run `gate:all` until green.
2. **STOP — ask you to test** (I'll give the exact screens/commands to try).
3. On your OK: `git add` (excluding the untouched `erp_questionnaire_v4.html`), commit, push to `main`.
4. Update `PROJECT_STATUS.md` + `DECISIONS.md` + this file's progress, then start the next phase.
