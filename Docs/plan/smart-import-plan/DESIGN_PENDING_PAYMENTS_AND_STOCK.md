# Design — Pending Payments + Reconciled Inventory Opening

Extends `FILE_16_FINANCE_ADAPTERS.md` Task B (payments/receipts) and the remainder of Task C
(`inventory_opening`, `inventory_transactions`), both left undelivered because the only existing
write-paths post to the GL/StockBalance immediately — violating the repo-wide **drafts-only**
standing decision (`DECISIONS.md` — "Agent actions — drafts-only standing decision reaffirmed").
Confirmed the gap isn't import-specific: `agent-actions-plan` (the AI assistant's draft-action
system — draft orders, POs, counts, transfers, journal entries) has no payment action either, for
the same reason. This design fixes the root gap once, so both imports and (later) agent-actions
can use it.

Two independent sub-projects, specced together, built as two sequential sessions.

## Sub-project 1 — Draftable payments (`PendingPayment`)

**Problem.** `sales.receive_payment` / `purchasing.pay_order` are the only payment write-paths.
Both post to the GL immediately and require the order already `INVOICED`/`BILLED`. Orders created
by this same import engine land `DRAFT`, so at import time there is usually nothing to pay against
yet, and even when there is, posting immediately breaks drafts-only.

**Model** (new, `erp/accounting` — shared home; sales and purchasing both use it):
- `module`: `"sales" | "purchasing"`
- `order_number`: nullable — set once a file's invoice/order reference resolves to a real order;
  blank for an unallocated payment
- `party_type`, `party_code`, `amount_minor`, `date`, `method` (`cash|transfer|cheque`, normalized
  incl. Arabic نقدي/تحويل/شيك)
- `source`: `"import"` today, `"agent"` reserved for a future agent-actions caller
- `status`: `pending | applied | discarded`
- `applied_by`, `applied_at`, `batch_ref`

**Services** (new, additive — `sales.receive_payment` / `purchasing.pay_order` signatures
untouched):
- `create_pending_payment(...)`
- `apply_pending_payment(pending, actor)` — resolves `module` + `order_number` to the real order
  and calls the **existing** `receive_payment`/`pay_order` exactly as the module screen does, so
  every current guard (overpayment, approval limit, order status) applies unchanged. This is the
  human-in-the-loop "post" step; nothing in this design creates a second GL write-path — applying
  a pending payment *is* calling the one sanctioned write-path, just deferred until a human
  confirms it.
- `discard_pending_payment(pending, actor)`
- `match_pending_payment(pending, order_number, actor)` — for the unallocated case, a human
  supplies the order later.

**Import adapter** (`erp/imports/adapters`, two entities: `payments`, `receipts`). Row-level, not
grouped — one row is one payment. Party resolution reuses the existing `_find_customer` (
`adapters/sales.py`) / `_find_supplier` (`adapters/purchasing.py`) helpers already used by the
document adapters — no new lookup logic. Always creates a `PendingPayment`; never calls
`receive_payment`/`pay_order` at import time. Reference resolves → pre-matched row. Reference
absent/unresolved → unmatched + a `warning` issue, per the original plan text ("import unallocated
+ warning (allocation is a human step)").

**API** (new, small): list (filterable by module / matched-state), apply, discard, match. Consumed
by a future review screen — **out of scope for this backend session**, same split already used for
`TH FILE_14/19/20` (B ships backend + tests, file stays open until Agent A ships the UI).

**Tests**: linked payment applies and reproduces today's `receive_payment`/`pay_order` behavior
exactly (including its guards); unmatched payment stays pending with the warning surfaced; apply
against a stale/overpaid order surfaces the existing `OverpaymentError` unchanged; discard is a
clean no-op on the ledger; `match` then `apply` round-trips correctly.

## Sub-project 2 — Reconciled inventory opening (`PendingStockEntry`)

**Problem.** `inventory.services.stock.receive_stock` posts Dr Inventory / Cr GRNI immediately
(GRNI = goods received, bill not yet in — factually wrong for an opening balance) AND would
double-count the Inventory control account, which `account_opening` (already shipped) already
books as one aggregate line from the customer's trial balance.

**Model** (new, additive, `erp/inventory`): `PendingStockEntry` — `item`, `warehouse`, `quantity`,
`unit_cost_minor`, `date`, `type` (`"opening"` only — see historic-movements decision below),
`status` (`pending | applied | discarded`), `batch_ref`.

**New service** (additive — `receive_stock` signature untouched): `apply_pending_stock_opening
(pending, actor)` — posts Dr Inventory / **Cr a new dedicated opening-suspense account**
(`IMPORTS_DEFAULTS['inventory_opening']['suspense_account']`, distinct from GRNI) and updates
`StockBalance` with the same math `receive_stock` uses, minus the GRNI leg.

**Double-count guard.** Extend `account_opening`'s existing `validate_group` (our own adapter code
— allowed to extend, not an existing service write-path) to detect when the same import session
also imports `inventory_opening` rows. If the TB file's lines include the Inventory control
account code in that case, raise a new `inventory_double_booked` issue instead of silently
importing — the human must drop the Inventory line from the TB file (item-level opening becomes
the source of truth for that account) or skip item-level opening. Turns a silent balance-sheet
error into an actionable one, consistent with `account_opening`'s existing correcting-entry
pattern.

**`inventory_transactions` (historic movements) — stays a documented blocker, not built.**
Confirmed by reading `StockBalance`/`StockMovement`: the weighted-average balance is a single
running total recomputed in **call order**, not date order — there is no as-of-date snapshot.
Inserting a backdated movement after later movements already happened would cost it against
today's balance, not the historical one, silently corrupting COGS. Fixing this needs an
event-sourced / date-ordered cost recomputation — a costing-engine rewrite, out of proportion for
this design. Leave exactly as currently documented in `erp/imports/adapters/accounting.py` and
`DECISIONS.md`.

**Tests**: opening entry posts to the suspense account (not GRNI) and updates `StockBalance`
correctly; an `account_opening` import carrying an Inventory line while `inventory_opening` rows
are present in the same session is rejected with the new issue; discard is a clean no-op.

## Out of scope (both sub-projects)

- Any `apps/web` UI (review/apply screens) — Agent A's territory; both files stay open
  (not `_done`) until that UI ships, matching the established B12–B15 precedent.
- `inventory_transactions` (historic movements) — documented architecture blocker, not a TODO.
- Changing any existing service write-path signature (`receive_payment`, `pay_order`,
  `receive_stock`, `account_opening`'s existing balanced-case behavior).
- A generic "apply any draft" surface — each sub-project's `apply_*` function is purpose-built for
  its own module, matching the existing per-module draft pattern (draft order, draft PO, draft
  journal entry) rather than inventing a cross-cutting drafts framework.

## Session split

1. **This design doc** (current session).
2. **Session N — Sub-project 1**: `PendingPayment` model + migration + services + `payments`/
   `receipts` adapters + tests. New DECISIONS.md entry recording the suspense-account choice.
3. **Session N+1 — Sub-project 2**: `PendingStockEntry` model + migration + service +
   `inventory_opening` adapter + `account_opening` double-book guard + tests. DECISIONS.md entry.
4. Both land as continuations of `FILE_16_FINANCE_ADAPTERS.md` (renamed `_done` once both are
   shipped or explicitly descoped) — not new numbered plan files, since they are the deferred
   halves of that same session's Task B/C, not new scope.
