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

## Open decisions (industry-standard default applied; confirm with client)

- **Inventory costing method** — questionnaire says "Not decided." Default **Weighted Average**,
  applied consistently to all valuations.
- **Backup policy** — left blank. Default: automated nightly backups with periodic tested restores.
- **Frontend serving** — React built separately; default to serving the static build behind Django for
  single-tenant simplicity.
