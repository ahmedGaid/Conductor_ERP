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
| workflow | Graph workflow engine (deterministic, crash-resumable, idempotent) + adapters | 2 | planned |
| forms | Dynamic forms builder feeding workflows | 2 | planned |
| accounting | GL, COA, journals, periods, tax/e-invoice, budgets, fixed assets | 5 | planned |
| inventory | Items, warehouses, stock movements/balances, batch/serial/expiry, counts | 5 | planned |
| sales | Quotation→SO→delivery→invoice→receipt→returns | 5 | planned |
| purchasing | PR→RFQ→PO→GRN→bill→payment, 3-way match | 5 | planned |
| crm | Leads, pipeline, activities, campaigns, tickets/SLA | 5 | planned |
