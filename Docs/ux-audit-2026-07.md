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
| S4 | **Form keys half-wired** | `useFormKeys` on 5 forms | Esc-cancel / ⌘↵-submit everywhere |
| S5 | **Stray spacing values** | 22 non-token px/rem (mostly legit sub-px) | audit, tokenize the real ones |

---

## Per-module page inventory

Status legend per page: `todo` = not yet audited · `pass` = audited, Linear-grade · `fix:<codes>` = needs work.

### Sales (high traffic — audit first in Phase 2)
| Page | Status | Notes |
|------|--------|-------|
| OrdersPage | todo | list — KB✅ ; bulk❌ |
| OrderDetailPage | todo | mockup-redesigned PR#19 |
| QuotationsPage | todo | list — KB✅ |
| QuotationDetailPage | todo | |
| NewOrderPage | todo | form |
| NewQuotationPage | todo | form |
| CustomersPage | todo | list — KB❌ bulk❌ |
| CustomerDetailPage | todo | PartyDetailView |
| InvoiceDocumentPage | todo | print/PDF — monochrome |

### Purchasing
| Page | Status | Notes |
|------|--------|-------|
| PurchaseOrdersPage | todo | KB✅ |
| PurchaseOrderDetailPage | todo | |
| PurchaseRequestsPage | todo | KB✅ |
| PurchaseRequestDetailPage | todo | |
| NewPurchaseOrderPage | todo | form |
| NewPurchaseRequestPage | todo | form |
| SuppliersPage | todo | KB❌ |
| SupplierDetailPage | todo | PartyDetailView |

### Inventory
| Page | Status | Notes |
|------|--------|-------|
| ItemsPage | todo | KB❌ |
| ItemDetailPage | todo | |
| WarehousesPage | todo | |
| WarehouseDetailPage | todo | |
| StockOnHandPage | todo | table-dense |
| StockMovementPage | todo | |
| MovementsTable | todo | shared table |
| StockCountsPage | todo | KB✅ |
| StockCountDetailPage | todo | |
| BatchesPage | todo | |

### Accounting
| Page | Status | Notes |
|------|--------|-------|
| ChartOfAccountsPage | todo | tree |
| JournalListPage | todo | KB✅ |
| JournalDetailPage | todo | |
| JournalEntryPage | todo | form — debit/credit grid |
| GeneralLedgerPage | todo | |
| TrialBalancePage | todo | report |
| BalanceSheetPage | todo | report |
| IncomeStatementPage | todo | report |
| CashFlowStatementPage | todo | report |
| VatReturnPage | todo | |
| BudgetsPage | todo | KB✅ |
| BudgetDetailPage | todo | |
| CostCentersPage | todo | |
| FixedAssetsPage | todo | KB✅ |
| FixedAssetDetailPage | todo | |
| BankReconciliationPage | todo | KB✅ |
| BankStatementDetailPage | todo | |
| ReportBuilderPage | todo | builder UX |

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
