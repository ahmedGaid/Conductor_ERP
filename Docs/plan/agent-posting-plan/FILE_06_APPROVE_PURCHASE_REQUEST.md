# SESSION 06 — Approve a purchase request
# Files: erp/assistant/services/actions.py, erp/assistant/tests/test_actions.py

**Model:** Sonnet — pattern replication over a real, already-tested manual endpoint
(`services.approve_request`, wired to the `approveRequest()` button today). Requires FILE_01 done
(does NOT need FILE_03's `find_orders` — purchase requests already have `find_requests`, used by
the existing `convert_purchase_request` draft action).

---

## Before You Start

1. Read `erp/purchasing/services/requests.py` `approve_request(req, actor=None)`: precondition
   `_require(req, PRStatus.SUBMITTED)` (a request under the org's auto-approval threshold never
   reaches `submitted` — it goes straight to `approved` at submit time; this action is only
   reachable for above-threshold requests actually sitting in `submitted`), `ApprovalLimitExceededError`
   via `access.can_approve(actor, "purchase_request", req.subtotal_minor)`.
2. Read `_build_convert_purchase_request`/`_execute_convert_purchase_request` in `actions.py` — the
   existing action that already uses `purchasing.find_requests`; this session's action is a sibling,
   one status step earlier in the same request's lifecycle.
3. Read `_can_post`/`challenge` (FILE_01).

"Do not write anything yet."

---

## Task A — `approve_purchase_request` action

In `erp/assistant/services/actions.py`, next to `_build_convert_purchase_request`:

- `_build_approve_purchase_request(actor, *, query=None, **_) -> dict`:
  - `if not _posting_enabled(): return _refused_posting_disabled()`; `if not _can(actor,
    BRANCH_MANAGER): return _refused()` (same two-step check as every build function in this plan).
  - Resolve via `purchasing.find_requests(actor, query=query)` (already exists, no new helper).
  - Status != `"submitted"` → calm `{"error": "Request <number> is '<status>' — only a submitted
    request awaiting approval can be approved."}` (mirrors `convert_purchase_request`'s existing
    "not approved yet" refusal style one step earlier in the same lifecycle).
  - Otherwise: summary shows the request's lines + supplier + subtotal; no money is posted by this
    action itself (approving unlocks the request for `convert_purchase_request` later — it doesn't
    touch the GL or stock), but it's still consequential (authorizes spend) — per the design spec,
    `"challenge": challenge(request["subtotal_minor"])` uses the request's subtotal as the retype
    value even though nothing posts here.
- `_execute_approve_purchase_request(actor, payload) -> dict`:
  - `if not _can_post(actor, BRANCH_MANAGER): raise PermissionError`.
  - Look the request back up by id, call `purchasing.approve(request, actor=actor)` — if
    `approve_request` isn't already re-exported from `erp/purchasing/contracts/__init__.py`, add a
    one-line wrapper there (same shape as `receive()`), keeping this action's reach through
    `contracts`, not `services`.
  - Return summary + the request's link.
- Register in `ACTIONS`: `kind="approve"` (already in `DESTRUCTIVE_KINDS`, so `requires_confirm`
  is asserted at import — already true by default, nothing to change there), `risk="post"`,
  `effects=(Effect("purchase_request", "update"),)` — **no `gl`/`stock` value** (neither posts nor
  moves anything itself), so `_validate_action` does NOT require an `invariants` tuple here (only
  effects with `gl="posts"`/`stock="moves"` trigger that rule) — leave `invariants=()`.

## Task B — tests

- `erp/assistant/tests/test_actions.py`: proposal on a `submitted` request shows the right
  challenge (the subtotal); on a `draft` or `approved` request → calm `{error}` naming the actual
  status, no card; toggle off/wrong role → refused; right retype → request `approved`,
  `approved_at`/`approved_by` set, one audit row; an actor over the request's approval limit → the
  underlying `ApprovalLimitExceededError` surfaces unchanged through `ActionExecuteView`'s existing
  `AppError` passthrough (confirm this action needs no extra handling, same as FILE_04's bill
  action); double-confirm → 409.

---

## Smoke Test

- [ ] "Approve request PR-2026-…" on a `submitted` request (above the auto-approval threshold) →
      card with subtotal challenge → confirm → request `approved`, card shows link
- [ ] Same on a `draft` or already-`approved` request → calm refusal naming the actual status
- [ ] Toggle OFF → calm refusal
- [ ] The existing `convert_purchase_request` draft action still works unchanged on the now-approved
      request (regression check — this session shares `find_requests` with it, touches no other
      code path it depends on)
- [ ] `pytest erp/purchasing erp/assistant` green; i18n parity + `tsc --noEmit` + gate03 green

---

## After This Session

```
Smoke test passed?
→ Rename this file: append _done.
→ Clear the session. Open FILE_07_ISSUE_STOCK_ENTRY.md and continue.
```
