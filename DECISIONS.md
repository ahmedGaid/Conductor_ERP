# DECISIONS

Running log of choices made where specs were silent or in conflict, plus any deviation from a
stated requirement. Every entry is traceable so future maintainers (and Claude Code) understand
*why* the code looks the way it does.

## Reconciliation of conflicting specs (2026-06-14)

The `files/` folder contained three conflicting specs (full NestJS ERP, Django engineering
charter, Node/Express workflow-MVP). Confirmed direction with the client:

- **Scope:** phased, foundation-first — platform + workflow/forms engine + bilingual RTL UI first,
  then ERP modules in questionnaire priority order (Accounting → Inventory → Sales → Purchasing → CRM).
- **Backend stack:** Python 3.13 / Django + DRF (the "System Architecture & Engineering
  Requirements" doc wins). **NestJS and Node/Express are dropped.** The `PHASE_00–09` docs remain as
  *design input* (workflow-engine contract, RTL UI spec, Purchase-Request reference flow), re-expressed
  on Django.
- **Deployment:** customer-hosted, single-tenant, Windows Server, multi-machine capable, no cloud-only deps.
- **Engineering standards:** all adopted (correlation IDs + structured logging, immutable audit,
  fault isolation + domain events, privacy-safe diagnostics + monitoring).
- The MVP-only "forbidden list" (no real ERP modules; dev-user-only auth) is **superseded** — we build
  the real modules and real RBAC/2FA.

## Architecture choices

- **Django config package** is named `config/`; the **modules** live under `erp/` (e.g. `erp/core`,
  `erp/workflow`) to match the engineering charter's module tree without clashing with the project package.
- **`core` module uses a flat layout** (infrastructure), while business modules will follow the strict
  `module/{api,domain,services,repositories,contracts,events,tests,docs}/` sub-layout.
- **`identity` app label** is used instead of `auth` because `auth` clashes with `django.contrib.auth`'s
  app label.
- **Custom `User` model created in Stage 0** so `AUTH_USER_MODEL` is locked before the first migration
  (swapping it later requires a destructive reset). Stage 1 expands it (JWT, RBAC, TOTP 2FA, branch scoping).

## Toolchain (local dev provisioning, 2026-06-14)

- Machine had only git. Installed via winget: Python 3.13, Node LTS, PostgreSQL 16.
- **Redis:** Memurai Developer was the first choice but its MSI repeatedly failed — first a UAC/elevation
  hang that, when killed, left Windows Installer in a stuck 1618 state (required a reboot), then after
  reboot a `1603` failure (`SFXCA: Failed to create temp directory. Error code 5` in its .NET custom
  actions — an elevated-TEMP/ACL issue specific to that installer). Switched to **`Redis.Redis`** (the
  Microsoft Redis-on-Windows port, plain MSI, no managed custom actions) via winget — installed cleanly,
  runs as the auto-start `Redis` service on port 6379, `redis-cli ping` → PONG. Still a native winget
  install, no cloud dep. Note: this port is Redis 3.0.x (older) but sufficient as a Celery broker/result
  backend for dev; revisit for production if newer Redis features are needed.

## Workflow engine (Stage 2)

- **Condition edge semantics.** The PHASE specs both say "exactly one winner" *and* ship a `true`
  fallback edge — contradictory under a strict reading. Resolved deterministically: edges with an
  explicit JSON-logic condition are **guards**; a single null/`true` edge is the **else-fallback**.
  Exactly one guard must be truthy → it wins; ≥2 truthy guards → fail (ambiguous); 0 truthy guards →
  take the lone fallback, else fail. Deterministic and supports an else branch. See `engine/edges.py`.
- **JSON-logic is self-implemented** (`workflow/lib/jsonlogic.py`) — no external dependency, no
  eval/exec; auditable and deterministic. Covers var/compare/and/or/if/arithmetic/in.
- **External-write idempotency** uses both layers: a durable `IdempotencyRecord` ledger keyed by
  `sha256(instance|node|attempt)` (engine short-circuits a same-attempt re-run) **and** DB-level
  proof (UNIQUE `idempotency_key` + `ON CONFLICT DO NOTHING` in the target). Proven by tests.
- **`erp_external` schema** (the simulated external ERP target) lives in the same Postgres instance
  via a `RunSQL` migration — no second server, matching the PHASE intent.

## Frontend foundation (Stage 3)

- **Build tooling = Vite + React 18 + TypeScript** (not Next.js): the app is a customer-hosted,
  single-tenant SPA served as a static bundle behind Django — no SSR requirement, so Vite keeps the
  build simple and dependency-light. Lives in `apps/web/`.
- **Arabic/RTL is the product default, not an afterthought.** `index.html` ships `lang="ar"
  dir="rtl"`; i18next `fallbackLng` is `ar`. The active language is reflected onto `<html dir/lang>`
  on every `languageChanged`, so a live AR↔EN switch flips direction with no reload.
- **Logical CSS only** (`inline-start/end`, `margin-inline-*`, `border-inline-end`, `inset-inline-*`)
  — never physical `left/right`. This is what makes one stylesheet mirror correctly in both
  directions. gate03 statically bans physical left/right properties.
- **Design tokens are the single source of truth for colour.** `src/styles/tokens.css` is the only
  file allowed to contain raw hex; everything else uses `var(--token)`. gate03 bans stray hex
  elsewhere. Enables future theming without hunting hardcoded values.
- **i18n key-parity is build-blocking, both directions.** `scripts/check-i18n-parity.mjs` runs as
  npm `prebuild`; a build cannot ship with a key present in one locale but missing in another.
  gate03 additionally proves the check *catches* drift by running it against a mutated fixture.
- **Fonts are self-hosted** via `@fontsource` (IBM Plex Sans Arabic + Inter) — no Google Fonts CDN,
  honouring the "no cloud-only deps" customer-hosting constraint. `<bdi>` isolates LTR tokens
  (codes/numbers/English) inside RTL text.

## Platform screens + workflow API (Stage 4)

- **Edges are exchanged by node `key`, not DB id.** The graph API (`GET/POST/PUT
  /api/workflow/workflows`) serializes edges as `{source: key, target: key, condition, ordering}`.
  This makes a definition round-trip cleanly (save → reload → identical structure) and keeps saved
  payloads stable across re-saves — proven by `test_save_graph_round_trips`.
- **`save_graph` upserts nodes by key; edges are replaced wholesale.** Nodes that persist across an
  edit keep their DB id, so a *running* instance pointing at a node survives a workflow edit. Edges
  aren't referenced by instances, so they're deleted+recreated. Every save bumps `Workflow.version`.
- **Validation lives in the service, before any write:** exactly one start node, unique node keys,
  edges reference existing nodes, and edge `ordering` is unique per source (the engine's deterministic
  selection depends on it). Invalid graphs return 400 and write nothing.
- **Frontend is a JWT SPA.** A login screen obtains the access token (stored in `localStorage`), the
  fetch client attaches it as a Bearer and unwraps the `{data}` / `{error}` envelope; a 401 clears
  the token. Routing is **HashRouter** so the static bundle works behind Django with no server-side
  route config.
- **Canvas = React Flow (`@xyflow/react`).** Chosen over a hand-rolled SVG editor: mature, handles
  pan/zoom/minimap/connection UX. The graph pane is wrapped `dir="ltr"` (a graph coordinate space
  isn't a reading direction) while the surrounding shell stays RTL — the rest of Stage 4's CSS is
  still logical-only and token-driven, enforced by gate03's scans over all of `apps/web/src`.
- **gate04 proves the contract at the API level** (round-trip, start→waiting→approve/reject,
  node-level logs in the viewer payload, real metrics) and statically asserts the screens are wired;
  it does **not** re-run the frontend build — gate03 already does a full `npm run build` that covers
  the new screens (typecheck + i18n parity + token/logical-CSS discipline).

## Accounting — General Ledger core (Stage 5a)

- **Money is integer minor units, never a float.** `domain/money.py` `Money(minor:int, currency)`
  (e.g. `1050` == `10.50 EGP`); binary floats can't represent decimals exactly and accounting must be
  exact. Ledger amount columns are `BigIntegerField`; `Money` forbids cross-currency arithmetic and
  rejects float construction. gate05 bans `FloatField`/`DecimalField` in the accounting models.
- **Default currency EGP** (Egypt deployment: ETA e-invoicing, Africa/Cairo), 2 minor digits.
- **Normal-balance rule is the single sign convention.** `domain/accounts.py`: assets/expenses are
  debit-normal, liabilities/equity/income credit-normal; `signed_balance()` drives every report so
  balances read positive in the account's natural direction.
- **`post_journal` is the one double-entry invariant point.** It enforces balanced (Σdebit==Σcredit,
  total>0), ≥2 lines, each line exactly one side >0 and non-negative, postable+active accounts, and
  an OPEN period — atomically. Invalid → raises an `ACC-NNN` AppError and writes nothing.
- **Posted entries are immutable; undo = reversal.** `reverse_journal` posts the mirror entry and
  links `reverses`; we never edit/delete a posted entry (audit integrity).
- **Period lock = posting gate.** Posting is allowed only to an OPEN `Period`; closing a period
  blocks further posting to it (`ACC-003`). Entry date must fall in a period (`ACC-006`) unless an
  explicit `period_code` is given.
- **Strict module layout, models re-exported.** The module follows
  `{domain,repositories,services,contracts,events,api,tests,docs}`. ORM models live in
  `domain/models.py`; `accounting/models.py` re-exports them so Django's app/migrations discovery
  works without breaking the layout. **Gotcha recorded:** a sibling `events/` *package* would shadow
  `events.py` — keep cross-module event-name constants in the `events.py` *module* only.
- **Other modules touch accounting only via `contracts/`** (`post_journal`, `Money`, event names) —
  never the ORM. Stage 5c modules will post to the GL through this surface / the `JournalPosted` bus.

## Product name + UI design (2026-06-14)

- **Product name = "Conductor."** Client offered "Prism" and "Conductor"; chose Conductor — it
  reflects the workflow/orchestration engine at the system's core (coordinating modules into one
  performance) and is more distinctive than the heavily-used "Prism". Applied to the wordmark/logo
  tile ("C"), browser title, and i18n `app.title` in both locales; the localized "ERP" phrase became
  `app.tagline`.
- **UI reference adopted from `files/preview.jpg`.** Modern dashboard language: icon sidebar with
  logo + grouped nav + user footer, command-bar topbar (search + quick actions), KPI stat cards with
  month-over-month % deltas, content panels, coloured status pills. Implemented with a refreshed
  token set (slate neutrals, **near-black brand** for primary actions/logo, subtle layered shadows,
  larger radii). Discipline unchanged: tokens-only hex, logical CSS only, i18n key-parity.

## Accounting — financial statements (Stage 5b-2)

- **Statements are pure functions of the posted GL** (`services/statements.py`); no separate
  reporting store. Income Statement = income−expense over a date range/period; Balance Sheet =
  assets vs liabilities+equity+current net income.
- **The balance sheet always balances** by construction: the trial balance balances (Σdebit==Σcredit)
  ⇒ Assets+Expenses = Liabilities+Equity+Income ⇒ Assets = Liabilities+Equity+(Income−Expense). The
  report computes and asserts `is_balanced`; current-period net income is folded into equity.
- **Cash accounts via an `Account.is_cash` flag** (migration 0002; seed marks Cash + Bank). Cash flow
  = movement of those accounts; `closing == opening + in − out` and is independently **reconciled** to
  the cash accounts' GL balance as of the end date.
- **AR/AP aging + VAT return are deferred, on purpose.** True aging needs per-customer/vendor
  open-item sub-ledgers (invoices with due dates) that only exist once Sales/Purchasing land; the GL
  alone has account balances, not open items. Building a fake aging from balances would be wrong, so
  it waits for those modules.

## Inventory module (Stage 5c)

- **Inventory posts to the GL only through `erp.accounting.contracts`** (`post_journal`) — never the
  accounting ORM/services. This is the modular-monolith boundary in action; gate06 statically forbids
  `erp.accounting.{domain,models,services}` imports in inventory.
- **Weighted-average costing, exact.** Quantity is `Decimal` (items can be fractional); value is
  integer **minor units**. The average is always value/quantity (never stored rounded). On issue, cost
  is taken **proportionally** from the remaining value (`round(value*issue_qty/qty)`), so the running
  value never drifts and issuing the whole quantity removes the whole value. (FIFO/standard cost can
  come later per item; weighted-average is the questionnaire default.)
- **GL mapping:** receipt → Dr Inventory (1200) / Cr Goods-Received-Not-Invoiced (2150, a liability
  cleared later by a Purchasing vendor bill); issue → Dr COGS (5000) / Cr Inventory; transfer posts
  **no** GL (value stays within the Inventory account). Seed adds account 2150.
- **Core invariant:** the Inventory GL account balance always equals total stock value — asserted by a
  test that posts receipts/issues then compares `general_ledger("1200")` to `Σ StockBalance.value`.
- **No negative stock** in this first slice: issuing/transferring more than on-hand is rejected
  (`INV-001`) and writes nothing (atomic). Adjustments + back-dated corrections come later.
- **Quantities use `DecimalField`** (exactness without float) — distinct from the money rule (money is
  integer minor units). gate06 bans `FloatField` for value but allows Decimal quantities.

## Sales module (Stage 5d)

- **Cross-module only via contracts.** Sales calls `inventory.contracts.issue(sku, warehouse, qty)`
  and `accounting.contracts.post_journal(...)` — never their ORM/services. gate07 forbids
  `erp.{accounting,inventory}.{domain,models,services}` imports in `sales/services/orders.py`.
- **References by business key, not FK.** Order lines store `item_sku` (string) and the order stores
  `warehouse_code` (string); no DB FK crosses a module boundary. Inventory exposes code-based
  `issue`/`receive`/`find_item` helpers (added to its contract) so callers stay decoupled.
- **Order-to-cash GL mapping:** deliver → (inventory) Dr COGS/Cr Inventory at weighted-average;
  invoice → Dr AR (1100)/Cr Sales Revenue (4000); payment → Dr Cash (1000)/Cr AR. Revenue is
  recognized at **invoice**, COGS at **delivery** (standard). VAT on invoices waits for the
  accounting tax slice.
- **Credit limit** enforced at confirm: customer outstanding (Σ invoiced − Σ paid) + this order ≤
  limit; `credit_limit_minor = 0` means unlimited. **No negative stock**: delivery beyond on-hand is
  rejected by the inventory contract and the order stays confirmed (atomic).
- **Each transition is atomic + guarded** by an explicit status check (`SAL-001`); over-payment is
  rejected (`SAL-005`). Proven: a full draft→paid flow leaves the trial balance balanced and AR at 0.

## Purchasing module (Stage 5e)

- **Mirror of Sales; closes the GRNI loop.** Receipts (from inventory) credit GRNI; the vendor
  **bill** debits GRNI and credits AP, so GRNI nets to zero and the payable is booked. Net of
  receive+bill is exactly Dr Inventory / Cr AP — the correct purchase entry.
- **3-way match before billing:** every line's `received_qty` must equal the ordered `quantity`
  (`PUR-002` otherwise); GRN supports **partial receipts**, which then (correctly) block the bill
  until matched. This is the architecture for partial/over receipts even though the happy path
  receives in full.
- **GL mapping:** receive → Dr Inventory (1200)/Cr GRNI (2150) [posted by the inventory contract];
  bill → Dr GRNI (2150)/Cr AP (2000); payment → Dr AP (2000)/Cr Cash (1000).
- **Cross-module only via contracts** (gate08 forbids `erp.{accounting,inventory}.{domain,models,
  services}` imports in `purchasing/services/orders.py`); items by SKU string, warehouse by code.
- Each transition atomic + guarded (`PUR-001`); over-payment rejected (`PUR-005`). Proven: full
  draft→paid flow leaves the trial balance balanced with GRNI at zero.

## Sales & Purchasing depth — returns + partial flows (Stage 5d-2 / 5e-2, 2026-06-15)

First "depth" increment on the two transactional modules. Chosen first because returns and partial
fulfilment exercise the GL + stock invariants the gates already prove (trial balance balances,
Inventory GL == stock value) — the project's core correctness story.

- **Returns are two balanced journals, split by ownership — never one cross-module entry.** The
  inventory leg is posted by the **inventory contract**; the financial leg by Sales/Purchasing. This
  keeps each module posting only the accounts it owns and preserves the "inventory owns the inventory
  GL leg" rule that makes `Inventory GL == stock value` inventory's responsibility.
  - **Customer return (sales credit note):** `inventory.return_in` posts Dr Inventory / Cr COGS (the
    exact reverse of an issue); Sales posts Dr **Sales Returns (4090)** / Cr AR. 4090 is a new
    credit-normal *contra-revenue* income account (added to seed + COA) — its signed balance reads
    **negative** against revenue, which is correct, so the GL test asserts `-value`.
  - **Supplier return (purchasing debit note):** `inventory.return_out` posts Dr GRNI / Cr Inventory
    (the reverse of a receipt); Purchasing posts Dr AP / Cr GRNI. GRNI nets to zero and the net of
    receipt+bill+return is nil — symmetric to the forward procure-to-pay flow.
- **Returns are valued at the current weighted-average cost**, computed *inside* inventory
  (`return_in` derives unit cost from the live `StockBalance`; if the warehouse holds none of the
  item the average is unknown and the return is valued at 0). Sales/Purchasing pass only SKU +
  quantity — they never see or supply cost, keeping the module boundary intact. Whatever cost is
  used, stock value and the Inventory GL move by the same amount, so the invariant always holds.
- **Return basis is the *delivered/received* quantity, not ordered.** A line can be returned only up
  to `delivered_qty − returned_qty` (sales) / `received_qty − returned_qty` (purchasing); excess is
  rejected (`SAL-007` / `PUR-007`). An empty return is rejected (`SAL-006` / `PUR-006`). Sales returns
  require INVOICED|PAID (AR exists to credit); purchase returns require BILLED|PAID (AP exists).
  Returning every delivered/received unit flips the order to a terminal `returned` status.
- **Partial fulfilment accumulates across calls.** `deliver_order(delivered=…)` and
  `receive_order(received=…)` take an optional `{line_no: qty}` map (omitted ⇒ act in full), add to
  each line's `delivered_qty`/`received_qty`, and set `partially_delivered`/`partially_received`
  until every line is complete (then `delivered`/`received`). Over-fulfilment beyond the outstanding
  ordered qty is rejected (`SAL-008` / `PUR-008`). Billing still requires the **full** receipt — a
  partially-received PO reaches `bill_order` but the existing 3-way match rejects it (so the match,
  not a status guard, remains the meaningful block; `bill_order` now also accepts
  `partially_received` for exactly this reason). Invoicing still requires full delivery.
- **Status columns widened to `max_length=24`** to fit `partially_delivered` (19) /
  `partially_received` (18). No separate Return/Shipment entities in this slice — quantities live on
  the order line and the credit/debit-note number is the posted journal's entry number (mirroring how
  `invoice_number`/`bill_number` already work); a dedicated return document can come later if needed.

## Sales & Purchasing depth — quotation / purchase-request front-ends (Stage 5d-3 / 5e-3, 2026-06-15)

Second depth increment: the pre-order documents the spec calls for (Quotation → approval → SO;
Purchase Request → approval → PO), with an amount-threshold approval gate.

- **Conversion reuses the existing order service — no order logic is duplicated.** `convert_quotation`
  calls `sales.create_order(...)` and `convert_request` calls `purchasing.create_order(...)`, building
  the order lines from the document's lines. The document only records the resulting order *number*;
  the proven order-to-cash / procure-to-pay lifecycle is untouched. This keeps the new feature a thin
  front-end over a trusted core.
- **Approval is an amount-threshold matrix, not a fixed step.** `APPROVAL_THRESHOLD_MINOR = 1,000,000`
  (10,000.00 EGP) per module. On **submit**: at/below the threshold the document **auto-approves**
  (status → approved, `approved_at` stamped, no approver); above it, it goes **submitted** and waits
  for an explicit `approve` (which records `approved_by`). This models a real "small purchases need no
  sign-off, large ones do" policy with one knob, rather than a hard-coded role hierarchy. The approve
  action is still gated by the existing **Branch Manager** RBAC role (the only elevated role today); a
  multi-tier matrix can layer on later by adding roles + per-tier thresholds.
- **Conversion is idempotent / one-shot.** A document carrying a `converted_order_number` cannot be
  converted again (`SAL-012` / `PUR-012`), so one quotation yields exactly one order; converting before
  approval is rejected (`SAL-010` / `PUR-010`), as is converting a rejected document. Reject is allowed
  from submitted *or* approved (a manager can pull a quote back before it's converted).
- **New entities, no money posting.** `Quotation`/`QuotationLine` and `PurchaseRequest`/
  `PurchaseRequestLine` are plain documents — they touch **no GL** (nothing is posted until the
  converted order runs its normal lifecycle), so they needed no accounting wiring. Money stays integer
  minor units; quantities Decimal. Status `max_length=16` fits all values here.
- **DRF + React mirror the existing order screens.** Endpoints `/api/{sales/quotations,
  purchasing/requests}` with `submit`/`approve`/`reject`/`convert` actions (convert returns the new
  order's id+number, status 201); list/new/detail React pages reuse the order form/table patterns,
  added as new tabs on the Sales/Purchasing sub-nav. gate07/08 assert the services reuse the order
  service and the screens are wired; ar/en i18n parity kept (gate03 build).

## Sales & Purchasing depth — discounts + approval matrix (Stage 5d-4 / 5e-4, 2026-06-15)

Third (and final, for now) depth increment, completing the Sales/Purchasing depth menu.

- **Line-level discounts on sales, net method.** Each `SalesOrderLine` carries a `discount_minor`
  taken off its gross (`round(qty*price)`); `line_total_minor = gross − discount` and the order
  `subtotal_minor` is the sum of net line totals. The invoice posts the **net** subtotal to Revenue
  (Dr AR / Cr Sales Revenue at net) — a valid net-method treatment, so no separate "Sales Discounts"
  contra account is needed and the trial balance still balances. A discount cannot be negative or
  exceed the line gross (`SAL-013`).
- **Returns now credit the net unit value, prorated.** `return_order` switched from `qty*unit_price`
  (gross) to `round(line_total_minor * returned_qty / quantity)` — so a discounted line refunds the
  discounted price. With no discount this is identical to the old result (existing return tests
  unchanged), so it's a strict generalization.
- **Header (order-level) discount deferred — on purpose.** A whole-order discount would have to be
  allocated back to lines to keep returns/partial-invoice math exact; line-level covers the common
  case cleanly. Recorded so the limitation is traceable. Purchasing **cost** discounts are likewise
  deferred: a PO discount changes the received inventory valuation and the GRNI↔bill match, which
  needs its own design — out of scope for this slice (approval still applies to POs).
- **Amount-threshold approval matrix at confirm, both modules.** `confirm_order` rejects with
  `SAL-009`/`PUR-009` when the order's net value is over `APPROVAL_THRESHOLD_MINOR = 1,000,000`
  (10,000.00 EGP) and it hasn't been approved; `approve_order` (Branch-Manager RBAC) stamps
  `approved`/`approved_by`/`approved_at` and unblocks confirm. At/below the threshold confirm
  proceeds with no approval. The gate is strictly `>` the threshold (an order exactly at 10,000.00
  needs no sign-off). This is the same threshold + one-knob philosophy as the quotation/PR approval,
  but applied to **direct** orders at the confirm step (quotation approval gates conversion; this
  gates confirmation) — the two compose without overlap.
- **No GL impact from approval; discounts only change the net already posted at invoice.** Approval
  is a workflow flag; discounts reduce the revenue/AR that invoice posts. Both keep the ledger
  invariants intact (proven: invoice posts net, TB balances, discounted return prorates).

## Accounting — VAT / tax (Stage 5b-4, 2026-06-15)

First accounting-depth slice beyond the GL core: VAT on sales, the highest-value compliance feature
for an Egypt deployment (precursor to ETA e-invoicing).

- **A `TaxCode` is a thin accounting master record**, referenced by other modules **only by its string
  `code` through the accounting contract** (`find_tax_code` / `compute_tax`) — never the ORM, same
  boundary rule as `post_journal`. gate07 asserts sales reaches VAT via the contract. Rate is stored
  in **basis points** (`rate_bps`, 1400 = 14%) so the rate itself is integer; tax is
  `round(net * rate_bps / 10000)` half-up, keeping the money path float-free. Seed adds **VAT14**
  (Egypt standard) and **VAT0** (exempt); output VAT posts to **2100 VAT Payable**.
- **VAT is opt-in per sales order** (`tax_code` blank ⇒ no VAT). This kept every pre-VAT sales test
  passing unchanged and means VAT is realised at **invoice**, not order entry: invoice posts
  **Dr AR (gross) / Cr Revenue (net) / Cr VAT Payable (vat)** (the VAT line is omitted when vat==0, so
  VAT0/untaxed orders stay a clean 2-line entry). `invoiced_minor` becomes the **gross** so payments
  settle net+VAT and `outstanding` is correct.
- **Returns reverse VAT proportionally.** A credit note now posts **Dr Sales Returns (net) /
  Dr VAT Payable (vat) / Cr AR (net+vat)** where `vat = compute_tax(returned_net)`. Combined with the
  earlier prorated-net return logic this keeps the trial balance balanced and the VAT account correct
  after partial returns.
- **VAT return = output − reversals over a date range**, read straight from the posted ledger
  (`vat_return` sums credits vs debits on the tax codes' output accounts). **Input (purchase) VAT
  recovery is deliberately deferred** — it changes the GRNI↔bill posting and the 3-way match, so it
  gets its own slice; today the report's `net_payable` is output VAT net of sales-return reversals,
  which is exactly right for the sales side. **ETA e-invoice records (UUID/submit/poll) are the
  planned next slice** and build on these VAT totals.

## E-Invoicing (ETA) — compliance records (Stage 6a, 2026-06-16)

The continuation of the VAT slice: every posted sales invoice becomes an **ETA e-invoice** record
with a submit/poll lifecycle. First module of Stage 6 (integrations).

- **A new bounded-context module `erp/einvoice`**, full strict layout. E-invoicing is a distinct
  compliance/integration concern (not part of accounting's ledger), so it gets its own app + gate
  (**gate10**, `ALL_GATES` extended to 00–10).
- **Driven by the event bus, not a call from Sales.** `einvoice` subscribes (in `AppConfig.ready()`)
  to the **`sales.OrderInvoiced`** event — which `invoice_order` now publishes **enriched** with the
  invoice's business data (number, customer code/name, date, tax code, net/tax/total) — and records a
  draft `ETAInvoice`. **Sales has zero knowledge of e-invoicing**; the only coupling is the public
  event name + payload, and the bus isolates subscriber failures so a recording error can never break
  invoicing. gate10 forbids `einvoice` importing `erp.sales.{domain,models,services}`. (Chosen over a
  direct `sales → einvoice` contract call precisely to keep invoicing independent of compliance.)
- **References by business key.** `ETAInvoice` stores `invoice_number`/`customer_code`/totals — no FK
  crosses the boundary; `record_invoice` is idempotent on `invoice_number` (one record per invoice).
- **Stubbed ETA adapter** (`services/eta_adapter.py`) — the real ETA API needs signing + credentials
  + network, disallowed in an offline/customer-hosted build. The stub is **deterministic**: `submit`
  returns a UUID = the document's sha256 (so retries are idempotent and tests reproducible) and
  `query` validates it. Lifecycle `draft → submitted (UUID assigned) → valid` (or `rejected`); each
  transition atomic. Swapping in a real HTTP client only touches that one file. Money stays integer
  minor units.
- **Recorded going forward only.** Invoices issued *before* this module existed have no ETA record
  (the subscriber wasn't registered); a backfill command can be added later if needed.

## Input (purchase) VAT — recoverable, netted on the VAT return (Stage 5b-5, 2026-06-16)

Closes the VAT loop deferred above: purchases now book **recoverable input VAT** that nets against
output VAT, so the VAT return shows the true position owed to (or refundable from) the authority.

- **`TaxCode` gains `input_account_code`** (default **1190 VAT Input — Recoverable**, an asset);
  seed adds the account and sets it on VAT14/VAT0. The accounting contract's `find_tax_code` now
  exposes it, so other modules never touch the ORM.
- **Opt-in per purchase order** (`tax_code`, blank ⇒ unchanged) — mirrors the sales decision, so every
  pre-VAT purchasing test stays green. The PO carries `tax_minor`; the **bill** posts **Dr GRNI (net)/
  Dr VAT Input (vat)/Cr AP (gross)** (2-line when untaxed), `billed_minor` becomes gross so payments
  settle net+VAT, and the **debit note reverses input VAT proportionally** (Dr AP/Cr GRNI/Cr VAT Input)
  — GRNI, AP and VAT Input all net to zero on a full return.
- **`vat_return` now nets output minus input.** Output VAT = credits−debits on the codes' *output*
  accounts; input VAT = debits−credits on the *input* accounts; `net_payable = net output − net input`
  (negative ⇒ a refund position, `is_payable` false). Backward compatible: sales-only ranges report
  `input_vat = 0` and the same `net_payable` as before.
- **Why book input VAT at *bill*, not receipt.** The receipt (GRN) is a goods/GRNI event with no tax
  document; VAT recoverability attaches to the supplier *bill*. This keeps the 3-way match and the
  Inventory-GL-equals-stock-value invariant untouched — only the GRNI→AP clearing leg changes.
- Proven: gate05 (vat_return nets input) + gate08 (bill books input VAT via the contract) extended;
  4 new purchasing tests + 1 accounting test. Demo seeds a billed VAT14 purchase (input VAT 280.00),
  so the VAT-return screen shows output netted against input.

## Report exports — CSV / Excel server-side, PDF via browser print (Stage 6b, 2026-06-16)

First slice of Stage 6 reporting: every existing report (trial balance, general ledger, the three
financial statements, VAT return, e-invoices) is downloadable.

- **A shared, presentation-agnostic renderer** `erp/core/exports.py` (`ReportTable` + `to_csv` /
  `to_xlsx` + `export_response`). It lives in core because exports span modules; it operates on plain
  `ReportTable` dicts passed in — no cross-module domain coupling. Money cells carry integer **minor
  units** and the renderer converts to major (÷100, 2dp) so Excel gets real summable numbers.
- **Arabic is preserved end to end.** CSV is UTF-8 **with a BOM** (so Excel detects the encoding on
  double-click); XLSX sets a **right-to-left sheet** when the request is `lang=ar`. Export column
  headers/titles are **bilingual in the API layer** (`erp/accounting/api/exports.py`) chosen by
  `?lang=`, so a download is self-describing without reaching into the frontend i18n bundle.
- **PDF is the browser's native print-to-PDF**, not a server library. `fpdf2`/`reportlab` can't shape
  Arabic without bundling an Arabic TTF + a reshaper/bidi stack — fragile for an RTL-first product —
  whereas the browser already shapes the whole UI perfectly. A `styles/print.css` strips the chrome
  (sidebar/topbar/navs/toolbars/`.no-print`) and a "Print / PDF" button calls `window.print()`. Zero
  fonts, zero deps, correct RTL. (So only **openpyxl** was added to requirements — pure-python,
  offline-safe; no system libraries.)
- **Download param is `?export=csv|xlsx`, NOT `?format=`** — DRF reserves `format` for content
  negotiation, so `format=csv` 404s before the view runs. An unknown `export=` value falls through to
  the normal JSON response. Downloads are authenticated (a blob fetch carrying the JWT, `downloadExport`
  in the api client), so no token ever lands in a URL.
- Proven: gate05 extended (renderer + `?export=` endpoints + React toolbar wired); gate01 runs the core
  renderer tests; 8 new tests (CSV BOM + minor→major, XLSX round-trips real numbers + RTL, auth, JSON
  fallback on unknown format).

## Design charter — "Telegram of ERP" (the standing UI/UX contract)

- The `Docs/Conductor_ERP_Product_Design_Engineering_Directive.md` vision (clarity, speed, simplicity,
  readability, confidence; modern/lightweight/focused; never overwhelming) was **operationalized into a
  concrete, enforceable charter** in that same file — turning a one-paragraph vision into per-screen
  rules + the non-negotiable engineering rules gate03 already checks (tokens-only colour, logical-CSS,
  i18n parity, clean build).
- **The "Telegram feel" is delivered through motion, focus, and restraint — NOT a colour reskin.** The
  near-black **Conductor** brand identity is deliberately kept (an earlier recorded decision); chasing
  literal "Telegram blue" was rejected as off-brand. Instead a **motion token scale**
  (`--ease-out`, `--dur-fast|--dur|--dur-slow`) + a single app-wide `:focus-visible` ring
  (`--focus-ring`) + `prefers-reduced-motion` + on-brand `::selection` make the existing clean UI feel
  fast, tactile, and confident, and these cascade to every screen via `tokens.css`/`global.css`.
- Standardized button/input/link/nav transitions onto the motion scale and gave the dashboard KPI cards
  a calm hover lift. Proven: gate03 green (build + token/logical-CSS scans + i18n parity).
- **Backlog tracked in the directive's implementation log** (designed empty states, layout-matched
  loading skeletons, a responsive/narrow-width pass, density reduction via progressive disclosure) —
  applied per screen as we touch them, so the charter is met incrementally rather than in one big reskin.

## Accounting — Fixed Assets + Depreciation (Phase 1 of the completion plan, 2026-06-16)

First increment of the completion plan (`COMPLETION_PLAN.md`): the fixed-asset sub-ledger, finishing
the priority-1 accounting module's depreciation story.

- **Every money movement posts through `post_journal`.** Acquisition, each monthly depreciation
  charge, and disposal are ordinary balanced journals — so the asset register, the GL, and the trial
  balance can never diverge (proven: every asset test asserts `trial_balance().is_balanced`). The asset
  record just *records* the journal numbers; it is not a parallel money store.
- **Straight-line, exact, with a salvage floor.** Monthly charge = `round((cost − salvage) / life)`,
  but each run books `min(standard, remaining_depreciable)` so the **final period trues up** — total
  depreciation equals `cost − salvage` to the minor unit and **net book value never drops below
  salvage**. (Declining-balance / units-of-production can be added per-asset later; straight-line is
  the questionnaire default, matching the weighted-average inventory choice.)
- **Depreciation run is idempotent per (asset, period).** `DepreciationEntry` has a UNIQUE
  `(asset, period_code)`; `run_depreciation(period)` skips any asset already charged in that period, so
  re-running a month posts nothing. Disposed / fully-depreciated assets are skipped.
- **GL mapping:** acquire → Dr Fixed Assets (1500) / Cr funding account (Cash 1000 default, or AP for a
  credit purchase); depreciate → Dr Depreciation Expense (5300) / Cr Accumulated Depreciation (1590, a
  contra-asset whose signed balance reads negative against assets — same pattern as 4090 Sales
  Returns); dispose → Cr Fixed Assets (cost), Dr Accumulated Depreciation (booked), Dr proceeds
  account, with the balancing line a **gain (Cr 4200)** or **loss (Dr 5400)** versus net book value.
  Seed adds accounts 1500/1590/4200/5300/5400.
- **Disposal is one-shot.** Only an `active` asset can be disposed (`ACC-008` otherwise); invalid
  acquisitions (non-positive cost/life, salvage ≥ cost) are rejected at entry (`ACC-007`). Money stays
  integer minor units (gate05 still bans Float/Decimal columns in the ledger models).
- **No separate gate:** the feature extends **gate05** (asset service posts via `post_journal`, the
  `/assets` + `/depreciation-run` + `/reports/asset-register` endpoints are mounted, the React screens
  are wired). 9 new accounting tests. React: a Fixed Assets register (new-asset + run-depreciation
  inline) + an asset detail/dispose screen, added as an Accounting sub-nav tab; ar/en parity kept.

## Accounting — Cost Centers (Phase 2 of the completion plan, 2026-06-16)

Second completion-plan increment: a reporting **dimension** so the P&L can be sliced by
department/project without a new ledger.

- **Purely additive.** A nullable/blank `cost_center_code` string on `JournalLine` (plus a `CostCenter`
  master, referenced by `code` like accounts/tax codes). Existing posts and every prior test are
  untouched — the dimension only adds optional tagging, it changes no posting maths and the trial
  balance is unaffected.
- **Validated at the one posting point.** `post_journal` rejects an unknown/inactive cost center
  (`ACC-009`) and writes nothing; a blank code is allowed (untagged). `reverse_journal` carries the
  line's cost center onto the mirror entry so a reversal stays in the same dimension.
- **P&L-by-cost-center == the income statement filtered by the dimension.** `income_statement` gained a
  `cost_center` filter rather than a separate report — simpler, and proven correct by the invariant
  that the per-center slices (plus the untagged remainder) sum to the un-dimensioned total. Balance
  sheet/cash-flow intentionally not filtered (a dimension on P&L is the 80% need; balance-sheet
  dimensions would need careful carry-forward semantics — deferred).
- **Sales/Purchasing do not yet stamp a cost center** on the journals they post — out of scope for this
  slice (it would touch each module's posting). Manual journal entries can tag lines today; wiring the
  transactional modules to a default cost center can layer on later. Extends **gate05**; 4 new tests.
  React: a Cost Centers master tab, a per-line cost-center picker on the journal-entry form, and a
  cost-center filter (with matching export) on the Income Statement; ar/en parity. Seeds CC-SALES/
  CC-OPS/CC-ADMIN.

## Accounting — Bank Reconciliation (Phase 3 of the completion plan, 2026-06-16)

Third completion-plan increment: tie a bank statement to its cash/bank GL account.

- **Matching is statement-line ↔ GL-line by signed amount.** A statement line's `amount_minor` is
  signed (+ deposit / − withdrawal); a cash GL line's signed amount is `debit − credit`. `auto_match`
  pairs each unmatched statement line to an unmatched posted cash GL line of equal signed amount;
  `match_line`/`unmatch_line` give manual override. A GL line can be claimed by at most one statement
  line (across all statements) — `_matched_gl_line_ids()` enforces it, `ACC-011` on a bad match.
- **Bank-only items are booked, never hand-waved.** Fees/interest that appear on the statement but not
  the books are entered via `post_adjustment`, which posts a balanced journal through `post_journal`
  (+amount ⇒ Dr Cash / Cr contra; −amount ⇒ Dr contra / Cr Cash) and then auto-matches the created cash
  line to its statement line. So every reconciling item ends up in the GL — the books and bank agree by
  construction, and the trial balance stays balanced (proven).
- **Reconciled = strict tie-out, outstanding items shown not hidden.** `reconciliation()` returns book
  balance vs statement closing, the difference, and both lists of unmatched items (in-transit deposits /
  outstanding checks on the book side; un-booked items on the bank side). `is_reconciled` is true only
  when **every** statement line is matched, **every** in-range cash GL line is matched, and
  closing == book balance. `mark_reconciled` refuses otherwise (`ACC-012`) and locks the statement
  (status → reconciled). Timing differences therefore keep a statement *open* (correct) rather than
  faking a tie-out.
- **Cash account required.** A statement's account must be `Account.is_cash` (`ACC-010`). Statement
  import in this slice is manual line entry (the form supports signed amounts); a CSV/OFX importer can
  layer on later behind the same `create_statement` service. Money stays integer minor units. Extends
  **gate05**; 6 new tests. React: a statement list + new-statement form and a detail/match screen
  (auto-match, per-line manual match, adjustment, reconcile); ar/en parity. New account 6100 Bank
  Charges; demo seeds a ready-to-reconcile statement.

## Accounting — Budgets + Budget-vs-Actual (Phase 4 of the completion plan, 2026-06-16)

Fourth completion-plan increment, completing Track A (accounting depth).

- **A budget is planned amounts per account+period; actuals come straight from the posted GL.** `Budget`
  (one per fiscal year) + `BudgetLine` (account_code, period_code, amount_minor; unique per
  account+period, upsert via `set_budget_line`, a **zero amount deletes** the line). No separate
  "actuals" store — `budget_vs_actual` reads posted journal lines for the budgeted accounts over the
  scope and signs them with the same `signed_balance` convention as the statements, so a P&L budget
  reads in its natural direction.
- **Variance = actual − budget, and the totals tie out by construction** (`total_variance ==
  total_actual − total_budget`) — the gate-proven invariant. Scope is a single period (its date range)
  or, with no period, the whole fiscal year (summing all the budget's lines and the FY date range).
- **Report shows only budgeted accounts.** An account you budgeted with no actuals shows actual 0
  (full unfavourable variance); unbudgeted spend is **not** surfaced in this slice — that would need a
  separate "actuals not in budget" pass, deferred. Keeps the report deterministic and tied to the plan.
- **Budget targets are validated** (`ACC-013` on an unknown fiscal year or account). Money stays integer
  minor units. Extends **gate05**; 5 new tests. React: a Budgets list/create + a detail screen with a
  line-entry form and the variance table (period filter, colour-coded variance, CSV/XLSX export); ar/en
  parity. Demo seeds a current-year operating plan.

## Inventory — Stock counts/adjustments + batch/lot (Phase 5 of the completion plan, 2026-06-17)

Fifth completion-plan increment, opening Track B (operational depth).

- **A count reconciles to the counted quantity through the same invariant point.** `StockCount` snapshots
  system quantities (`StockCountLine.system_quantity`); posting calls `adjust_stock` per counted line,
  which posts the value variance to the GL **via `erp.accounting.contracts`** (never the accounting
  ORM — gate06's boundary still holds). Shortage: value removed at weighted average → Dr Inventory
  Adjustment (5900) / Cr Inventory (1200); overage: valued at the current weighted-average unit cost
  (or a supplied cost when the warehouse holds none) → Dr Inventory / Cr Adjustment. Because stock value
  and the Inventory GL move by the same amount, **Inventory GL == stock value survives every
  adjustment** (proven by a count test).
- **Adjustment is a new signed movement.** `MovementType.ADJUSTMENT`; the movement stores the signed
  variance quantity and signed value (− shortage / + overage). `adjust_stock` returns `None` when there
  is no variance (posts nothing). Negative counted quantity rejected (`INV-008`); a count can be posted
  once (`INV-007`).
- **Batch/lot is traceability, not batch-level costing.** Optional `batch_no` + `expiry_date` on
  receipts; the **batches** report sums received quantity per (item, warehouse, batch) with the earliest
  expiry. Issues remain weighted-average and are **not** batch-allocated — so this is an honest
  receiving/expiry view, not a consumed-by-lot ledger (full lot tracking with FIFO-by-expiry issue is a
  later, larger change). The contract `receive()` now forwards batch/expiry, so Purchasing can pass them
  later.
- New account **5900 Inventory Adjustment** (expense). Extends **gate06**; 7 new tests. React: Stock
  counts list/new/detail (inline count entry + post) + a Batches view, and batch/expiry fields on the
  receive form; ar/en parity. Demo seeds a batched receipt + an open count.

## CRM — Campaigns + ticket escalation (Phase 6 of the completion plan, 2026-06-17)

Sixth completion-plan increment, completing Track B (operational depth).

- **Campaign ROI rolls up from linked records, by code.** Leads and opportunities carry an optional
  `campaign_code` (the same decoupled string-key pattern CRM uses for customers); `campaign_metrics`
  sums **won** opportunity amounts (won value) against the campaign `cost_minor` for ROI, plus
  open-pipeline and counts. No money is posted — a campaign is a marketing record, not a GL event.
  Proven: only linked opportunities count, lost ones are excluded from pipeline, ROI = won − cost.
- **Ticket escalation is idempotent — exactly once per breach.** `escalate_ticket` requires the ticket
  open + breached + not-yet-escalated (`escalated_at` null), then bumps priority one level
  (low→…→urgent, urgent is the ceiling), stamps `escalated_at`, logs a notify Activity, and publishes
  `crm.TicketEscalated` on the bus (a notification adapter can subscribe in Phase 8 — escalation does
  not send email itself). `run_escalations` sweeps every open/breached/un-escalated ticket; the
  `escalated_at` guard makes a repeated sweep a no-op. `AlreadyEscalatedError` (CRM-005) /
  `NotBreachedError` (CRM-006).
- **Why bump priority rather than reset the SLA.** The ticket has already breached; raising priority
  surfaces it for re-triage without faking a fresh due time. A multi-tier escalation matrix (reassign,
  notify a manager) can layer on the same event later. Extends **gate09**; 7 new tests. React: a
  Campaigns list (ROI column) + detail (metrics, activate/complete) and a Tickets escalate
  action/indicator + a run-escalations sweep; ar/en parity. Demo seeds a campaign (won 15k vs cost 12k)
  and a breached ticket.

## Open decisions (industry-standard default applied; confirm with client)

- **Inventory costing method** — questionnaire says "Not decided." Default **Weighted Average**,
  applied consistently to all valuations.
- **Backup policy** — left blank. Default: automated nightly backups with periodic tested restores.
- **Frontend serving** — React built separately; default to serving the static build behind Django for
  single-tenant simplicity.
