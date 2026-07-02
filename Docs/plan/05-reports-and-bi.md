# Session 05 — Reports + BI layer

**Goal:** a reporting layer that turns the now-complete data (accounting + costing + HR) into the
statements and dashboards an SMB owner and accountant actually open daily. A report builder already
exists — this session deepens it into a trustworthy financial reporting suite. Recall
`conductor-brand` + `erp-frontend`. Branch `feat/reports-bi`.

## Scope
- **Statutory financials:** Trial Balance, P&L (income statement), Balance Sheet, Cash Flow — with
  period comparison and drill-down to source documents (reuse `EntityLink`/`StageSnapshot`).
- **Operational:** AR/AP aging, inventory valuation (from Session 03), sales by
  item/customer/branch, gross margin, payroll summary (from Session 04).
- **Owner dashboard:** the "one screen a busy owner checks each morning" — cash position, overdue
  receivables, low stock, month revenue vs last month. Calm, monochrome, colour only inside content.

## Tasks
1. Build financial statements as **queries over the GL**, not stored snapshots — always live,
   always reconcilable. Trial Balance is the base; P&L and Balance Sheet are groupings of it by
   account type. Add the account-type roll-up config if missing.
2. **Reconciliation invariants (trust):** Balance Sheet balances (assets = liabilities + equity);
   P&L net income flows to retained earnings; TB debits == credits. Add to the invariant suite
   (Session 01). These are the tests that let you say "the numbers are never wrong."
3. **Drill-down everywhere:** every figure on every statement clicks through to the journals/
   documents behind it. This is the trust differentiator vs spreadsheet-based SMB accounting.
4. **Exports:** reuse the existing `ReportTable`/`export_response` engine (CSV/PDF). Scheduled
   reports already exist (Celery beat) — extend saved-report definitions to the new statements.
5. **Performance:** statements must render fast on a year of data — pre-aggregate where needed,
   respect Session 01 budgets, index GL by (account, date, branch).
6. **AI tie-in (optional, if Session 02 shipped):** the assistant's read tools can answer questions
   over these same aggregates ("why is margin down this month?").
7. **UI:** report viewer with period picker, comparison, drill-down; owner dashboard as the default
   post-login landing for the owner role. Designed empty/loading states; every string ar/en.

## Done bar
- TB, P&L, Balance Sheet, Cash Flow render correct, balanced, and drill through to source docs.
- Reconciliation invariants pass; statements meet Session 01 latency budget on a year of seed data.
- `gate:all` GREEN; parity + `tsc -b` + `gate03` GREEN.
