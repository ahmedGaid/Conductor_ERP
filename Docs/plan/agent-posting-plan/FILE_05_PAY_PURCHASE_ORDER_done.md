# SESSION 05 — Pay a purchase order (cash settlement against a billed order)
# Files: erp/assistant/services/actions.py, erp/assistant/tests/test_actions.py

**Model:** Sonnet — pattern replication over a real, already-tested manual endpoint
(`services.pay_order`, wired to the `payPO()` button + `PaymentDialog.tsx` today). Requires FILE_01
and FILE_03 done (reuses `find_orders`).

---

## Before You Start

1. Read `erp/purchasing/services/orders.py` `pay_order(order, amount_minor, actor=None)`: status
   precondition (`_require(order, POStatus.BILLED)` — **not** `RECEIVED`, this only works after
   FILE_04's bill step), `OverpaymentError` (`amount_minor <= 0` or `> order.outstanding_minor`),
   `ApprovalLimitExceededError` via `access.within_limit(actor, "payment", amount_minor)`.
2. Read `apps/web/src/components/PaymentDialog.tsx` — the manual UI defaults the amount to the full
   outstanding balance but lets the human edit it down (partial payment). This action mirrors that:
   `amount` argument optional, defaults to `order.outstanding_minor`.
3. Read this plan's FILE_03/04 (`_done`) — `find_orders`, the guard/challenge pattern to mirror.

"Do not write anything yet."

---

## Task A — `pay_purchase_order` action

In `erp/assistant/services/actions.py`:

- `_build_pay_purchase_order(actor, *, query=None, amount=None, **_) -> dict`:
  - `if not _posting_enabled(): return _refused_posting_disabled()`; `if not _can(actor,
    BRANCH_MANAGER): return _refused()` (same two-step check as every build function in this plan).
  - Resolve via `purchasing.find_orders(actor, query=query)`.
  - Status != `"billed"` → calm `{"error": "Order <number> is '<status>' — it needs to be billed
    first before it can be paid."}` (points the user at FILE_04's action / the manual Bill button).
  - `amount_minor = _minor(amount) if amount else order["outstanding_minor"]` (reuse the existing
    `_minor` helper already in this file, same as `_build_journal_entry` uses for line amounts).
  - `amount_minor <= 0 or amount_minor > order["outstanding_minor"]` → calm `{"error": "That amount
    doesn't work — <label> is outstanding on <number>."}` (proposal-time precondition check,
    mirrors FILE_04's partial-receipt-blocks-billing precedent — never hand back a card that would
    422 on confirm).
  - Otherwise: summary shows outstanding vs. the amount about to be paid; `"challenge":
    challenge(amount_minor)`.
- `_execute_pay_purchase_order(actor, payload) -> dict`:
  - `if not _can_post(actor, BRANCH_MANAGER): raise PermissionError`.
  - Look the order back up, call `purchasing.pay(order, payload["amount_minor"],
    actor=actor)` — if `pay_order` isn't already re-exported from
    `erp/purchasing/contracts/__init__.py`, add the one-line wrapper (same shape as `receive()`),
    keeping every action's cross-module reach through `contracts`, never `services` directly.
  - Return a summary line (amount paid, resulting status — `"billed"` still if partial,
    `"paid"` if this cleared the balance) + the order link.
- Register in `ACTIONS`: `kind="post"`, `risk="post"`, `effects=(Effect("purchase_order", "update",
  gl="posts"),)`, `invariants=("period_open",)` (same reasoning as FILE_04 — `pay_order` posts via
  `post_journal` internally, which already enforces this; the invariant here feeds the
  post-execute verifier-pack cross-check).
- `ACTION_ARG_FIELDS`: add `"amount"` if not already present (check first — `edit_sales_order_draft`
  packs per-line prices inside `items` rather than a bare `amount` field; this action's `amount` is
  a single top-level number, closer to `set_reorder_point`'s bare-number arg shape — follow that
  precedent, not the line-packing one).

## Task B — tests

- `erp/assistant/tests/test_actions.py`: proposal on a `billed` order with no `amount` given shows
  the full outstanding as the challenge; with a partial `amount` shows that amount; amount over
  outstanding → calm `{error}`, no card; order not yet billed → calm `{error}` naming the
  precondition; toggle off/wrong role → refused; right retype → `paid_minor` increases, status
  flips to `"paid"` only once `paid_minor >= billed_minor`, one `post_journal` entry (AP debit /
  Cash credit) exists, one audit row; double-confirm → 409.

---

## Smoke Test

- [ ] "Pay PO PO-2026-…" on a billed order, no amount specified → card shows full outstanding as
      the challenge → confirm → order `paid`, GL entry exists, card shows link
- [ ] Same with a partial amount → order stays `billed` (not yet fully paid), outstanding reduced
      by exactly that amount
- [ ] Amount larger than outstanding → calm refusal, no card
- [ ] Order still only `received` (not billed) → calm refusal naming the precondition
- [ ] Toggle OFF → calm refusal
- [ ] `pytest erp/purchasing erp/accounting erp/assistant` green; i18n parity + `tsc --noEmit` +
      gate03 green

---

## After This Session

```
Smoke test passed?
→ Rename this file: append _done.
→ Clear the session. Open FILE_06_APPROVE_PURCHASE_REQUEST.md and continue.
```
