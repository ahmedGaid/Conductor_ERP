# ERP System — End-to-End Build Specification

**Company:** General  
**Business type:** Local & imported equally  
**Company size:** Large (250+) · **Branches:** 10+ branches · **Geographic scope:** Multiple cities (local)  
**Prepared for:** Autonomous AI engineering agent  
**Generated:** 2026-06-14T08:12:58Z

---

## 0. Instructions to the AI Build Agent

Implement this ERP **end-to-end without asking for clarification**. This document is the single source of truth.

- Where a detail is unspecified, apply the **industry-standard default**, implement it, and record it under "Assumptions" (Appendix B).
- Deliver **production-ready, working** code: backend, frontend, database migrations, seed data, automated tests, and deployment files.
- All monetary values are in **EGP** unless stated. Dates ISO-8601. Timezone Africa/Cairo.
- UI must support **Arabic (RTL) + English (LTR)** with full i18n and a language switch.
- Every list view: search, filter, sort, pagination, and CSV/Excel/PDF export. Every record: a full **audit trail** (user, timestamp, before/after).
- Enforce **role-based access control (RBAC)** on every API endpoint and UI action.

### Definition of Done
1. Every module below implemented with full CRUD + listed workflows + business rules.
2. Seed data and a demo user per role.
3. Automated tests (unit + integration) covering all business rules; CI passes.
4. One-command bootstrap ("docker compose up") runs migrations + seeds and brings the whole system online.
5. API documented via OpenAPI/Swagger; README covering setup + architecture.

## 1. Architecture & Tech Stack (recommended defaults)

| Layer | Technology |
|---|---|
| Frontend | React 18 + TypeScript + Vite + TailwindCSS; i18next (ar/en, RTL-aware) |
| Backend | NestJS (Node 20, TypeScript), REST + OpenAPI |
| Database | PostgreSQL 16 with Prisma ORM (migrations + seeds) |
| Auth | JWT access/refresh, RBAC, argon2 password hashing, TOTP 2FA |
| Async/Jobs | Redis + BullMQ (alerts, payroll, report generation, integrations) |
| Storage | S3-compatible object storage for documents/attachments |
| Reporting | Server-side PDF (Puppeteer) + ExcelJS export |
| Deployment | Docker + docker-compose — target: Hybrid |

### Global requirements derived from the answers
- **Multi-branch:** 10+ branches → enforce per-branch data scoping, inter-branch transfers, and consolidated + per-branch reporting.
- **Multi-currency:** YES → store currency + FX rate on every transaction; support revaluation.
- **Taxation:** VAT registered; ETA e-invoicing integration: YES.
- **Expected concurrent users:** 100+ users → size connection pools/caching accordingly.
- **Hosting:** Hybrid; **Backup policy:** —.
- **Security requirements:** Two-Factor Authentication (2FA), Role-based access, Full audit log, Data encryption, IP whitelisting.
- **Access methods:** Web browser (LAN), Web browser (remote).
- **Current systems to migrate/replace:** Excel / Google Sheets, Local accounting software, Existing ERP, Manual on demand, Custom scheme, Point of Sale (POS).
- **Primary pain points to solve:** Data loss, Manual entry errors, Difficult reporting, Inaccurate inventory, Slow invoicing, Lack of system integration, No performance visibility, Difficulty tracking customers, Complex internal approvals, Weak cost control.
- **Target go-live:** 1–3 months.

### Shared data-model conventions
- Every table: id (uuid), created_at, updated_at, created_by, updated_by, branch_id (mandatory scope), soft-delete (deleted_at).
- Money stored as integer minor units + currency; never floats.
- All documents have a status state-machine and a sequential, branch-scoped number series.

## 2. Functional Modules

### 2.1 Sales & Customers

**Purpose:** Order-to-cash for Local & imported equally customers across channels: Showroom / Office, Field sales reps, Phone / Call center, Website, WhatsApp Business API, Social media, Online marketplaces.

**Entities & key fields:**
- Customer(code, name, type[B2B/B2C/B2G], tax_id, price_list_id, credit_limit, payment_terms, currency, opening_balance, branch_id, is_active)
- CustomerContact, CustomerAddress(billing/shipping)
- PriceList, PriceListItem(item_id, currency, unit_price, min_qty)
- Quotation(no, customer_id, date, valid_until, status[draft/pending_approval/approved/sent/won/lost], lines)
- QuotationLine(item_id, description, qty, unit_price, discount, tax_code, line_total)
- SalesOrder(no, quotation_id?, customer_id, date, fulfillment_status, payment_status, lines)
- DeliveryNote(no, sales_order_id, warehouse_id, date, lines[item, qty_delivered]) → posts stock-OUT
- SalesInvoice(no, sales_order_id?, customer_id, date, due_date, currency, fx_rate, subtotal, tax_total, total, status[draft/posted/paid/partially_paid/void]) → posts AR + GL
- ReceiptVoucher(no, customer_id, date, method, amount, allocations[invoice_id, amount])
- SalesReturn/CreditNote(no, invoice_id, reason, restock[bool], lines)
- SalesCommission(rep_id, basis, percent, amount, status) — REQUIRED

**Workflow:** Lead → Quotation → Internal approval → Sales Order → Delivery Note → Invoice → Payment Collection → Returns.

**Business rules:**
- Quotation requires internal approval before sending: YES (block "sent" until approved).
- Enforce customer credit limit: YES (warn+block new orders when (balance + order) > limit).
- Multi-currency invoicing with FX rate captured per document: YES.
- Discounts/promotions engine (line + document level): YES.
- Sales-rep commissions accrual: YES.
- Accepted payment methods: Cash, Bank Transfer, RFID card, Cheque, Digital Wallets, Installments.

**Reports:** Sales by period/customer/product/rep, quotation win-rate, AR aging, returns analysis.
**Roles:** Sales Rep (own records), Sales Manager (approve + all), Accountant (invoices/receipts).
**Acceptance:** Posting an invoice from a delivered order atomically updates stock, AR balance, and GL; credit-limit rule blocks exactly when configured.

### 2.2 Purchasing & Suppliers

**Purpose:** Procure-to-pay. Supplier sourcing: Local & imported equally.

**Entities & key fields:**
- Supplier(code, name, tax_id, payment_terms, currency, rating, contract_id?, branch_id)
- PurchaseRequest(no, requester_id, dept, status, lines) — internal demand
- RFQ(no, lines, suppliers[]) + SupplierQuote(supplier_id, prices) + QuoteComparison
- PurchaseOrder(no, supplier_id, date, expected_date, currency, fx_rate, status[draft/pending/approved/sent/received/closed], lines)
- GoodsReceiptNote(no, po_id, warehouse_id, date, lines[item, qty_received, qc_status]) → posts stock-IN
- SupplierInvoice/Bill(no, po_id?, grn_id?, date, due_date, totals, status) → posts AP + GL
- PaymentVoucher(no, supplier_id, method, amount, allocations)
- PurchaseReturn(no, grn_id, reason, lines)
- SupplierRating(supplier_id, period, score) — REQUIRED
- SupplierContract(supplier_id, start, end, terms) — REQUIRED

**Workflow:** Purchase Request (PR) → Request for Quotation (RFQ) → Supplier comparison → Purchase Order (PO) → Goods Receipt (GRN) → Supplier invoice → Payment Collection → Return to supplier.

**Business rules:**
- Approval levels on POs: By amount (tiered) (implement configurable approval matrix).
- 3-way match (PO + GRN + Invoice) required before payment: YES (block payment on mismatch beyond tolerance).
- Supplier performance rating: YES.
- Annual supplier contracts: YES.

**Reports:** Purchases by period/supplier/item, PO status, AP aging, price variance, supplier scorecard.
**Roles:** Buyer, Purchasing Manager (approve), Warehouse (GRN), Accountant (bill/pay).
**Acceptance:** Payment is blocked unless 3-way match passes (when enabled); GRN increments stock and accrues AP.

### 2.3 Warehouses & Inventory

**Purpose:** Multi-warehouse stock control. Warehouses: 10+ branches; SKUs: 10,000+ items.

**Entities & key fields:**
- Item(code, name_ar, name_en, category_id, base_uom, type, barcode, is_stockable, costing_method, reorder_point, reorder_qty)
- ItemCategory, UoM, UoMConversion(from_uom, to_uom, factor) — REQUIRED (multi-UoM)
- Warehouse, Bin/Location
- StockMovement(item_id, warehouse_id, bin_id, qty, direction[in/out], source_doc, unit_cost, datetime)
- StockBalance(item_id, warehouse_id, qty_on_hand, qty_reserved, avg_cost) — derived/maintained
- Batch(item_id, batch_no, mfg_date, expiry_date) — REQUIRED
- SerialNumber(item_id, serial, status) — REQUIRED
- StockCount(no, warehouse_id, date, lines[item, system_qty, counted_qty, variance]) → adjustment posting
- ReorderRule(item_id, warehouse_id, min, max) → low-stock alert job

**Item types in scope:** Finished goods, Raw materials, Work-in-Progress (WIP), Spare parts, Consumables, Packaging materials, Services.

**Business rules:**
- Costing method: Not decided (apply consistently to all valuations).
- Barcode/QR tracking: YES.
- Expiry-date tracking + FEFO picking + expiry alerts: YES.
- Batch/Lot tracking: YES.
- Serial-number tracking: YES.
- Multiple units of measure: YES.
- Periodic physical stock count + variance posting: YES.
- Automatic low-stock reorder alerts: YES.

**Reports:** Stock on hand by warehouse, movement ledger, valuation, near-expiry, reorder, ABC analysis, dead stock.
**Roles:** Warehouse Clerk, Inventory Manager, Auditor.
**Acceptance:** Every stock movement updates balances and posts inventory GL at the chosen costing method; expiry/batch/serial rules enforced exactly as flagged.

### 2.4 Accounting & Finance

**Purpose:** General ledger and financial control. Tax status: VAT registered; fiscal year starts January.

**Entities & key fields:**
- ChartOfAccounts(code, name, type[asset/liability/equity/income/expense], parent_id)
- JournalEntry(no, date, period, source, status[draft/posted], lines) + JournalLine(account_id, debit, credit, cost_center_id?, currency, fx_rate)
- AccountingPeriod, FiscalYear (lock/close)
- CostCenter — REQUIRED
- BankAccount/CashBox, BankReconciliation — multiple accounts REQUIRED
- TaxCode(rate, type) ; EInvoiceSubmission(invoice_id, uuid, status) — ETA e-invoicing REQUIRED
- Budget(account_id, period, amount) + variance — REQUIRED
- FixedAsset(code, category, acquisition_cost, useful_life, method, accumulated_depr) + DepreciationRun — REQUIRED

**Business rules:**
- Double-entry, balanced postings only; period locking after close.
- Tax authority e-invoicing integration: YES (Egypt ETA: UUID, signing, submission, status polling).
- Bilingual invoices (Arabic + English) layout: YES.
- Cost-center dimension on postings: YES.
- Multiple banks/cash funds + reconciliation: YES.
- Budgeting & budget-vs-actual: YES.
- Fixed assets & depreciation: YES.

**Required statements/reports:** Income Statement, Balance Sheet, Cash Flow Statement, Trial Balance, AR Aging, AP Aging, VAT Report, General Ledger.
**Roles:** Accountant, Chief Accountant (post/close), Auditor (read).
**Acceptance:** Trial balance always balances; closing a period prevents back-dated postings; VAT/e-invoice output validates against authority schema when enabled.

### 2.5 CRM

**Purpose:** Customer relationship management.

**Entities & key fields:**
- Lead(source, contact, status, owner), Opportunity(stage, value, probability, expected_close)
- Activity(type[call/meeting/email], due, outcome), Campaign(channel, budget, ROI)
- SupportTicket(customer_id, subject, priority, status, SLA)

**Features in scope:** —.

**Business rules:**
- Pipeline stages with conversion to Sales Order on win (integrate with Sales module).
- SLA timers + escalation on support tickets.

**Reports:** Pipeline, conversion funnel, activity log, campaign ROI, ticket SLA compliance.
**Roles:** Sales Rep, Marketing, Support Agent, Manager.
**Acceptance:** Winning an opportunity creates a linked Sales Order; SLA breaches escalate automatically.

## 3. Reporting & Dashboards

- **Access control for reports:** Role-based access.
- **Dashboard KPIs (home screen widgets):** Today's sales, This month's sales, Top products, Top customers, Stock levels, Cash position, Overdue invoices, Profit margin, Purchases summary, Employee attendance.
- **Required export formats:** Excel / Google Sheets, PDF, CSV, Direct print, Share via WhatsApp.
- Provide a report builder with date-range, branch, and dimension filters; schedule + email delivery of key reports.

## 4. External Integrations

Implement adapters (with retry/idempotency via the job queue) for: Excel / Google Sheets, Send by email, WhatsApp Business API, SMS, Tax authority (e-invoicing), Bank integration, Payment gateways, Shipping companies, Website / Online store, Mobile app + GPS, Biometric devices, Barcode scanners, Existing accounting system.
- **Egypt ETA e-invoicing:** document signing, UUID generation, submission, and status polling.
- **Payment gateways:** tokenized payments + webhook reconciliation to receipts.
- **WhatsApp Business API:** send invoices/notifications + delivery status.

## 5. Security, Roles & Infrastructure

- **RBAC:** roles per module (see each module's Roles). Default roles: System Admin, Branch Manager, Accountant, plus module operators.
- **Security controls:** Two-Factor Authentication (2FA), Role-based access, Full audit log, Data encryption, IP whitelisting.
- **Hosting target:** Hybrid; **backup:** — (automated, restorable, tested).
- **Access channels:** Web browser (LAN), Web browser (remote).
- Full audit logging, rate limiting, input validation, and OWASP Top-10 hardening.

## 6. Non-Functional Requirements

- Page loads < 2s on typical data; list endpoints paginated and indexed.
- Horizontal-scalable stateless API; background jobs isolated from request path.
- Automated DB backups per the stated policy; disaster-recovery runbook.
- Observability: structured logs, health checks, error tracking, basic metrics.

## 7. Delivery Plan (suggested phases)
1. Foundation: auth, RBAC, org/branch setup, master data (items, customers, suppliers, COA).
2. Core transactional modules selected above (in dependency order: Inventory/Finance first).
3. Reporting, dashboards, exports.
4. Integrations + e-invoicing.
5. Hardening, tests, deployment, seed/demo data.

## Appendix B — Assumptions register

The agent must populate this section with every default decision it made where the spec was silent.



---

# Appendix A — Raw Questionnaire Answers

# ERP System Requirements — General

> **Submitted:** 2026-06-14 08:12:58 UTC  
> **Form Version:** v3.0 Smart  
> **Prepared by:** Ahmed Mohamed Gaid (ahmedgaid14@gmail.com)

---

## 1. Company Information

| Field | Value |
|---|---|
| Company Name | General |
| Business Type | Local & imported equally |
| Company Size | Large (250+) |
| Number of Branches | 10+ branches |
| Geographic Scope | Multiple cities (local) |
| Years in Business | 10+ branches |

### Contact Details

| Field | Value |
|---|---|
| Full Name | Ahmed Mohamed Gaid |
| Position | Owner / Founder |
| Phone | 01010665106 |
| Email | ahmedgaid14@gmail.com |

---

## 2. Current Status

- **Current systems in use:** Excel / Google Sheets, Local accounting software, Existing ERP, Manual on demand, Custom scheme, Point of Sale (POS)
- **Main pain points:** Data loss, Manual entry errors, Difficult reporting, Inaccurate inventory, Slow invoicing, Lack of system integration, No performance visibility, Difficulty tracking customers, Complex internal approvals, Weak cost control
- **Target go-live timeline:** 1–3 months

---

## 3. Required Modules & Priorities

| Module | Selected | Priority |
|---|---|---|
| Sales & Customers | ☑ Yes | 3 |
| Purchasing & Suppliers | ☑ Yes | 4 |
| Warehouses & Inventory | ☑ Yes | 2 |
| Accounting & Finance | ☑ Yes | 1 |
| Human Resources & Payroll | ☐ No | — |
| Manufacturing & Production | ☐ No | — |
| Project Management | ☐ No | — |
| Assets & Maintenance | ☐ No | — |
| CRM | ☑ Yes | 5 |
| Point of Sale (POS) | ☐ No | — |
| Fleet Management | ☐ No | — |
| Quality Control | ☐ No | — |

### Automatic Cost Estimate

Enterprise Package | Estimated total: 104,800 EGP | Annual maintenance: 15,720 EGP
  - Base / Core package: 8,000 EGP
  - Module: Sales & Customers: 5,000 EGP
  - Module: Purchasing & Suppliers: 4,000 EGP
  - Module: Warehouses & Inventory: 5,000 EGP
  - Module: Accounting & Finance: 6,000 EGP
  - Module: CRM: 4,000 EGP
  - Company size: Large (250+): 9,000 EGP
  - Number of branches: 10+ branches: 9,000 EGP
  - Geographic scope: Multiple cities (local): 800 EGP
  - Concurrent users: 100+ users: 10,000 EGP
  - Hosting: Hybrid: 4,000 EGP
  - Number of warehouses: 10+ branches: 6,000 EGP
  - Item count: 10,000+ items: 4,000 EGP
  - External integrations (13): 15,600 EGP
  - CRM features (7): 4,900 EGP
  - Payment methods (2): 3,000 EGP
  - Export formats (1): 1,500 EGP
  - Dashboard KPIs (5): 2,500 EGP
  - Tax authority e-invoicing: 2,500 EGP

_Indicative estimate — final quotation after the requirements analysis session._

---

## 4. Sales & Customers

| Field | Value |
|---|---|
| Primary Customer Type | Local & imported equally |

- **Sales channels:** Showroom / Office, Field sales reps, Phone / Call center, Website, WhatsApp Business API, Social media, Online marketplaces
- **Sales cycle stages:** Lead, Quotation, Internal approval, Sales Order, Delivery Note, Invoice, Payment Collection, Returns
- **Payment methods accepted:** Cash, Bank Transfer, RFID card, Cheque, Digital Wallets, Installments

| Question | Answer |
|---|---|
| Quotations require internal approval | ✅ Yes |
| Customer credit limits in use | ✅ Yes |
| Multi-currency transactions | ✅ Yes |
| Discounts & promotional pricing | ✅ Yes |
| Sales rep commissions | ✅ Yes |

---

## 5. Purchasing & Suppliers

| Field | Value |
|---|---|
| Supplier sources | Local & imported equally |
| Purchase approval levels | By amount (tiered) |

- **Purchase cycle stages:** Purchase Request (PR), Request for Quotation (RFQ), Supplier comparison, Purchase Order (PO), Goods Receipt (GRN), Supplier invoice, Payment Collection, Return to supplier

| Question | Answer |
|---|---|
| 3-way matching (PO + GRN + Invoice) | ✅ Yes |
| Supplier performance rating | ✅ Yes |
| Annual supplier contracts | ✅ Yes |

---

## 6. Warehouses & Inventory

| Field | Value |
|---|---|
| Number of warehouses | 10+ branches |
| Approximate item count | 10,000+ items |
| Inventory costing method | Not decided |

- **Item types:** Finished goods, Raw materials, Work-in-Progress (WIP), Spare parts, Consumables, Packaging materials, Services

| Question | Answer |
|---|---|
| Barcode / QR Code tracking | ✅ Yes |
| Expiry date tracking | ✅ Yes |
| Batch / Lot number tracking | ✅ Yes |
| Serial number tracking | ✅ Yes |
| Multiple units of measure (UoM) | ✅ Yes |
| Periodic physical stock count | ✅ Yes |
| Low-stock reorder alerts | ✅ Yes |

---

## 7. Accounting & Finance

| Field | Value |
|---|---|
| Tax status | VAT registered |
| Fiscal year starts | January |

- **Required financial reports:** Income Statement, Balance Sheet, Cash Flow Statement, Trial Balance, AR Aging, AP Aging, VAT Report, General Ledger

| Question | Answer |
|---|---|
| Tax authority e-invoicing integration | ✅ Yes |
| Bilingual invoices (Arabic + English) | ✅ Yes |
| Cost centers | ✅ Yes |
| Multiple bank accounts / cash funds | ✅ Yes |
| Budget management | ✅ Yes |
| Fixed assets & depreciation | ✅ Yes |

---

## 16. Reporting & Dashboards

| Field | Value |
|---|---|
| Reports access control | Role-based access |

- **Dashboard KPIs:** Today's sales, This month's sales, Top products, Top customers, Stock levels, Cash position, Overdue invoices, Profit margin, Purchases summary, Employee attendance
- **Export formats needed:** Excel / Google Sheets, PDF, CSV, Direct print, Share via WhatsApp

---

## 17. External Integrations

- **Required integrations:** Excel / Google Sheets, Send by email, WhatsApp Business API, SMS, Tax authority (e-invoicing), Bank integration, Payment gateways, Shipping companies, Website / Online store, Mobile app + GPS, Biometric devices, Barcode scanners, Existing accounting system

---

## 18. Infrastructure & Hosting

| Field | Value |
|---|---|
| Hosting preference | Hybrid |
| Concurrent users (expected) | 100+ users |
| Backup requirements | — |

- **Access methods:** Web browser (LAN), Web browser (remote)
- **Security requirements:** Two-Factor Authentication (2FA), Role-based access, Full audit log, Data encryption, IP whitelisting

---

## 19. Goals & Final Notes

- **Management goals:** Cost reduction, Operational efficiency, Data accuracy, Performance visibility, Customer satisfaction, Legal & tax compliance, Support growth & expansion, Better decision-making

---

*Auto-generated by ERP Requirements Questionnaire v3.0*
