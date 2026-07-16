# SESSION — Partial Payments / Collections UI (pre-handover blocker #1)
# Files: apps/web/src (sales collect dialog + purchasing payment dialog + api clients), erp/sales + erp/purchasing API tests (extend), i18n locales

Why blocking: FILE_03 known-issue — "collect" and "register payment" always settle the FULL
outstanding balance. Egyptian SMBs run on partial collections; a cash business can't operate
day one without this. The service layer already supports partial amounts — this is UI + API
verification only.

---

## Before You Start

1. Open `erp/sales/` collect/receipt service fn → confirm the partial-amount parameter, its
   validation, and what "remaining balance" it returns/derives.
2. Open `erp/purchasing/` register-payment service fn → same.
3. Open the current collect dialog + payment dialog in `apps/web/src/pages/` → the exact
   components to extend (extend, don't fork).
4. Open `lib/money.ts` → amount input handling (integer minor units at the edge).

"Do not write anything yet."

---

## Task A — Amount field in both dialogs

Default = full outstanding (pre-filled, so the one-click flow stays one-click). Editable:
validate 0 < amount ≤ outstanding, human ar/en errors ("المبلغ أكبر من المتبقي"), minor units on
the wire. Show, live in the dialog: outstanding now → paying → remaining after.

## Task B — Document state honesty

After a partial payment: document stays open/unsettled with remaining balance visible on the
detail page and in list meta (reuse existing status chip + amount display; wording from the
canonical lexicon — likely «سداد جزئي», confirm in Identity System §6 BEFORE shipping).
Multiple partials accumulate until settled; each is its own audit row + timeline entry.

## Task C — API tests (backend truth)

Extend `pytest erp/sales` + `erp/purchasing` API tests: partial then remainder → settled;
overpay rejected; zero rejected; two partials sum correctly in the ledger (trial balance still
balances — assert).

---

## Smoke Test

- [ ] Invoice 10,000 EGP → collect 4,000 → doc open, remaining 6,000 shown; collect 6,000 → settled
- [ ] Same on purchasing payment side
- [ ] Overpay + zero rejected with human ar/en message
- [ ] Ledger/trial balance correct after partial sequence
- [ ] RTL dialogs correct; parity + `npx tsc -b` + gate03 green; brand checklist; `pytest erp/sales erp/purchasing` green

---

## After This Session

```
Smoke test passed?
→ Rename with _done. Update erp-status. /compact.
→ Open FILE_06_PROVISIONING.md in a FRESH session.
```
