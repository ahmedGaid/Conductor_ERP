# SESSION 03 — Receive a purchase order
# Files: erp/purchasing/contracts/__init__.py, erp/assistant/services/actions.py,
#        erp/assistant/tests/test_actions.py, erp/purchasing/tests/

**Model:** Sonnet — pattern replication over a real, already-tested manual endpoint
(`services.receive_order`, wired to the `receivePO()` button today). Say so at session start and
let the founder `/model` down before starting. Requires FILE_01 done.

---

## Before You Start

1. Read `FILE_00_INDEX.md`'s action-1 table row + the "v1 = full receipt only" scope note.
2. Read `erp/purchasing/services/orders.py` `receive_order(order, received=None, actor=None)` in
   full — status precondition (`CONFIRMED` or `PARTIALLY_RECEIVED`), `ExcessiveReceiptError`,
   partial-receipt `received: {line_no: qty}` map (this session passes `None` → full remaining
   receipt on every line — no natural-language partial-quantity parsing in v1, matching the
   descoping precedent other sessions in this codebase use to keep scope tight).
3. Read `erp/purchasing/contracts/__init__.py` `find_requests` (line ~139) — the exact template to
   mirror for a NEW `find_orders` function this session adds (no purchase-order equivalent exists
   yet; `open_purchase_orders` nearby is a reporting helper — status/supplier filters only, no
   number search, no line detail — not a fit, don't reuse it for this).
4. Read `_build_convert_purchase_request`/`_execute_convert_purchase_request` in `actions.py` — the
   closest existing template (find-by-query, one risk line, single execute call).
5. Read `_can_post`/`challenge` (FILE_01) — every task below uses them, not plain `_can`.

"Do not write anything yet."

---

## Task A — `find_orders` contract helper

In `erp/purchasing/contracts/__init__.py`, next to `find_requests`:

```python
def find_orders(actor, *, query: str, limit: int = 8) -> list[dict]:
    """Find purchase orders by number or supplier — scoped to the actor, most recent first.
    Carries lines + status so posting actions (receive/bill/pay) can build a proposal without a
    second lookup (mirrors find_requests)."""
    q = (query or "").strip()
    qs = _scoped_orders(actor).select_related("supplier")
    if q:
        qs = qs.filter(
            Q(number__icontains=q) | Q(supplier__name__icontains=q) | Q(supplier__code__icontains=q)
        )
    return [
        {"id": str(o.id), "number": o.number, "supplier_code": o.supplier.code,
         "supplier_name": o.supplier.name, "status": o.status,
         "subtotal_minor": o.subtotal_minor, "received_minor": o.received_minor,
         "billed_minor": o.billed_minor, "paid_minor": o.paid_minor,
         "outstanding_minor": o.outstanding_minor,
         "lines": [
             {"line_no": ln.line_no, "item_sku": ln.item_sku, "quantity": str(ln.quantity),
              "received_qty": str(ln.received_qty), "unit_cost_minor": ln.unit_cost_minor}
             for ln in o.lines.all().order_by("line_no")
         ]}
        for o in qs.order_by("-order_date")[: max(1, min(limit, 20))]
    ]
```

Add `"find_orders"` to this module's `__all__` (check whether one exists — `find_requests` should
already be listed there; add alongside it).

## Task B — `receive_purchase_order` action

In `erp/assistant/services/actions.py`:

- `_build_receive_purchase_order(actor, *, query=None, **_) -> dict`:
  - `if not _posting_enabled(): return _refused_posting_disabled()`
  - `if not _can(actor, BRANCH_MANAGER): return _refused()`
  - Resolve `query` via `purchasing.find_orders(actor, query=query)` (add `find_orders` to
    `erp/assistant/services/actions.py`'s `purchasing` import if it imports specific names, or via
    the existing `purchasing` module alias if it imports the whole contracts module — check the
    existing import style at the top of the file and match it).
  - No match / ambiguous (>1 with no exact number match) → `_blocker("purchase order", query,
    candidates=[...])` (same shape `_build_convert_purchase_request` uses for requests).
  - Status not in `("confirmed", "partially_received")` → `{"error": "Order <number> is
    '<status>' — it needs to be confirmed before it can be received."}` (calm, names the real
    precondition, mirrors `edit_sales_order_draft`'s non-draft refusal style).
  - Otherwise: summary lines = each unreceived line (item, remaining qty); records = the order link;
    `"challenge": challenge(<sum of remaining_qty * unit_cost_minor across lines>)`.
- `_execute_receive_purchase_order(actor, payload) -> dict`:
  - `if not _can_post(actor, BRANCH_MANAGER): raise PermissionError`
  - Look the order back up by id from payload, call `purchasing.receive(order, actor=actor)` — full
    receipt (`received=None`). (If `receive` isn't already re-exported from `contracts/__init__.py`
    the way `receive_order` service is, add it there rather than importing `services` directly in
    `actions.py`, matching how every other action reaches purchasing only through `contracts`.)
  - Return `{"summary": f"Received {order.number} in full.", "links": [{"type":
    "purchaseOrder", "value": str(order.id), "label": order.number}]}`.
- Register in `ACTIONS`: `kind="update"`, `risk="post"`, `effects=(Effect("purchase_order",
  "update", stock="moves"),)`, `invariants=("stock_non_negative",)`.

## Task C — tests

- `erp/purchasing/tests/`: `find_orders` — number search, supplier search, line detail shape.
- `erp/assistant/tests/test_actions.py`: proposal on a `confirmed` order shows the right challenge
  amount; on a `draft` order → calm `{error}` naming the precondition, no card; toggle off →
  refused; wrong role → refused; right retype → order becomes `received` (or `partially_received`
  if seeded with mixed remaining quantities — assert the actual resulting status, don't assume
  `received`), one audit row, stock balance increased; double-confirm → 409.

---

## Smoke Test

- [ ] "Receive PO PO-2026-…" on a `confirmed` order (toggle ON, right role, right retype) → card →
      confirm → order now `received`, stock on hand increased, GRNI clears per the existing
      `receive_order` accounting (unchanged — this session adds no new GL logic)
- [ ] Same on a `draft` order → calm refusal naming the precondition, no card
- [ ] Toggle OFF → calm refusal
- [ ] `pytest erp/purchasing erp/assistant` green; no UI strings changed beyond the two new keys
      from FILE_01 (this file adds no new i18n keys of its own) — still run i18n parity + `tsc
      --noEmit` + gate03 to confirm nothing regressed

---

## After This Session

```
Smoke test passed?
→ Rename this file: append _done.
→ Clear the session. Open FILE_04_BILL_PURCHASE_ORDER.md and continue.
```
