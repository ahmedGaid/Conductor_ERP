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

## Open decisions (industry-standard default applied; confirm with client)

- **Inventory costing method** — questionnaire says "Not decided." Default **Weighted Average**,
  applied consistently to all valuations.
- **Backup policy** — left blank. Default: automated nightly backups with periodic tested restores.
- **Frontend serving** — React built separately; default to serving the static build behind Django for
  single-tenant simplicity.
