# Modules

> Auto-maintained inventory of modules, their purpose, and lifecycle stage.
> Updated as each module lands. Communication between modules is only via public contracts,
> service interfaces, and domain events.

| Module | Purpose | Stage | Status |
|---|---|---|---|
| core | Cross-cutting platform: correlation IDs, structured logging, errors/catalog, event bus, repository base, transactions, Branch + abstract bases | 0–1 | done (gate01) |
| identity | Auth (JWT), users, RBAC roles, TOTP 2FA, branch scoping | 0–1 | done (gate01) |
| audit | Immutable append-only audit trail + service | 0–1 | done (gate01) |
| monitoring | Health + system-check (db/redis/storage/workers) | 0–1 | done (gate01) |
| workflow | Graph workflow engine (deterministic, crash-resumable, idempotent) + REST/SQL/Webhook adapters + DRF API (`/api/workflow/`: graph CRUD, instances, approve/reject, metrics) | 2, 4 | done (gate02, gate04) |
| forms | Dynamic forms builder feeding workflows | 2 | done (gate02) |
| web (apps/web) | "Conductor" React+TS+Vite frontend: Arabic/RTL-first i18n, design tokens, logical CSS, modern app shell (icon sidebar + command bar), dashboard (KPI cards + panels), workflow screens (React Flow canvas, execution viewer), accounting screens (COA, journal entry, list/detail, trial balance, general ledger, income statement, balance sheet, cash flow), inventory screens (stock on hand, items, warehouses, stock movement), sales screens (orders, new order, order detail w/ lifecycle actions, customers), purchasing screens (POs, new PO, PO detail w/ lifecycle actions, suppliers) | 3, 4, 5 | done (gate03–gate08) |
| accounting | COA, fiscal periods + lock, double-entry journals (atomic/balanced), trial balance, general ledger, **financial statements (Income Statement, Balance Sheet, Cash Flow)**, integer-minor-unit Money, DRF API. Planned: tax/e-invoice, banks, budgets, fixed assets; AR/AP aging + VAT return await Sales/Purchasing | 5 | GL core + statements done (gate05); rest planned |
| inventory | Items, categories, warehouses, stock movements (receive/issue/transfer), weighted-average balances, stock-on-hand valuation, DRF API + React screens; posts to GL via accounting contract (receipt→Inventory/GRNI, issue→COGS/Inventory). Planned: UoM conversions, batch/serial/expiry FEFO, counts, reorder alerts | 5 | core done (gate06); rest planned |
| sales | Customers (credit limit) + Sales Order lifecycle (draft→confirm→deliver→invoice→payment); deliver issues stock via inventory contract (COGS), invoice posts AR+revenue, payment posts cash — all via accounting/inventory contracts; DRF API + React screens. Planned: quotations, partial deliveries, discounts, FX, VAT, commissions | 5 | core done (gate07); rest planned |
| purchasing | Suppliers + PO lifecycle (draft→confirm→receive→bill→payment); receive posts GRN via inventory contract (Dr Inventory/Cr GRNI), bill runs 3-way match then clears GRNI→AP, payment posts AP/Cash; DRF API + React screens. Planned: PR + approval matrix, RFQ/comparison, partial billing, supplier rating | 5 | core done (gate08); rest planned |
| crm | Leads, pipeline, activities, campaigns, tickets/SLA | 5 | planned |
