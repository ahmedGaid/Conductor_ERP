# SESSION 10 — AI-Agent Node (Workflow)  🤖 permission story required in the commit
# Files: erp/workflow/ (node type + validator), erp/workflow/tests/, apps/web canvas node, i18n locales

Twenty reference: `AI_AGENT` as a workflow action — the agent is a STEP whose output feeds the
next node. This merges our two engines (workflow canvas + assistant actions) into the flagship
machine: "on new PO → agent drafts the journal → human approves". Note Twenty also splits
`DRAFT_EMAIL` from `SEND_EMAIL` at the type level — same doctrine as our drafts-only rule.

---

## Before You Start

1. Open `erp/assistant/` action catalog (agent-actions FILE_01–06 shipped per-module DRAFT
   actions via propose→confirm→execute) → the exact action registry + input schemas. The node
   REUSES these actions; zero new AI capability is built here.
2. Open the reliability gateway entry point (`erp/assistant/` gateway) → all model calls in the
   node go through it (budgets/caching/failover apply automatically).
3. Read FILE_09's approval node (engine + service) — the validator below depends on it.
4. Open `Docs/ARP_STRATEGY.md` §3 — the six mechanics; this node must satisfy all six.

"Do not write anything yet."

---

## Task A — Engine node type `assistant_action`

Config: action id (from the existing catalog), input mapping (workflow context → action inputs),
output key (action result → context for downstream nodes). Runtime: executes the action **as
the run's triggering actor** (RBAC by construction; never a system superuser), through the
gateway, recording the trace id on the run step. Failure → typed error into the run (blame-free
message), fail branch if configured.

## Task B — The drafts-only VALIDATOR (the teeth)

Workflow save-time validation: any `assistant_action` whose action WRITES (creates a draft) must
be followed — on every path to a terminal node — by an `approval` node before any node that
posts/sends/finalizes. Violation = save rejected with a human explanation. Enforce in engine
code + assert in tests. (Posting actions themselves remain out of catalog per agent-actions
FILE_06 deferred decision — the validator future-proofs the day they arrive.)

## Task C — Canvas node UI

Node card shows the action's i18n label + a small "AI" wordmark treatment consistent with the
existing assistant surface (monochrome). Config panel: action picker (permission-filtered),
input mapping fields, output key. Run view: the draft produced, the gateway trace link, tokens
used — click-verifiable numbers (mechanic 4).

## Task D — Permission story (ships IN the commit message / PR description)

Who can trigger: whoever can run the workflow (existing workflow RBAC). What it can touch: only
catalog draft-actions the TRIGGERING ACTOR could do by hand. What audit shows: workflow run id,
node id, gateway trace, draft record, approval decision. AI off (no API key) → node fails soft
with an actionable blocker (mechanic 5), workflow paths without AI unaffected.

## Task E — Tests

Actor scoping (actor without sales role → sales draft action fails); validator rejects
draft-without-approval graphs; output flows to next node; no-API-key soft failure.

---

## Smoke Test

- [ ] Demo flow: PO created → agent drafts journal → approval card shows the draft → approve →
      draft confirmed via existing propose→confirm path
- [ ] Same flow as a low-permission user → agent action fails with a human permission error
- [ ] Saving a graph with draft-action but no downstream approval → rejected with clear message
- [ ] `pytest erp/workflow` green; parity + tsc + gate03 green; permission story in the commit

---

## After This Session

```
Smoke test passed?
→ Rename with _done. Update erp-status. /compact.
→ Open FILE_11_CUSTOM_FIELDS_BACKEND.md in a FRESH session.
```
