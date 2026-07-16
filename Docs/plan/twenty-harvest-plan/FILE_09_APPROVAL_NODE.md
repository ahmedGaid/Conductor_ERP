# SESSION 9 — Human-Approval Node (Workflow)
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
