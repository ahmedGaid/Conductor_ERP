# PROJECT STATUS — Conductor ERP (Django)

> Living resume anchor. The `/erp-resume` skill reads this file. Keep it updated after every
> meaningful step. Last updated: **2026-06-19 (Stages 0–5f + Sales/Purchasing depth (5d-2..4/5e-2..4)
> + Accounting VAT output (5b-4) + input/purchase VAT (5b-5) + ETA e-invoicing (Stage 6a) + report
> exports (Stage 6b) + COMPLETION_PLAN Phases 1–8: Fixed Assets + Depreciation, Cost Centers, Bank
> Reconciliation, Budgets, Inventory counts/adjustments + batch/lot, CRM campaigns + ticket
> escalation, custom report builder + scheduled reports, notification/integration adapters
> (email/WhatsApp, event-wired) + context help on every page (bilingual ar/en); gate:all 00–11
> GREEN. Latest pushed commits: ef6a9a3 (Phase 8 notifications), a420fde (context help))**.
>
> **Resume note (2026-06-19, later session):** Phase 9 frontend-polish has progressed past the
> commits above — pushed since: `b779ebe` (in-page link colour), `5c81c4a` (sticky list headers +
> empty states), `79a5ca6` (whole-app polish: module header bands + detail-page progressive
> disclosure), `0bbb744` (real command bar: ⌘K palette + contextual help + **notifications
> relocated to a topbar bell**). That relocation broke **gate11** (it hard-checked the *sidebar* for
> the notifications link); gate11 was updated to accept the notifications top-level wiring at its new
> home (command-bar bell / ⌘K palette / sidebar).
>
> **Phase 9 COMPLETE + COMMITTED** — commit **`b2bb341`** (pushed to `main`, 2026-06-20) bundles:
> 1. **Reconciled the two external UX-tips docs** into the design directive backlog (one source of
>    truth — NOT a second charter). Adopt / Adopt-with-change / Defer split.
> 2. **Data-into-meaning:** Dashboard **"Needs attention today"** panel (`DashboardPage.AttentionPanel`)
>    — pending sales/PO approvals, outstanding receivables/payables, SLA-breached tickets, failed
>    messages; cross-module fetches `.catch(()=>[])` so a role without access can't break the dashboard.
> 3. **Human-language statuses:** plain-language status line on sales/purchasing **order-detail** pages.
> 4. **Progressive disclosure:** Quotation + Purchase-Request detail now lead with Total + primary
>    action; secondary meta behind a "Details" `Disclosure` (matches order/PO).
> 5. **Dark mode** (full): token remap under `:root[data-theme="dark"]` (pure-black), toggle in command
>    bar + login, no-FOUC init in `index.html`, persisted to `localStorage["erp.theme"]`.
> 6. **gate11 fix:** accept notifications wired via the command-bar bell / palette.
> A monochrome "Uber" restyle was tried this cycle and **fully reverted** at the user's request (not in
> the commit). **Known follow-ups (not blocking):** React-Flow workflow canvas isn't dark-themed;
> "context before action" on primary buttons. Stray dev artifacts (outside the repo / git-ignored):
> `C:\Users\Rw\pw-verify\` (temp Playwright harness); background Django :8000 + Vite dev servers from
> verification; uncommitted `erp_questionnaire_v4.html` (user edit) + `Images/` were deliberately
> excluded from the commit.
>
> **Phase 10 — Hardening DONE + COMMITTED** (2026-06-20): DRF rate limiting (anon/user, env-tunable;
> off in dev/test), prod hardening (HSTS/SSL-redirect/proxy-header/CSRF-trusted-origins/env-CORS/secure
> cookies/secret-required), journals-list N+1 fixed via `Prefetch`. New **gate12** = `manage.py check
> --deploy --fail-level WARNING` (prod) + a real 429 throttle test + a journals query-budget test;
> `ALL_GATES` now 00–12, all GREEN. See COMPLETION_PLAN Phase 10.
>
> **NEXT: Phase 11 — Deployment packaging + runbook (Track E, the final phase).** Django serving the
> built React bundle (WhiteNoise/IIS), Celery worker + beat as Windows services, `.env.prod` template,
> Postgres/Redis prod notes, nightly-backup + tested-restore policy, operator runbook (install/migrate/
> seed/start/upgrade). Final `gate:all` green = release candidate.

## COMPLETION PLAN (road to ship)
A phased plan to finish everything is in **`COMPLETION_PLAN.md`** (11 phases across accounting depth →
operational depth → Stage 6 finish → frontend polish → Stage 7 hardening/deploy). **Working rhythm:**
each phase is one gate-green committable increment; after each, the user tests, then we commit + push
and update this file. **Phases 1–4 (Track A, accounting depth) + Phases 5–6 (Track B, operational
depth) + Phase 7 (Track C, custom report builder + scheduled reports) DONE** (Fixed Assets +
Depreciation; Cost Centers; Bank Reconciliation; Budgets; Inventory counts/adjustments + batch/lot;
CRM campaigns + ticket escalation; custom report builder + scheduled reports; notification/integration
adapters — all committed). **Phase 9 — Design charter backlog (frontend polish, Track D) IN PROGRESS:**
list-polish landed (sticky headers on every module's long lists via one global `[class$="-table-wrap"]`
rule; empty states on the 5 reference screens — Accounts/Items/Warehouses/Customers/Suppliers;
skeletons + SWR confirmed already universal). **Remaining:** density / progressive-disclosure on the
busy detail pages — to be done with the **impeccable** design skill (now installed) translated into our
tokens. **impeccable is active** as a Skill + a PostToolUse design hook that scans edited frontend files.

**UI colour preference (durable — applies to ALL future UI work):** keep the near-black **"Uber-style"
app chrome** (brand / background / primary buttons / logo / active nav) **exactly as-is**; add colour
**only inside page content** (text, links). An indigo-brand experiment was tried and **rejected +
fully reverted**. **Committed:** links are now blue app-wide — `global.css` `a` uses `--color-accent`
(hover `--color-accent-strong` + underline), a new `--color-accent-strong` (`--palette-brand-700`)
token, help-drawer related-links use the accent. Further in-page colour is done **directly** (reconcile
into `tokens.css` — hex only there — via `var()`, keep gate03 green: logical CSS + ar/en parity).
**impeccable** (pbakaus' design plugin) **cannot load in this VS Code environment** — `/plugin` is
unsupported so `/impeccable` never registers; to use it, `npx skills add pbakaus/impeccable` in an
external terminal + full Claude Code restart.

Phase 8 delivered (new module `erp/notifications`, gate11): **integration adapters.** Pluggable
outbound-message channels behind one interface (`NotificationAdapter.send`): an **email** adapter
(Django email framework — offline-safe console backend by default, SMTP via `EMAIL_BACKEND` env in
prod) and a deterministic **WhatsApp** stub (like the ETA adapter; payment/bank gateways slot in the
same way). A `dispatch` service resolves the channel via `get_adapter(...).send(...)`, writes exactly
one `Notification` log row per attempt, and **never propagates a send failure** (records `failed`,
publishes a Failed event). Event-wired + decoupled: subscribes to `sales.OrderInvoiced` (emails the
customer) and `crm.TicketEscalated` (WhatsApp alert) by event **name** — neither module knows
notifications exist, and the bus isolates a broken channel from invoicing/escalation. DRF
`/api/notifications` (log list/filter + resend) behind auth/Branch-Manager; React **Notifications**
sidebar section (delivery log, status filter, resend, export). 12 tests; gate:all 00–11 green. Demo
seeds a sent + a failed row.

Context help on every page (out-of-band feature, gate03 extended): a floating "?" button mounted once
in the app shell (`src/help/HelpCenter.tsx`) opens a **bilingual (ar/en) slide-in guide** for the
current route — purpose, how it works, every field/button, step-by-step tasks, examples, tips, common
mistakes, and links to related pages. Guides are plain-language (non-technical) and live in
`src/help/content/*` keyed by route in `src/help/registry.ts` (matchPath resolves the active page,
most-specific first); content is outside the i18n JSON so prose doesn't bloat the parity files. gate03
now **fails the build if any App.tsx route lacks a guide**, so help stays in sync as pages are added.
All ~54 routes covered.

Phase 7 delivered (extends gate05): **custom report builder + scheduled reports.** Saved
`ReportDefinition`s (account-type and/or explicit account-code filters, date range, **group by account
or by period**) run deterministically over the **posted GL** via `report_builder.run_definition` →
`BuiltReport` (account grouping uses `signed_balance` in each account's normal direction; period
grouping nets debit−credit) and export to CSV/XLSX through the existing `exports.py` renderer. Optional
**schedule** (daily/weekly/monthly): a Celery beat task `accounting.run_scheduled_reports` (registered
in `CELERY_BEAT_SCHEDULE`, hourly tick) calls `run_scheduled(now)`, which itself decides due-ness
(`is_due`), writes each due report's CSV to `REPORTS_DIR` (= `STORAGE_ROOT/reports`, gitignored), and
stamps `last_run_at` — so it is **offline-safe and idempotent** (a second sweep in the same window
writes nothing). DRF `/api/accounting/report-definitions` (CRUD + `/<id>/run` → JSON or
`?export=csv|xlsx&lang=`); React **Report builder** screen (create form + saved-definition list with
Run/Delete + inline results table + export toolbar), new accounting sub-nav tab; ar/en parity. 6 new
tests; gate:all 00–10 green. Demo seeds 3 definitions (Revenue by account, Expenses by account,
Activity by period [monthly]).

Phase 6 delivered (extends gate09): **CRM campaigns + ticket escalation.** `Campaign` master; leads +
opportunities carry an optional `campaign_code`. `campaign_metrics` rolls up won-opportunity value vs
campaign cost into ROI (+ open pipeline, counts). Ticket SLA escalation: `escalate_ticket` bumps a
breached/open/un-escalated ticket up one priority **exactly once** (`escalated_at` guard), logs a
notify Activity, publishes `crm.TicketEscalated`; `run_escalations` sweeps (idempotent). DRF
`/api/crm/campaigns` (+ status/metrics), ticket `escalate` + `tickets-run-escalations`; React Campaigns
list/detail + Tickets escalate action/indicator + run-escalations; ar/en parity. 7 new tests; gate:all
00–10 green. Demo seeds a campaign (won 15k vs cost 12k) + a breached ticket.

Phase 5 delivered (extends gate06): **Inventory stock counts/adjustments + batch/lot.** `StockCount` +
`StockCountLine` snapshot system quantities; posting reconciles each counted line via a new
`adjust_stock` (shortage → Dr 5900 Inventory Adjustment / Cr 1200 Inventory at weighted-avg; overage →
Dr 1200 / Cr 5900), posting through the accounting **contract** so **Inventory GL == stock value holds
through adjustments**. Batch/lot: optional `batch_no` + `expiry_date` on receipts + a batches
(received-qty + earliest-expiry) report (issues stay weighted-average — traceability only). DRF
`/api/inventory/counts` (+ set-line/post), `/reports/batches`, batch receive fields; React Stock counts
list/new/detail + Batches tabs, batch/expiry on the receive form; ar/en parity. 7 new tests; gate:all
00–10 green. New account 5900. Demo seeds a batched receipt + open count.

Phase 4 delivered (extends gate05): **Budgets + Budget-vs-Actual.** `Budget` (per fiscal year) +
`BudgetLine` (planned amount per account+period; upsert, zero deletes). `budget_vs_actual` compares the
plan to the posted GL over a period or the whole fiscal year; **variance = actual − budget** and the
totals tie out. DRF `/api/accounting/budgets` (+ set-line, `/variance` with `?period=` and CSV/XLSX
export); React Budgets list/create + detail (line-entry form + variance table, period filter, export);
ar/en parity. 5 new tests; gate:all 00–10 green. `ACC-013` validates fiscal year/account. Demo seeds a
current-year operating plan.

Phase 3 delivered (extends gate05): **Bank Reconciliation.** `BankStatement` + `BankStatementLine`
reconciled against a cash GL account; statement amounts are signed (+deposit/−withdrawal). `auto_match`
pairs statement lines to unmatched posted cash GL lines of equal signed amount (a GL line claimed once
only); manual match/unmatch override. Bank-only items (fees/interest) are booked via `post_adjustment`
(balanced journal through `post_journal`, auto-matched). `reconciliation()` gives book vs statement,
the difference, and the outstanding-item lists; `mark_reconciled` locks only on a strict tie-out
(`ACC-012` otherwise). DRF `/api/accounting/bank-statements` (+auto-match/adjustment/reconcile/
candidates, line match/unmatch); React statement list/new + detail match screen; ar/en parity. 6 new
tests; gate:all 00–10 green. New account 6100 Bank Charges; demo seeds a ready-to-reconcile statement.

Phase 2 delivered (extends gate05): **Cost Centers — a dimensional reporting tag.** A `CostCenter`
master + an optional, nullable `cost_center_code` on each `JournalLine` (purely additive — existing
posts/tests untouched). `post_journal` validates the code (`ACC-009` on unknown/inactive, writes
nothing) and reversals carry it through. **Income statement is filterable by cost center** (= the
P&L-by-cost-center report; per-center slices sum to the un-dimensioned total). DRF
`/api/accounting/cost-centers` + `?cost_center=`; React Cost Centers master tab, per-line cost-center
picker on the journal-entry form, cost-center filter + export on the Income Statement; ar/en parity.
4 new tests; gate:all 00–10 green. Seeds CC-SALES/CC-OPS/CC-ADMIN. (Sales/Purchasing don't stamp a
cost center yet — deferred; manual entries can tag lines today.)

Phase 1 delivered (extends gate05): **Fixed Assets + Depreciation.** A fixed-asset sub-ledger
(`erp/accounting`, models `FixedAsset` + `DepreciationEntry`) where acquisition, monthly straight-line
depreciation, and disposal all post through `post_journal` (register/GL/trial-balance can't diverge).
Depreciation run is **idempotent per (asset, period)** and trues up the final period so NBV never drops
below salvage; disposal books a gain (4200) or loss (5400) vs net book value. Asset register report
(+CSV/XLSX export). DRF `/api/accounting/assets` (+ depreciation-run, dispose) + `reports/asset-register`;
React Fixed Assets register + detail/dispose screens (new Accounting sub-nav tab), ar/en parity. New COA
accounts 1500/1590/4200/5300/5400. 9 new tests; gate:all 00–10 green. Demo seeds FA-VAN + FA-LAPTOP.

## PRODUCT NAME
The ERP is branded **"Conductor"** (wordmark + logo tile "C", browser title, i18n `app.title` in both
locales; the localized "ERP" phrase is the tagline). Design reference adopted from
`C:\AhmedGaid\ERP\files\preview.jpg` (modern dashboard: icon sidebar, command-bar topbar, KPI cards
with deltas, panels, status pills). Keep the UI at that bar — modern, clean, RTL-first — as we go.

## CURRENT POSITION
**Stages 0–4 + Accounting (GL + statements + screens) + UI rebrand + Inventory (5c) + Sales (5d) +
Purchasing (5e) + CRM (5f) + the FULL Sales/Purchasing depth menu (5d-2/5e-2 returns + partial flows;
5d-3/5e-3 quotation/PR approval front-ends; 5d-4/5e-4 discounts + approval matrix) COMPLETE —
`gate:all` (00–09) is GREEN.** No active blocker.
**All five priority-order ERP modules are built**, the Sales/Purchasing depth menu is fully done, the
**Accounting VAT/tax** slice is in (**both output and input/purchase VAT — the VAT loop is closed**),
**ETA e-invoicing (Stage 6a)** has landed as a new module (now its own top-level UI section), and
**report exports (Stage 6b — CSV/Excel + browser print-to-PDF)** are live on every report. `gate:all`
now runs **00–10**. Next options: remaining **Stage 6** (a custom report **builder**, scheduled
reports, more integration adapters: WhatsApp/email/payment/bank); other accounting depth (fixed assets
+ depreciation, cost centers, bank reconciliation); inventory batch/serial/counts; CRM campaigns +
ticket escalation; then **Stage 7** (hardening/deploy). Repo is committed + pushed to
`github.com/ahmedGaid/Conductor_ERP` through the e-invoicing reorg (the exports increment is the next
to commit). See plan.

Stage 6b delivered (gate05 extended): **report exports.** A shared `erp/core/exports.py`
(`ReportTable` + `to_csv`/`to_xlsx` + `export_response`) renders any report to **CSV** (UTF-8 BOM) or
**XLSX** (openpyxl, RTL sheet for Arabic, real numeric money cells); the six accounting reports + the
e-invoices list serve downloads via **`?export=csv|xlsx&lang=…`** (param is `export`, since DRF
reserves `format`). **PDF = the browser's native print-to-PDF** (a `styles/print.css` + "Print / PDF"
button — perfect RTL, no fonts/deps). React: an authed `downloadExport` blob helper + a reusable
`<ExportButtons>` toolbar on every report screen; en/ar parity kept. 8 new tests (CSV/XLSX/auth/JSON
fallback). Only new dependency: **openpyxl** (pure-python, offline-safe).

Stage 5b-5 delivered (gates 05/08 extended): **input (purchase) VAT — the VAT loop closed.** `TaxCode`
gains `input_account_code` (default **1190 VAT Input/Recoverable**, asset; seeded + set on VAT14/VAT0,
exposed via the accounting contract). VAT is **opt-in per purchase order** (`tax_code`, blank ⇒
unchanged, so all pre-VAT purchasing tests stay green): the PO carries `tax_minor`, the **bill** posts
**Dr GRNI (net)/Dr VAT Input (vat)/Cr AP (gross)** (2-line when untaxed), `billed_minor` becomes gross,
and the **debit note reverses input VAT proportionally** (GRNI/AP/VAT-Input all net to zero on a full
return). **`vat_return` now nets output minus input** (`net_payable = net output − net input`; negative
⇒ refund position) — backward compatible (`input_vat = 0` on sales-only ranges). React: tax-code picker
+ live VAT on New PO, VAT on PO detail, input rows on the VAT-return screen; ar/en parity kept. 5 new
tests (bill books recoverable VAT, untaxed unchanged, debit-note reversal, vat_return nets output−input
in both purchasing + accounting). Demo seeds a billed VAT14 purchase (input VAT 280.00).

Stage 6a delivered (new module `erp/einvoice`, gate10): **ETA e-invoicing** — every posted sales
invoice becomes an `ETAInvoice` compliance record via a `draft → submitted → valid` lifecycle.
**Event-driven + decoupled:** `invoice_order` now publishes an **enriched `sales.OrderInvoiced`**
event (customer/date/tax/net/tax/total) and `erp.einvoice` subscribes (in `AppConfig.ready()`) to
record a draft — **Sales has no knowledge of e-invoicing**; gate10 forbids einvoice importing sales
internals, and the bus isolates subscriber failures from invoicing. References by business key (no
FK); `record_invoice` idempotent per invoice number. **Stubbed deterministic ETA adapter**
(`eta_adapter.py`, no network/cloud): `submit` assigns a UUID = the document's sha256 (idempotent
retries), `poll` validates; swapping a real client touches only that file. DRF `/api/einvoice/invoices`
(+ submit/poll) behind Accountant/Branch-Manager RBAC; 7 tests (record-via-bus, submit assigns UUID,
poll→valid, idempotent, untaxed still recorded, API lifecycle, auth). React **E-invoicing** is its
**own top-level sidebar section** (`/einvoice`, `pages/einvoice/` with its own nav — promoted out of
the accounting sub-nav so the UI mirrors the standalone backend module); ar/en parity kept.
(Input/purchase VAT has since landed — Stage 5b-5 above.)

Stage 5b-4 delivered (gates 05/07 extended): **VAT/tax on sales** — the first accounting-depth slice.
New `TaxCode` (rate in basis points; seed adds **VAT14** + **VAT0**, output → 2100 VAT Payable),
referenced by other modules only via the accounting **contract** (`find_tax_code`/`compute_tax`).
VAT is **opt-in per sales order** (`tax_code`): invoice posts **Dr AR (gross)/Cr Revenue (net)/Cr VAT
Payable (vat)** (2-line when untaxed, so all pre-VAT tests still pass); `invoiced_minor` becomes gross
so payments settle net+VAT; **returns reverse VAT proportionally**. New **VAT-return** report
(`vat_return` = output − reversals over a date range) + `/api/accounting/reports/vat-return` and
`/api/accounting/tax-codes`. React: tax-code picker + live VAT/grand-total on New order, VAT shown on
order detail, and a **VAT return** accounting screen. 10 new tests (tax compute, VAT invoice posts the
3-line entry + TB balanced, payment over gross, return reverses VAT, untaxed path unchanged, VAT
return totals). (Input/purchase VAT and ETA e-invoice records have since landed — see above.)

Stage 5d-4 / 5e-4 delivered (gates 07/08 extended): **line discounts (sales) + an amount-threshold
approval matrix at confirm (both modules)** — completing the depth menu. **Discounts:** each sales
order line has `discount_minor` off its gross; `line_total = round(qty*price) − discount`, order
subtotal is the net sum; the **invoice posts the net** to Revenue/AR (net method, no contra account)
and **returns now credit the net unit value prorated** (`line_total*ret_qty/qty`). Negative/over-gross
discount rejected (`SAL-013`). **Approval matrix:** `confirm_order` rejects (`SAL-009`/`PUR-009`) when
net value > 10,000.00 EGP and the order isn't approved; `approve_order` (Branch-Manager RBAC) stamps
approved/by/at and unblocks confirm; at/below threshold confirm is free. **Proven (8 new tests):**
discounted line_total/subtotal, invoice posts net + TB balanced, discounted return prorates,
above-threshold confirm blocked then approved on both modules. DRF: line `discount` input +
`discount_minor`/`approved`/`requires_approval` output + `/orders/{id}/approve` on both. React: New-order
discount column, order/PO detail Approve button + pending-approval indicator + discount column; ar/en
parity kept. `seed_demo.py` parks a discounted order + above-threshold pending-approval SO/PO.
**Header-level (order) discount and purchasing cost discounts deliberately deferred — see DECISIONS.**

Stage 5d-3 / 5e-3 delivered (gates 07/08 extended): **quotation & purchase-request front-ends with an
amount-threshold approval gate** — the pre-order documents from the spec, layered as a thin front-end
over the proven order lifecycle. New models `Quotation`/`QuotationLine` (sales) and `PurchaseRequest`/
`PurchaseRequestLine` (purchasing); **no GL posting** (nothing posts until the converted order runs its
normal flow). Lifecycle `draft → submit → approve/reject → convert`: **submit auto-approves at/below
10,000.00 EGP, else awaits an explicit approve** (`requires_approval` threshold, approver recorded);
**convert reuses `create_order`** so one document yields exactly one draft SO/PO (`converted_order_number`
recorded; re-convert blocked `SAL-012`/`PUR-012`; convert-before-approval blocked `SAL-010`/`PUR-010`).
**Proven (12 service + 3 API tests):** threshold auto-approve vs await, convert builds an order with the
matching subtotal, double-convert/reject/empty guards. DRF `/api/sales/quotations` +
`/api/purchasing/requests` (submit/approve/reject/convert; convert → 201 with order id+number) behind
Branch-Manager RBAC. React: Quotations / Purchase-requests list + new + detail (submit/approve/reject/
convert) pages, added as new Sales/Purchasing sub-nav tabs; ar/en i18n parity kept. `seed_demo.py` now
also parks demo quotations + PRs in each state.

Stage 5d-2 / 5e-2 delivered (gates 06/07/08 extended): **returns + partial fulfilment** on Sales &
Purchasing, built to exercise the GL/stock invariants. Inventory gained two contract methods —
`return_in` (customer return: stock back at weighted-avg, **Dr Inventory / Cr COGS**) and
`return_out` (supplier return: stock out, **Dr GRNI / Cr Inventory**) + two movement types; the
financial leg is posted by Sales/Purchasing (never one cross-module entry). **Sales:** partial
`deliver_order(delivered={line_no:qty})` accumulates to `partially_delivered`→`delivered`;
`return_order` (credit note) posts **Dr Sales Returns (4090, new contra-revenue acct) / Cr AR** and
reduces the receivable; `SAL-006/007/008`. **Purchasing:** `receive_order` now accumulates across
calls (`partially_received`→`received`); `return_order` (debit note) posts **Dr AP / Cr GRNI** so
GRNI nets to zero and AP drops; `PUR-006/007/008`. **Proven (50→62 module tests, all green):** every
flow keeps the **trial balance balanced**, **Inventory GL == stock value** through returns, GRNI back
to zero after a supplier return, and the excess/empty/wrong-status guards reject. DRF: new
`/orders/{id}/return` on both modules + partial-qty body on deliver/receive; serializers expose
`delivered_qty`/`returned_qty`/`returned_minor`/`credit_note_number`/`debit_note_number`. React: order
+ PO detail pages gained Return + "deliver/receive remaining" actions, returned columns, and credit/
debit-note display; ar/en i18n parity kept (gate03 build green). Seed/COA add account **4090**.

Stage 5f delivered (`erp/crm`, gate09): the **CRM** module — the relationship side of the ERP and the
last priority module. Models: Lead, Opportunity (+ OpportunityLine), Activity, Ticket. Services:
`leads.py` (capture → qualify → **convert** once into an opportunity, `CRM-002` on re-convert),
`pipeline.py` (`qualifying→proposal→negotiation→won|lost`; **win hands the deal to Sales via
`erp.sales.contracts.place_order`** — customer *code* + line inputs only, no sales ORM crosses the
boundary; records the SO number; `CRM-003` unknown customer, `CRM-004` no lines), `support.py`
(priority-driven **SLA** tickets — due time at open: urgent 4h/high 8h/medium 24h/low 72h, `is_breached`
when still open past due; `open→in_progress→resolved→closed`; plus activities log/complete). Sales
contract gained code-based `find_customer` + `place_order` for this. **Proven: a won opportunity
creates a draft sales order whose subtotal equals the opportunity amount, purely through the contract;
unknown-customer/empty wins rejected; ticket SLA breach computed from priority.** DRF API `/api/crm/`
(leads, opportunities, activities, tickets + lifecycle actions) behind RBAC (Branch Manager); 17
tests. React screens (Pipeline w/ inline new-opportunity, Opportunity detail w/ stage/win/lose, Leads,
Tickets w/ SLA breach indicator); "CRM" now an active sidebar module.

Stage 5e delivered (`erp/purchasing`, gate08): **Purchasing & Suppliers** procure-to-pay — mirrors
Sales and **closes the GRNI loop**. Models: Supplier, PurchaseOrder, PurchaseOrderLine (ordered vs
`received_qty`). `services/orders.py` lifecycle `draft→confirm→receive→bill→payment`: receive calls
`inventory.contracts.receive` per line (raises stock + Dr Inventory/Cr GRNI, supports partial GRN);
bill runs the **3-way match** (received==ordered per line, else `PUR-002`) then posts Dr GRNI/Cr AP
via `accounting.contracts` (clearing GRNI); payment posts Dr AP/Cr Cash. Proven: full flow leaves
trial balance balanced and **GRNI back at zero**, Inventory GL == stock value, 3-way match blocks a
partial bill, over-payment rejected. DRF API `/api/purchasing/` behind RBAC (Branch Manager); 8
tests. React screens (Purchase orders, New PO, PO detail w/ confirm/receive/bill/payment, Suppliers);
"Purchasing" now an active sidebar module.

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

Design charter adopted (2026-06-16): the `Docs/Conductor_ERP_Product_Design_Engineering_Directive.md`
"Telegram of ERP" vision is now an **operational, enforceable design charter** (concrete per-screen
rules + the gate03-enforced engineering rules). The "Telegram feel" is delivered via **motion + focus +
restraint, not a colour reskin** — new **motion tokens** (`--ease-out`, `--dur-fast|--dur|--dur-slow`),
one app-wide `:focus-visible` ring (`--focus-ring`), `prefers-reduced-motion`, on-brand `::selection`,
standardized transitions, and a calm KPI-card hover; near-black Conductor brand kept. gate03 GREEN.
Backlog (per-screen, tracked in the directive's implementation log): designed empty states, loading
skeletons, responsive/narrow-width pass, density reduction. See DECISIONS.md.

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
| Redis (winget `Redis.Redis`) | ✅ installed, `Redis` service running, `ping`→PONG (Memurai abandoned — see DECISIONS.md) |

## ACTIVE BLOCKER → none
No active blocker. Redis runs as the auto-start **`Redis`** service (winget `Redis.Redis` port — the
earlier Memurai MSI failures were abandoned; see DECISIONS.md), and `gate:00` is green. The only
common post-reboot hiccup is the Redis service not having started yet — verify and start if needed:
```
Get-Service Redis
& 'C:\Program Files\Redis\redis-cli.exe' ping   # expect PONG
# if stopped: Start-Service Redis
```

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
