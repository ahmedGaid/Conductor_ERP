# SESSION 07 — Issue stock (consumption, posts COGS)
# Files: erp/assistant/services/actions.py, erp/assistant/tests/test_actions.py

**Model:** Sonnet — pattern replication over a real, already-tested manual endpoint
(`services.issue_stock`, wired to `issueStock()` in `api/inventory.ts` today). Requires FILE_01
done. Does not depend on FILE_02–06.

---

## Before You Start

1. Read `erp/inventory/services/stock.py` `issue_stock(*, item, warehouse, quantity, ...)`:
   `InsufficientStockError` if `quantity > on-hand`, the weighted-average `costing.issue_value(...)`
   call, `_post_gl` (Dr COGS / Cr Inventory) — the GL value is only known once `issue_stock` actually
   runs (it locks the balance row); this session's `build_proposal` can only ESTIMATE it beforehand.
2. Read `_build_stock_transfer` in `actions.py` in full (lines ~758+) — the item/warehouse
   resolution template (`_resolve_item`, `_resolve_warehouse`, `_qty`) this session reuses
   unchanged, plus its on-hand risk-line pattern via `inventory.stock_on_hand(query=sku,
   warehouse=code)`.
3. Read `inventory.stock_on_hand`'s return shape (`rows[].quantity`, `rows[].value_minor`) — the
   only inputs available for the proposal-time value estimate: `est_value_minor = round(row.value_minor
   * qty / row.quantity)` (current weighted-average unit cost × requested quantity). Note in the
   proposal/challenge copy that this is an estimate — the confirmed result card shows the actual
   posted value from `execute()`, which is authoritative.

"Do not write anything yet."

---

## Task A — `issue_stock_entry` action

In `erp/assistant/services/actions.py`, next to `_build_stock_transfer`:

- `_build_issue_stock_entry(actor, *, item=None, quantity=None, warehouse=None, **_) -> dict`:
  - `if not _posting_enabled(): return _refused_posting_disabled()`; `if not _can(actor,
    BRANCH_MANAGER): return _refused()` (same two-step check as every build function in this plan).
  - Resolve `item` via `_resolve_item` (blocker with near-match candidates on miss, same as
    `_build_stock_transfer`), `warehouse` via `_resolve_warehouse`, `quantity` via `_qty`
    (`{"error": "What quantity should be issued?"}` if `None`).
  - Look up the on-hand row for `(sku, warehouse_code)` via `inventory.stock_on_hand(query=sku,
    warehouse=warehouse_code)["rows"]`; `qty > on_hand` → calm `{"error": "Only <on_hand> of
    '<name>' on hand at <warehouse> — can't issue <qty>."}` (never a card that would 422 on confirm
    — same proposal-time precondition style as every other file in this plan).
  - Otherwise: `est_value_minor = round(row["value_minor"] * qty / row["quantity"])` if `on_hand >
    0` else `0`; summary shows item/qty/warehouse + "estimated value" line; `"challenge":
    challenge(est_value_minor)`.
- `_execute_issue_stock_entry(actor, payload) -> dict`:
  - `if not _can_post(actor, BRANCH_MANAGER): raise PermissionError`.
  - Resolve item/warehouse again from the payload (same as `_execute_stock_transfer` re-resolves
    rather than trusting the proposal's snapshot — follow that precedent, don't cache resolved
    objects across the confirm boundary).
  - Call `inventory.issue(sku, warehouse_code, quantity, actor=actor)` (the existing
    `contracts/__init__.py` wrapper — already re-exported, no new contract code needed here, unlike
    FILE_03's `find_orders`).
  - Return a summary line (item, quantity, warehouse, the ACTUAL posted value from the returned
    `StockMovement`) + a link (`{"type": "item", "value": sku, "label": name}`, same shape
    `_execute_stock_transfer` already returns).
- Register in `ACTIONS`: `kind="adjust"`, `risk="post"`, `effects=(Effect("stock_movement",
  "create", stock="moves", gl="posts"),)`, `invariants=("stock_non_negative", "period_open")`.

## Task B — tests

- `erp/assistant/tests/test_actions.py`: proposal shows a sane estimated value (seed a known
  on-hand quantity/value so the estimate is checkable exactly); quantity exceeding on-hand → calm
  `{error}`, no card; toggle off/wrong role → refused; right retype → stock balance decreases by
  exactly `quantity`, one `StockMovement` (`type=ISSUE`) exists, one GL entry (COGS debit /
  Inventory credit) exists matching the ACTUAL posted value (which may differ slightly from the
  proposal's estimate if another movement landed in between — assert against the real posted
  value, not the estimate); double-confirm → 409.

---

## Smoke Test

- [ ] "Issue 5 of <item> from <warehouse>" (toggle ON, right role) → card with estimated value →
      confirm → stock on hand reduced by 5, COGS/Inventory GL entry exists, card shows the actual
      posted value + item link
- [ ] Quantity greater than on-hand → calm refusal, no card
- [ ] Toggle OFF → calm refusal
- [ ] `pytest erp/inventory erp/accounting erp/assistant` green; i18n parity + `tsc --noEmit` +
      gate03 green

---

## After This Session

```
Smoke test passed?
→ Rename this file: append _done.
→ Clear the session. Open FILE_08_ACCEPTANCE.md and continue.
```
