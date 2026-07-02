# Linear UX/UI Audit — Conductor ERP (2026-07)

> The spine of the full-app audit. One row per page, scored against the rubric.
> Core question per screen: **"If the Linear design team built this today, would they ship it this way?"**
> If no → redesign within the existing system (tokens + primitives), not a new brand.
> Pair with `conductor-brand` (on-brand? judgment) + `erp-frontend` (how to build).

**Branch:** `feat/linear-ux-audit-phase1` · **Started:** 2026-07-01 · **Mode:** polish-within-system, per-phase PRs.

---

## Rubric (per page)
Score each: ✅ pass · ⚠️ minor · ❌ redesign · — n/a

| Code | Dimension |
|------|-----------|
| HI | Visual hierarchy — most important info first, low noise |
| SP | Spacing from tokens — vertical rhythm, padding, section gaps |
| DN | Table/content density — dense but not cluttered |
| FO | Forms — label/field rhythm, grouping, progressive disclosure |
| AC | Contextual actions — placed near the data they affect |
| ST | Designed empty / error / loading states |
| KB | Keyboard — list nav (j/k/Enter), form keys (Esc/⌘↵), focus mgmt |
| FS | Focus states — one clear ring, predictable |
| MO | Motion — settled, fast, reduced-motion honoured |
| LX | Arabic lexicon — canonical word, human statuses, blame-free errors |
| LN | "Would Linear ship this?" — overall craft verdict |

---

## Systemic findings (fix once → fans out everywhere)

Banked by prior audits (PR #25 etc.) — treat as ✅ baseline:
- Monochrome chrome (light + dark, chroma 0) · owned single-stroke icon set · `<Badge tone>` primitive ·
  `ListSkeleton` on 55 pages · coherent `--space-*`/radius/font-size/table-density token scale ·
  RTL-safe BackLink · data-surfaces.css consolidation.

Open systemic gaps (Phase 1):
| ID | Gap | Evidence | Fix |
|----|-----|----------|-----|
| S1 | **No bulk actions** — zero row multi-select anywhere | no `type="checkbox"` in any list table | ✅ DONE primitive: `useRowSelection` + `<BulkActionBar>` + `<Checkbox>`; wired Sales Orders (approve/confirm). Fan-out to other lists pending. |
| S2 | **Inline edit nearly absent** | `InlineEdit` used on 1 page | ✅ Extended primitive with `display` prop (formatted read / raw edit); wired PriceListDetail line cells (price + min qty via `updateLine`, optimistic). Party/Item name inline-edit deferred — needs backend PATCH endpoints (out of polish scope). StockCount already inline (fast-tab input, left as-is). |
| S3 | **List keyboard-nav half-wired** | `useListKeyboardNav` on 11 of ~22 list pages | ✅ DONE: +7 pages (Customers, Suppliers, Items, Warehouses, PriceLists, Users, Roles). Leads/Tickets/EInvoices excluded — no detail-open by design. |
| S4 | **Form keys half-wired** | `useFormKeys` on 5 forms | ✅ DONE: ⌘↵-submit fanned to 12 create/entry forms (Customers, Suppliers, Items, Warehouses, PriceLists, PriceListDetail add-line, Leads, Campaigns, Tickets, CostCenters, Budgets, FixedAssets). No Esc on inline forms (would fight list-nav Esc). SetupWizard multi-step deferred to Phase 2. |
| S5 | **Stray spacing values** | 22 non-token px/rem (mostly legit sub-px) | ✅ DONE: audited — nearly all were component SIZES (icon/avatar/dialog widths, breakpoints), correctly not spacing tokens. Real finding: micro-gaps spelled two ways (`2px`/`0.125rem`). Added `--space-0-5` (2px, the step below `--space-1`); converted all ~13 gap/padding micro-values to it. Spacing system now fully token-driven. |

---

## Per-module page inventory

Status legend per page: `todo` = not yet audited · `pass` = audited, Linear-grade · `fix:<codes>` = needs work.

### Sales (high traffic — audit first in Phase 2)
| Page | Status | Notes |
|------|--------|-------|
| OrdersPage | ✅ | bulk-select + KB (P1.1) |
| OrderDetailPage | ✅ reviewed | mockup-redesigned PR#19; designed loading/error states, clean tokens — Linear-grade, no defect |
| QuotationsPage | ✅ | bulk-select (submit/approve) + KB; live-verified |
| QuotationDetailPage | ✅ reviewed | ListSkeleton + ErrorState present; clean — no defect |
| NewOrderPage | ✅ reviewed | smart defaults + WorkflowTracker + form keys + price-source; Linear-grade — no defect |
| NewQuotationPage | ✅ reviewed | mirrors NewOrder; form keys present — no defect |
| CustomersPage | ✅ | KB + form-keys (P1.3/1.4) |
| CustomerDetailPage | ✅ reviewed | PartyDetailView with loading/error/notFound states — no defect |
| InvoiceDocumentPage | ✅ reviewed | monochrome print doc, org masthead, no colour on totals — on-brand |

**Sales module verdict:** already Linear-grade + mechanically clean (no physical CSS, no raw hex, no
hardcoded strings, all states designed). The one real gap was bulk-select on the two list pages — now
closed (Orders P1.1, Quotations P2). No cosmetic churn forced (CLAUDE.md: enforce the system, don't reinvent).

**Purchasing module verdict (Phase 2):** identical finding — Linear-grade + clean. Bulk-select fanned to
both list pages: PurchaseOrders (approve/confirm) + PurchaseRequests (submit/approve), live-verified
end-to-end (request Submitted→Approved, "1 request approved"). Detail/form/supplier pages: designed
states, tokens-only, form keys present — no defect. No cosmetic churn.

### Purchasing — ✅ reviewed (Phase 2). Verdict: already Linear-grade + clean; gap was list bulk-select, now closed.
| Page | Status | Notes |
|------|--------|-------|
| PurchaseOrdersPage | ✅ | bulk-select (approve/confirm) + KB; live-verified |
| PurchaseOrderDetailPage | ✅ reviewed | designed states, clean — no defect |
| PurchaseRequestsPage | ✅ | bulk-select (submit/approve) + KB; live-verified |
| PurchaseRequestDetailPage | ✅ reviewed | designed states, clean — no defect |
| NewPurchaseOrderPage | ✅ reviewed | form keys present — no defect |
| NewPurchaseRequestPage | ✅ reviewed | form keys present — no defect |
| SuppliersPage | ✅ | KB + form-keys (P1.3/1.4) |
| SupplierDetailPage | ✅ reviewed | PartyDetailView states — no defect |

### Inventory — ✅ reviewed (Phase 2). No clean list bulk (reference lists + counts post is a detail-only, destructive action needing line review). Inline-style defects fixed app-wide.
| Page | Status | Notes |
|------|--------|-------|
| ItemsPage | ✅ | KB + form-keys (P1) |
| ItemDetailPage | ✅ reviewed | clean |
| WarehousesPage | ✅ | KB + form-keys (P1) |
| WarehouseDetailPage | ✅ reviewed | clean |
| StockOnHandPage | ✅ reviewed | dense report — clean |
| StockMovementPage | ✅ reviewed | clean |
| MovementsTable | ✅ reviewed | shared table — clean |
| StockCountsPage | ✅ reviewed | KB; bulk-post rejected (destructive, detail-only); inline hint → `.hint` |
| StockCountDetailPage | ✅ reviewed | inline hint → `.hint`; fast-tab count input kept |
| BatchesPage | ✅ reviewed | reference list — clean |

### Accounting — ✅ reviewed (Phase 2). No clean list bulk (journals are immutable posted GL entries; the rest are reports/reference/detail-driven). Inline-style defects fixed app-wide.
| Page | Status | Notes |
|------|--------|-------|
| ChartOfAccountsPage | ✅ reviewed | tree — clean |
| JournalListPage | ✅ reviewed | KB; journals immutable → no bulk |
| JournalDetailPage | ✅ reviewed | clean |
| JournalEntryPage | ✅ reviewed | inline `flex`/`marginBlock` → `.grow`/`.block-spaced` |
| GeneralLedgerPage | ✅ reviewed | report — clean |
| TrialBalancePage | ✅ reviewed | report — clean |
| BalanceSheetPage | ✅ reviewed | report — clean |
| IncomeStatementPage | ✅ reviewed | report — clean |
| CashFlowStatementPage | ✅ reviewed | report — clean |
| VatReturnPage | ✅ reviewed | clean |
| BudgetsPage | ✅ reviewed | KB + form-keys; inline `flex` → `.grow` |
| BudgetDetailPage | ✅ reviewed | inline hint → `.hint` |
| CostCentersPage | ✅ reviewed | form-keys; inline `flex` → `.grow` |
| FixedAssetsPage | ✅ reviewed | KB + form-keys — clean |
| FixedAssetDetailPage | ✅ reviewed | clean |
| BankReconciliationPage | ✅ reviewed | KB; inline hint/`marginBlock` → `.hint`/`.block-spaced` |
| BankStatementDetailPage | ✅ reviewed | inline `flex` → `.grow` |
| ReportBuilderPage | ✅ reviewed | inline hint → `.hint` |

### CRM — ✅ reviewed (Phase 2). Leads bulk-qualify added; Campaigns (channel, no lifecycle) + Pipeline (kanban) + Tickets (multi-state) no clean list bulk. Inline-style defects fixed.
| Page | Status | Notes |
|------|--------|-------|
| LeadsPage | ✅ | bulk qualify (new→qualified) + form-keys; live-verified render/gating |
| PipelinePage | ✅ reviewed | kanban — not a table |
| OpportunityDetailPage | ✅ reviewed | clean |
| CampaignsPage | ✅ | KB + form-keys; inline `flex` → `.grow`; no lifecycle → no bulk |
| CampaignDetailPage | ✅ reviewed | inline hint → `.hint` |
| TicketsPage | ✅ | form-keys; inline hint → `.hint`; multi-state per-row actions kept (no clean bulk) |

### Pricing
| Page | Status | Notes |
|------|--------|-------|
| PriceListsPage | todo | KB❌ |
| PriceListDetailPage | todo | |
| CustomerPricingPage | todo | |

### CRM
| Page | Status | Notes |
|------|--------|-------|
| LeadsPage | todo | KB❌ |
| PipelinePage | todo | kanban |
| OpportunityDetailPage | todo | |
| CampaignsPage | todo | KB✅ |
| CampaignDetailPage | todo | |
| TicketsPage | todo | KB❌ |

### Dashboard / cross
| Page | Status | Notes |
|------|--------|-------|
| DashboardPage | todo | "needs attention" panel; StatCard deltas |
| GettingStarted | todo | |
| SetupWizardPage | todo | onboarding |

### E-invoice / Workflows / Notifications
| Page | Status | Notes |
|------|--------|-------|
| EInvoicesPage | todo | |
| WorkflowListPage | todo | KB✅ |
| WorkflowCanvasPage | todo | React Flow canvas |
| ExecutionViewerPage | todo | |
| NodeConfigPanel | todo | |
| NotificationsPage | todo | |

### Settings / Admin
| Page | Status | Notes |
|------|--------|-------|
| ProfilePage | todo | |
| AppearancePage | todo | |
| AccessibilityPage | todo | |
| OrganizationPage | todo | |
| NotificationsSettingsPage | todo | |
| DashboardSettingsPage | todo | |
| NavigationSettingsPage | todo | reorder ↑↓ glyphs (deferred) |
| UsersPage | todo | KB❌ |
| UserDetailPage | todo | |
| RolesPage | todo | |
| RoleDetailPage | todo | permission matrix |

### Auth
| Page | Status | Notes |
|------|--------|-------|
| LoginPage | todo | |

---

## Changelog
- 2026-07-01 — tracker created (Phase 0). Systemic gaps S1–S5 logged.
- 2026-07-01 — **Phase 1.1 DONE**: bulk-actions primitive. New `components/Checkbox`, `components/BulkActionBar`,
  `hooks/useRowSelection` (x toggle / ⌘A all / shift-range / Esc clear); `minus` icon added; shared
  `.X-table__select` + `[data-selected]` CSS in data-surfaces.css; `bulk.*` i18n (1283 keys). Wired Sales
  OrdersPage (bulk approve/confirm, monochrome bar bg ink-900). Live-verified (9 rows, 2-select bar, select-all 9).
  tsc -b + parity + gate03 GREEN. Next: fan bulk-select to remaining list tables (Phase 2 per module).
- 2026-07-01 — **Phase 1.3 DONE**: finished `useListKeyboardNav` fan-out (j/k highlight, Enter/o open, cursor
  persist) to 7 list pages — Customers, Suppliers, Items, Warehouses, PriceLists, Users, Roles. Leads/Tickets
  (unlinked by design) + EInvoices (action-oriented, no detail route) intentionally excluded. tsc -b + gate03
  GREEN. Live-verified Customers (j×2 → row 1).
- 2026-07-01 — **Phase 1.2 DONE**: inline-edit fan-out. Extended `InlineEdit` with a `display` prop
  (formatted read text over a raw editable value — e.g. money). Wired PriceListDetail line cells: unit
  price (`minorToAmount`/`parseToMinor` bridge, formatted `display`) + min qty, both optimistic via
  `updateLine`. Party/Item name inline-edit deferred (needs backend PATCH — out of polish scope);
  StockCount left as its fast-tab input. tsc -b + parity (1283) + gate03 GREEN. Live-verified end-to-end
  (7.00 → 9.50 EGP, persisted server-side `price_minor:950`, then restored).
- 2026-07-01 — **Phase 1.4 DONE**: `useFormKeys` (⌘/Ctrl+Enter submit) fanned to 12 create/entry forms —
  Customers, Suppliers, Items, Warehouses, PriceLists, PriceListDetail add-line, CRM Leads/Campaigns/
  Tickets, accounting CostCenters/Budgets/FixedAssets. Esc-cancel intentionally omitted on inline
  list-page forms (collides with list-nav Esc); SetupWizard (multi-step) deferred. tsc -b + parity (1283)
  + gate03 GREEN. Live-verified Customers ⌘Enter (rows 5→6, form cleared).
- 2026-07-01 — **Phase 1.5 DONE (Phase 1 COMPLETE)**: spacing/density token audit. Finding: the spacing
  system was already coherent — the ~120 hardcoded px/rem are component *sizes* (icons, avatars, dialog
  widths, media breakpoints), not spacing. Only real drift = sub-`--space-1` micro-gaps spelled two ways
  (`2px` vs `0.125rem`). Added `--space-0-5` (2px) token; converted all ~13 gap/padding micro-values
  (CommandPalette, SegmentedControl, Sidebar, StatCard, help, settings, admin, pricing, Badge, einvoice,
  notifications). gate03 (build+CSS) GREEN; token resolves live. **Phase 1 systemic primitives all done.**
  Next: Phase 2 per-module pixel pass + bulk-select fan-out to remaining list tables.
- 2026-07-01 — **Phase 2 Sales**: Quotations bulk-select (submit/approve). Sales module verdict recorded.
- 2026-07-01 — **Phase 2 Purchasing**: bulk-select on PurchaseOrders (approve/confirm) + PurchaseRequests
  (submit/approve). Purchasing verdict recorded. (1295 keys.)
- 2026-07-01 — **Phase 2 Inventory + CRM + Accounting** + app-wide craft cleanup:
  - **CRM Leads bulk-qualify** (new→qualified), live-verified render/gating. (1297 keys.)
  - **Bulk-select verdict for the rest**: no clean list bulk where there's no lifecycle to mirror —
    Inventory (reference lists; count-post is destructive + detail-only), Accounting (journals immutable;
    rest are reports), CRM Campaigns (channel, no status) / Pipeline (kanban) / Tickets (multi-state).
    Recorded, not forced.
  - **App-wide inline-style cleanup** (real craft defect the impeccable hook flags): added `.hint`
    (muted+sm), `.grow` (flex:1), `.block-spaced` (margin-block) utilities to global.css; replaced all
    ~14 STATIC inline `style={{…}}` across 12 files (accounting ×8, crm ×4, inventory ×2) with them.
    Dynamic inline styles (Dashboard bar widths, Popover/Tooltip coords) correctly kept. `.hint` verified
    live (13px, muted). tsc -b + parity (1297) + gate03 GREEN.
  - **Whole-app bulk-select status:** all 4 transaction lists (Sales Orders/Quotations, Purchase
    Orders/Requests) + CRM Leads. No further clean candidates exist. Fan-out complete.
