# SESSION 16 — Finance Adapters: Journals, Payments, Opening Balances
# Files: erp/imports/adapters/accounting.py, adapters/inventory.py (extend) (new/extend), erp/imports/tests/test_finance_adapters.py (new)

---

## Before You Start

1. Open `erp/accounting/services/` → journal-entry creation (draft), payment/receipt
   creation, chart-of-accounts lookup; `erp/inventory/services/` → opening-balance /
   adjustment transaction path. Note the roadmap Phase A promise: **trial balance must
   balance or the import proposes the correcting entry.**
2. Open session 15's group machinery — journal entries are grouped rows too (entry number →
   debit/credit lines).

"Do not write anything yet."

---

## Task A — `journal_entries` adapter (grouped)

Lines: account (code or name → COA lookup with normalized matching), debit, credit (money),
description, date, reference. Group validation: **sum(debit) == sum(credit) per entry** →
else group error "unbalanced_entry" showing the difference (money-formatted at the edge).
Batch-level: whole-file imbalance summary in stats. Drafts only; posting on module screens.

## Task B — `payments` + `receipts` adapters

Party ref (customer/supplier), amount, date, method (normalize: cash/transfer/cheque +
Arabic نقدي/تحويل/شيك), account/treasury ref, invoice reference OPTIONAL — if the file links
payments to invoice numbers, resolve to the imported/existing invoice and pass allocation to
the service if it supports it; else import unallocated + warning (allocation is a human step).

## Task C — Opening balances

- `inventory_opening`: item ref, warehouse ref, qty, unit cost (money) → the module's opening/
  adjustment service, dated to the opening date (batch-level option field).
- `account_opening` (GL opening balances): account + debit/credit → ONE generated balanced
  opening journal entry; imbalance → the correcting-entry proposal: preview shows a generated
  balancing line to a configurable suspense account (`IMPORTS_DEFAULTS`), user must approve it
  explicitly in the creation-plan panel — never silently inserted (Phase A promise, delivered
  human-in-the-loop).
- `inventory_transactions` (historic movements): same path as opening but per-date; mark
  clearly in the UI copy that historic COST recalculation follows module rules — check the
  costing engine's stance (read `erp/inventory` costing docs/code) and STOP with a blocker if
  backdated movements violate it.

## Task D — Tests

Balanced entry imports as draft; unbalanced → group error with difference; GL opening
imbalance → proposed suspense line, approval required, approved import balances exactly;
payments resolve party + optional invoice allocation; inventory opening creates the right
transaction; backdated-cost blocker path (if applicable) surfaces cleanly.

---

## Smoke Test

- [ ] Trial-balance fixture (40 accounts, balanced) → one draft opening entry, TB matches to the piastre
- [ ] Same fixture minus one line → correcting-entry proposal, approve → balanced
- [ ] Journal file with a bad entry → only that entry errors, rest import
- [ ] Payments file: allocated where invoice number matches, warning where not
- [ ] `pytest erp/imports` green — plus `pytest erp/accounting erp/inventory` (regression)

---

## After This Session

```
Smoke test passed?
→ Rename with _done. Update erp-status. /compact.
→ Open FILE_17_ACCEPTANCE.md in a FRESH session.
```
