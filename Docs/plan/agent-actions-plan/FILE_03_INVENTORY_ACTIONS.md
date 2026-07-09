# SESSION 03 — Inventory actions (transfer draft, count draft, set reorder point)
# Files: erp/assistant/services/actions.py, erp/assistant/tests/test_actions.py,
#        apps/web/src/i18n/locales/{ar,en}.json (only if a card needs a new label)

**Model:** Sonnet. Pattern-replication. Say so, `/model` down.

---

## Before You Start

1. Read `FILE_00_INDEX.md` (drafts-only law — this file is where it bites hardest).
2. Read an existing action pair as the template.
3. Read `erp/inventory/contracts.py` — confirm functions/args for: create a stock **transfer**
   draft (between two warehouses), open a stock **count** (draft/in-progress, not yet posted), and
   update an item's **reorder point** (a master-data edit). Note: `adjust_stock` / `receive` POST
   movements and hit the GL — those are **out of scope** (see FILE_06 deferred decision). Only draft
   / master-edit operations here.

"Do not write anything yet."

---

## Task A — `create_stock_transfer_draft`

Args: `item` (SKU or name), `quantity`, `from_warehouse`, `to_warehouse`. `build_proposal` resolves
the item + both warehouses, shows on-hand at source (reuse `stock_on_hand`) and a **risk line** if
the transfer would exceed available quantity. `execute` creates a `draft` transfer — it does NOT
post the movement. `kind="create"`.

## Task B — `create_stock_count_draft`

Args: `warehouse`, optional `scope` (e.g. a category or "all"). `build_proposal` shows how many item
lines the count will cover. `execute` opens a draft/in-progress count for a human to enter figures
and post later. `kind="create"`.

## Task C — `set_reorder_point`

Args: `item` (SKU or name), `reorder_point` (quantity). Master-data edit. `build_proposal` shows the
current vs new reorder point and current on-hand (context for the choice). `execute` updates the
item master. `kind="update"`.

## Task D — register + tests

- Add three to `ACTIONS`; extend `ACTION_ARG_FIELDS` with `from_warehouse`, `to_warehouse`,
  `reorder_point`, `quantity`, `scope` as needed (add only the fields a contract actually consumes).
- `test_actions.py`: transfer proposal shows source on-hand + over-quantity risk; confirm creates a
  **draft** transfer (assert no stock movement / GL row posted) + audit + link; count opens draft;
  `set_reorder_point` updates the master + audit; dismiss inert; double-confirm 409; unpermitted
  actor refused both stages.

---

## Smoke Test

- [ ] "Move 20 of <item> from <wh A> to <wh B>" → card with source on-hand → confirm → **draft**
      transfer exists, no posted movement, audit + link
- [ ] Transfer more than on-hand → risk line shown
- [ ] "Start a stock count in <warehouse>" → card → confirm → draft count opened
- [ ] "Set reorder point of <item> to 50" → current-vs-new card → confirm → master updated
- [ ] User without inventory permission → refused calmly both stages
- [ ] `pytest erp/assistant` + (if any new string) i18n parity + tsc + gate03 green

---

## After This Session

```
Smoke test passed?
→ Rename this file: append _done.
→ Clear the session. Open FILE_04_ACCOUNTING_ACTIONS.md and continue.
```
