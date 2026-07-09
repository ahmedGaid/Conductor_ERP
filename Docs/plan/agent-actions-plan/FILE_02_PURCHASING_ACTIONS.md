# SESSION 02 — Purchasing actions (PO draft, request→PO, onboard supplier)
# Files: erp/assistant/services/actions.py, erp/assistant/tests/test_actions.py,
#        apps/web/src/i18n/locales/{ar,en}.json (only if a card needs a new label)

**Model:** Sonnet. Pattern-replication of `create_purchase_request_draft`. Say so, let the founder
`/model` down.

---

## Before You Start

1. Read `FILE_00_INDEX.md` (drafts-only law).
2. Read `_build_purchase_request` / `_execute_purchase_request` — the template.
3. Read `erp/purchasing/contracts.py` — confirm functions/args for: create PO (draft), convert a
   purchase request → PO draft, create supplier. Note validation errors (unknown supplier, SKU,
   request not convertible).

"Do not write anything yet."

---

## Task A — `create_purchase_order_draft`

Distinct from the existing *request* action: this drafts a PO directly. Args: `supplier`,
`items` (list of {item, quantity, unit_cost?}), `warehouse` (optional). `build_proposal` resolves
supplier + costs the lines (real totals); risk line if any item has no cost on record (so the buyer
knows to fill it). `execute` creates a `draft` PO. `kind="create"`.

## Task B — `convert_purchase_request`

Args: `query` (request number or supplier name). `build_proposal`: find the request, show lines +
resulting PO-draft summary; risk if not in an approvable/convertible state. `execute` calls the
convert contract → new PO **draft**, card links to it. `kind="create"`.

## Task C — `create_supplier`

Direct mirror of the existing `create_customer`: args `query` (supplier name), optional
`phone`/`tax_id` if the contract takes them. **Duplicate-check first** — a near-match supplier is a
**risk line on the card**, never a silent create. `kind="create"`.

## Task D — register + tests

- Add all three to `ACTIONS`. Reuse existing arg fields (`supplier`, `items`, `warehouse`, `query`).
- `test_actions.py`: proposal totals real; confirm creates draft + audit + link; dismiss inert;
  double-confirm 409; unpermitted actor refused both stages; `create_supplier` near-duplicate
  surfaces the risk line (mirror the existing `create_customer` duplicate test).

---

## Smoke Test

- [ ] "Draft a PO to <supplier> for 10 of <item>" → costed card → confirm → PO draft + audit + link
- [ ] Item with no cost on record → risk line shown, still confirmable
- [ ] "Convert purchase request PR-… to an order" → card → confirm → PO draft linked
- [ ] "Add a supplier called <name>" where a near-match exists → duplicate risk line, not silent create
- [ ] User without purchasing permission → refused calmly both stages
- [ ] `pytest erp/assistant` + (if any new string) i18n parity + tsc + gate03 green

---

## After This Session

```
Smoke test passed?
→ Rename this file: append _done.
→ Clear the session. Open FILE_03_INVENTORY_ACTIONS.md and continue.
```
