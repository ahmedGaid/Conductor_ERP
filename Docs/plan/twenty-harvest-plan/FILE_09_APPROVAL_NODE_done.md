# SESSION 9 — Human-Approval Node (Workflow) — DONE 2026-07-18 (reduced scope, see note)

**Finding:** the engine already had a generic `approval` node (halt on `waiting`, resume on
decision) wired into the canvas palette, API, and tests — what was missing was everything AROUND
it: no `ApprovalRequest` model, no approver-spec RBAC, no notification, no audit call. That's what
this session built.

**Task A — done in full:** new `ApprovalRequest` model (`erp/workflow/models.py`, migration
`0003_approvalrequest`) created the moment a run halts at an approval node (hooked in
`engine.py`'s waiting branch → `erp/workflow/approvals.py:create_approval_request`). Config reads
`approver_user_id`/`approver_role`/`title`/`message` off the node's `config` JSON (blank = anyone
may decide, preserving the pre-existing behavior for graphs that don't set an approver).
`approvals.decide(actor, request_id, decision, comment)` is RBAC-checked (superadmin bypass, named
user, or role membership), records to `erp.audit`, dispatches an in-app notification to the
resolved recipient(s), and resumes the engine. `InstanceDecisionView` now routes through it whenever
a pending `ApprovalRequest` exists (i.e. always, going forward) — old direct-`engine.resume` callers
(pre-existing tests) are unaffected since a superadmin/unscoped request always passes the check.

**Task D — done in full:** `erp/workflow/tests/test_approval_request.py` (10 tests: creation on
wait, unscoped/named-user/role-scoped decide, superadmin bypass, wrong-approver 403, double-decide
conflict, audit entry, notification dispatch, durability across a simulated restart) +
`test_api.py::test_decision_by_wrong_approver_is_403_and_leaves_run_waiting` (DRF-level 403 +
run-untouched + correct-approver-still-works). `pytest erp/workflow` — 47/47 pass. `gate:all`
00–17 green.

**Task B — partial:** added structured `title`/`message`/`approver_role` fields to the canvas
config panel for approval nodes (`apps/web/src/pages/canvas/NodeConfigPanel.tsx`) — the raw JSON
textarea remains for `approver_user_id` (no user-search combobox built here, follow-up). **Did
NOT** build the bespoke node-card/palette-chip visual (pending/approved/rejected state, monochrome
status + glyph) the plan asked for — no canvas node type has ANY custom visual today (confirmed:
`<ReactFlow>` has no `nodeTypes` prop, every node renders as React Flow's default box); building
one bespoke card for just `approval` would be an inconsistent one-off, and building the general
per-type node-card system is a bigger, separate frontend-architecture decision this rollout session
shouldn't make unasked.

**Task C — partial:** the existing decision card (`ExecutionViewerPage.tsx`, pre-existing, not new)
now shows the `ApprovalRequest`'s title/message, takes a comment on decide, and shows
"decided by X — comment" after the fact. This is the functional inbox moment, not the polished
"demo moment — craft it" version the plan describes (no dedicated focused approval-card layout,
no shared review with a design pass). Flagged rather than silently shipped as if fully addressed.

# Files: erp/workflow/ (engine: node type + run state), erp/workflow/tests/, apps/web workflow canvas (node UI), erp/notifications (approval request), i18n locales

Twenty reference: the `FORM` workflow action — a human-input step INSIDE the flow. For us this
is bigger than a feature: it makes human-in-the-loop a visible, sellable workflow primitive
(STRATEGY §3 mechanic 3 as a canvas node).

---

## Before You Start

1. Open `erp/workflow/` engine: how node types are defined, how a run advances, where run state
   persists. The approval node must HALT a run durably (survive restarts) — confirm the run
   model supports a waiting state or add one.
2. Open `erp/notifications/` → how in-app notifications are created + surfaced.
3. Open the canvas (`@xyflow/react` usage in apps/web) → how existing node types register
   (palette, config panel, rendering).

"Do not write anything yet."

---

## Task A — Engine node type `approval`

Config: approver = role or specific user; title/message (i18n-able text fields); timeout days
(optional) with on-timeout branch (escalate = notify again / fail path). Runtime: run enters
`waiting_approval`, an ApprovalRequest row is created (run FK, node id, approver spec, status
pending/approved/rejected, decided_by, comment, decided_at) and a notification goes out.
`decide(actor, request_id, approve|reject, comment)` service fn: RBAC-checked (only the
approver spec), records to audit, resumes the run down the approve/reject branch.

## Task B — Canvas node UI

Palette entry + node card (approver chip, pending state visualized calmly — monochrome, status
word + glyph, never color alone); config side panel; run view shows who approved/rejected, when,
comment. Designed states for pending/approved/rejected/timed-out.

## Task C — The approval INBOX moment

Notification → click → a focused approval card: what's being approved (linked record), approve /
reject + comment. Blame-free copy. This card is the demo moment — craft it.

## Task D — Tests

Halt is durable (reload engine, run still waiting); only the approver can decide; both branches
resume correctly; timeout path; audit rows present.

---

## Smoke Test

- [ ] Workflow: trigger → approval → notify: run halts; approver decides from the card; run
      resumes down the right branch
- [ ] Non-approver decide attempt → human 403; audit shows the decision trail
- [ ] Restart Django mid-wait → run still waiting, decision still works
- [ ] `pytest erp/workflow` green; parity + tsc + gate03 green; brand checklist on the card

---

## After This Session

```
Smoke test passed?
→ Rename with _done. Update erp-status. /compact.
→ Open FILE_10_AI_AGENT_NODE.md in a FRESH session.
```
