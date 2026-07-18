# FILE_01 — Roll ComboBox + DatePicker across the app

**Goal:** no long native `<select>` and no bare `<input type="date">` left in a create/edit form.
Every one becomes the matching primitive, so selecting a customer and picking a date feel identical
on every screen.

## The rule (this is also the standing brand rule — see the Directive + erp-frontend skill)
- **Long or dynamic option list** (customers, suppliers, items, accounts, cost centers, warehouses,
  price lists, departments, …) → **`ComboBox`** (searchable).
- **Short, static list** (≤ ~7 fixed options: tax code, a status filter, yes/no, a mode) → keep the
  native `<select>` — a search box there is noise. The dimmed empty-option "Select …" text stays.
- **Any date field** → **`DatePicker`**. No raw `<input type="date">` in forms.

## Before you start (reads)
- `apps/web/src/components/ComboBox.tsx`, `DatePicker.tsx`, `Popover.tsx` — the contracts.
- `pages/sales/NewOrderPage.tsx` + `pages/accounting/JournalEntryPage.tsx` — the reference wirings.

## ComboBox targets (long/dynamic selects already carrying the "Select …" placeholder)
Sweep these; convert the long-list selects only (leave Tax and other ≤7-option selects native):
- sales: `NewQuotationPage` (customer, warehouse, item)
- crm: `PipelinePage` (customer, warehouse, item)
- inventory: `StockMovementPage` (item, from/to warehouse), `StockCountsPage` (warehouse)
- purchasing: `NewPurchaseRequestPage`, `NewPurchaseOrderPage`, `ImportInvoicePage` (supplier,
  warehouse, item)
- admin: `UsersPage`, `UserDetailPage` (department — borderline; ComboBox once it has many)
- pricing: `PriceListDetailPage`, `CustomerPricingPage` (customer, price list, item)
- accounting: `JournalEntryPage` (account, cost center — the two line selects),
  `BankReconciliationPage` (account), `BankStatementDetailPage` (contra account),
  `BudgetDetailPage` (account, period)
- Any `FilterBar` "select" value list already uses the same Popover pattern — leave it.

Pattern (per select):
```tsx
<ComboBox
  value={x}
  onChange={setX}
  placeholder={t("common.selectField", { field: t("...label...") })}
  options={(rows ?? []).map((r) => ({ value: r.code, label: `${r.code} · ${r.name}` }))}
/>
```

## DatePicker targets (`grep type="date"`)
`StockMovementPage`, `StockCountsPage`, `PriceListDetailPage` (validFrom/To),
`CustomerPricingPage` (validFrom/To), `BalanceSheetPage`, `BankReconciliationPage` (stmt + line),
`FixedAssetDetailPage`, `FixedAssetsPage` (×2), `VatReturnPage` (from/to),
`ReportBuilderPage` (from/to). (JournalEntry entry date already done.)
`FilterBar`'s inline `type="date"` value editor: convert too, so filter dates match.

Pattern: `<DatePicker value={d} onChange={setD} />` — drop `className="latin"` (the picker handles
digits). Keep any surrounding `<label className="*-field">`.

## Watch-outs
- Some line selects sit in table cells; the `Popover` is portalled so it escapes `overflow` — fine.
- Required date fields: the old `<input required>` enforced non-empty via the browser. `DatePicker`
  has no native `required`; keep the existing submit-time validation (most forms already block on
  empty — verify each still does).
- Money/qty inputs are NOT in scope. Only selects and date inputs.

## Deferred (intentionally NOT converted in the first sweep)
- **Report-page filter selects with an "All" default** — e.g. `GeneralLedgerPage` account + party,
  and the period/cost-center filters on the statement pages. Here empty means "all rows", not
  "unset", so the ComboBox empty-placeholder contract differs; convert only once the "All" option is
  modelled as an explicit first option. Long chart-of-accounts lists make these good candidates.
- **Select-as-action controls** that reset `value` to `""` after each pick (e.g.
  `BankStatementDetailPage` match-ledger-line picker) — not a field with a persistent value; leave
  native or give them a purpose-built control later.
- **Short/static selects stay native by rule** (Tax, role, status, period, type, priority, channel,
  groupBy, schedule, import column mapping).

## Gates + proof
- `cd apps/web`: `node scripts/check-i18n-parity.mjs` + `npx tsc -b`; repo root `python
  scripts/gates/gate03.py`.
- Live-check a sample per module (one sales, one purchasing, one accounting) in **both** ar and en:
  combobox filters + selects; datepicker opens, scrolls its month/year lists without closing, footer
  visible, RTL week starts Saturday.
- Run the `conductor-brand` brand-feel checklist.
