# SESSION 04 — Bill a purchase order (3-way match, invoice/GRNI clearing)
# Files: erp/assistant/services/actions.py, erp/assistant/tests/test_actions.py

**Model:** Sonnet — pattern replication over a real, already-tested manual endpoint
(`services.bill_order`, wired to the `billPO()` button today). Requires FILE_01 and FILE_03 done
(reuses `find_orders` from FILE_03 — no new contract helper needed here).

---

## Before You Start

1. Read `FILE_00_INDEX.md`'s "scope note" on why bill + pay are both in this plan.
2. Read `erp/purchasing/services/orders.py` `bill_order(order, actor=None)` in full: status
   precondition (`RECEIVED` or `PARTIALLY_RECEIVED`), the 3-way match (`ThreeWayMatchError` if any
   line's `received_qty != quantity` — **a partially-received order will refuse to bill**, that's
   correct existing behavior, not a bug to work around), the VAT calc (`compute_tax(net,
   order.tax_code)` from `erp.accounting.contracts`, reused as-is — don't reimplement tax logic),
   `ApprovalLimitExceededError` on the resulting gross via `access.within_limit(actor, "invoice",
   gross)`.
3. Read this plan's FILE_03 (now `_done`) — `find_orders`, the `_build_receive_purchase_order`
   pattern this session mirrors almost line for line.

"Do not write anything yet."

---

## Task A — `bill_purchase_order` action

In `erp/assistant/services/actions.py`, right next to `_build_receive_purchase_order`:

- `_build_bill_purchase_order(actor, *, query=None, **_) -> dict`:
  - `if not _posting_enabled(): return _refused_posting_disabled()`; `if not _can(actor,
    BRANCH_MANAGER): return _refused()` (same two-step check as every build function in this plan).
  - Resolve via `purchasing.find_orders(actor, query=query)`.
  - Status not in `("received", "partially_received")` → calm `{"error": ...}` naming the real
    precondition.
  - Any line `received_qty != quantity` (partially received) → calm `{"error": "Order <number> is
    only partially received (line <n>: <received> of <ordered>) — it can't be billed until every
    line is fully received."}` — this is the 3-way match check surfaced BEFORE confirm, at proposal
    time, so the user never sees a card that would fail (mirrors `edit_sales_order_draft`'s
    proposal-time precondition check).
  - Otherwise: `net = order.received_minor`; `vat = compute_tax(net, order.tax_code) if
    order.tax_code else 0` (import `compute_tax` from `erp.accounting.contracts`, same import style
    as any other cross-module contract call already in this file); `gross = net + vat`. Summary
    shows net/VAT/gross; `"challenge": challenge(gross)`.
- `_execute_bill_purchase_order(actor, payload) -> dict`:
  - `if not _can_post(actor, BRANCH_MANAGER): raise PermissionError`.
  - Look the order back up, call `purchasing.bill(order, actor=actor)` — if `bill_order` isn't
    already re-exported from `erp/purchasing/contracts/__init__.py`, add a one-line wrapper there
    (mirror the existing `receive()`/`issue()` wrapper shape in that file), don't reach into
    `services` directly.
  - Return summary + a link to the order (bill number is on `order.bill_number` after the call).
- Register in `ACTIONS`: `kind="post"`, `risk="post"`, `effects=(Effect("purchase_order", "update",
  gl="posts"),)`, `invariants=("period_open",)` (billing posts a journal via `post_journal`, which
  already enforces its own period-open check internally — declaring the invariant here is for the
  verifier-pack cross-check `ActionExecuteView` runs post-execute, not a duplicate guard).

## Task B — tests

- `erp/assistant/tests/test_actions.py`: proposal on a fully-received order shows net/VAT/gross
  correctly (seed an order with a real `tax_code` to prove VAT isn't silently dropped); on a
  partially-received order → calm `{error}` naming the specific short line, no card; toggle
  off/wrong role → refused; right retype → order `billed`, `bill_number` set, one `post_journal`
  entry exists with the expected GRNI/VAT-input/AP lines; an actor over the `invoice` approval
  limit → the underlying `ApprovalLimitExceededError` surfaces as the existing calm `AppError`
  path (`ActionExecuteView` already re-raises `AppError` verbatim — confirm this action doesn't
  need its own translation of that error, just let it flow through unchanged).

---

## Smoke Test

- [ ] "Bill PO PO-2026-…" on a fully-received order → card with net/VAT/gross → confirm → order
      `billed`, GL entry exists (check via the accounting journals list), card shows link
- [ ] Same on a partially-received order → calm refusal naming the short line, no card
- [ ] Toggle OFF → calm refusal
- [ ] `pytest erp/purchasing erp/accounting erp/assistant` green; i18n parity + `tsc --noEmit` +
      gate03 green (no new UI strings expected — confirm)

---

## After This Session

```
Smoke test passed?
→ Rename this file: append _done.
→ Clear the session. Open FILE_05_PAY_PURCHASE_ORDER.md and continue.
```
