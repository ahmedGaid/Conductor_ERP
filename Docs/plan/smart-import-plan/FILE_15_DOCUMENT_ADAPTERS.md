# SESSION 15 — Document Adapters: Sales & Purchasing
# Files: erp/imports/adapters/sales.py, adapters/purchasing.py (extend), erp/imports/engine.py (group support), erp/imports/tests/test_document_adapters.py (new)

---

## Before You Start

1. Open the module write-paths for: quotations + orders (`erp/sales/services/`), sales
   invoices (find where invoices are created — sales or accounting), purchase orders +
   invoices (`erp/purchasing/services/`). Note EXACTLY how lines are passed (list-of-dicts
   arg? separate calls?) and what "draft" means per document — **imports create DRAFTS;
   posting stays on module screens** (STRATEGY §3 mechanic 3).
2. Open `erp/imports/registry.py` → `group_by` (session 1 planted it) and `engine.py`'s
   per-row loop — this session teaches the engine about row GROUPS.

"Do not write anything yet."

---

## Task A — Group support in the engine

Flat Excel reality: one row per LINE, document fields repeated (or filled only on the first
line). Add to analyze/engine:

```python
# adapter.group_by = "invoice_number" → rows bucketed by normalized group key.
# Header fields (customer, date, currency…) taken from first row of group; conflicting
# header values within one group → group-level issue "inconsistent_document".
# Blank group key rows → attached to the previous group IF header fields empty
# (merged-cell export pattern), else error.
# Execution: one group = one write call = one document, atomic within the chunk;
# group fails → whole group's rows → error, not a half-document.
# Duplicate detection for documents: natural key = document number (+ party) vs DB → the
# strategy decides (skip_existing default); in-file same number+different content → error.
```

## Task B — Five adapters

`sales_quotations`, `sales_orders`, `sales_invoices`, `purchase_orders`, `purchase_invoices`.
Each: header FieldSpecs (doc number, party ref, date, currency, warehouse?, payment terms?) +
line FieldSpecs (item ref, qty, unit, unit_price money, discount?, tax token) — refs resolve
via existing adapters' lookups (customer/supplier/item/warehouse/unit); tax tokens resolve to
configured tax records (normalize_tax + accounting lookup). `write(actor, group)` builds the
service call for a DRAFT document. Totals: NEVER trust file totals — the module service
computes; if the file HAS a total column, compare and attach a `total_mismatch` WARNING
(not error) with both numbers — the classic dirty-data catch.

## Task C — Tests

Fixture: 3 invoices / 7 lines, repeated headers + one merged-cell-style blank block. Groups
build right; draft invoices created with computed totals; mismatched file total → warning;
inconsistent customer within one invoice number → group error; group atomicity on line-3
failure; existing invoice number honored per strategy.

---

## Smoke Test

- [ ] Real-shaped invoice sheet → 3 draft sales invoices, lines exact, totals computed
- [ ] Preview UI shows the grouped document (session 13 grid renders group headers — verify, small CSS fix allowed)
- [ ] Purchase invoice path same, supplier-side
- [ ] Rollback deletes the drafts (they're unposted)
- [ ] `pytest erp/imports` green

---

## After This Session

```
Smoke test passed?
→ Rename with _done. Update erp-status. /compact.
→ Open FILE_16_FINANCE_ADAPTERS.md in a FRESH session.
```
