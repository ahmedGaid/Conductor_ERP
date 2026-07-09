# SESSION 01 — Sales actions (quote, quote→order, edit order draft)
# Files: erp/assistant/services/actions.py, erp/assistant/tests/test_actions.py,
#        apps/web/src/i18n/locales/{ar,en}.json (only if a card needs a new label)

**Model:** Sonnet. This is pattern-replication of the existing `create_sales_order_draft`. Say so
and let the founder `/model` down before starting.

---

## Before You Start

1. Read `FILE_00_INDEX.md` (the drafts-only rule and the actor/audit corollaries are law here).
2. Read `_build_sales_order` / `_execute_sales_order` in `actions.py` — the template you copy.
3. Read `erp/sales/contracts.py` — confirm the exact functions and args for: create quotation,
   convert quotation → sales-order draft, and updating a **draft** order's lines. Note the
   validation errors each raises (bad customer code, unknown SKU, order not in `draft` status).

"Do not write anything yet."

---

## Task A — `create_quotation_draft`

Mirror `create_sales_order_draft`, but the execute() calls the quotation-create contract, producing
a `draft` quotation. Args: `customer` (code or name), `items` (list of {item, quantity}),
`warehouse` (optional). `build_proposal`: resolve customer + price the lines (real minor-unit
totals on the card), surface a **risk line** for a customer over credit limit or with overdue
balance (reuse `customer_profile`). `kind="create"`.

## Task B — `convert_quotation`

Args: `query` (quotation number or customer name to find the quotation). `build_proposal`: find the
quotation, show its lines/total and the resulting SO-draft summary; risk line if it's already
converted or not in an approvable state. `execute`: call the convert contract → returns the new
sales-order **draft**. `kind="create"`. Card result links to the created order draft.

## Task C — `edit_sales_order_draft`

Args: `query` (order number), `items` (new/changed lines: list of {item, quantity, unit_price?}).
Only operates on an order in `draft` status — a non-draft order returns a calm `{error}` at
proposal time (never a card). `kind="update"`. `build_proposal` shows a before/after line diff with
totals. `execute` updates the draft's lines via the contract.

## Task D — register + tests

- Add all three to the `ACTIONS` list. If any needs a new arg, extend `ACTION_ARG_FIELDS`
  (currently `customer, items, supplier, warehouse, from_low_stock, query`) — add e.g. `unit_price`
  only if a contract needs it; prefer packing per-line prices inside `items` to keep the field set
  small.
- `test_actions.py`: for each action — proposal builds with real totals; confirm creates the draft
  + one `audit.record(module="assistant")` row + returns a document link; dismiss creates nothing;
  double-confirm 409s; an actor without sales-create permission is refused at proposal AND execute;
  `edit_sales_order_draft` on a confirmed (non-draft) order returns `{error}`, no card.

---

## Smoke Test

- [ ] "Quote <customer> for 3 of <item>" → card with priced lines + credit risk if any → confirm →
      draft quotation exists, audit row, card shows link
- [ ] "Turn quotation Q-… into an order" → card → confirm → SO draft created, linked
- [ ] "Change the draft order SO-… to 5 of <item>" → before/after card → confirm → draft updated
- [ ] Same edit on a *confirmed* order → calm refusal, no card
- [ ] User without sales permission → refused calmly at both stages
- [ ] `pytest erp/assistant` + (if any new string) i18n parity + tsc + gate03 green

---

## After This Session

```
Smoke test passed?
→ Rename this file: append _done.
→ Clear the session. Open FILE_02_PURCHASING_ACTIONS.md and continue.
```
