# SESSION 08 — Acceptance, benchmark wiring, close the plan
# Files: none new — verification only + DECISIONS.md closure entry

**Model:** Opus (judgment + closing a founder decision, same as agent-actions FILE_06).

---

## Before You Start

1. Read `FILE_00_INDEX.md` and every `_done` file 01–07.
2. Read `agent-actions-plan/FILE_06_ACCEPTANCE_done.md` — this session's checklist shape is that
   file's, extended with two new items (below). Same spirit: "do not write anything yet," drive the
   real dev server, test Arabic first then English.
3. Start the dev backend + `apps/web`; log in as (a) System Admin, (b) BRANCH_MANAGER/ACCOUNTANT,
   (c) a role with none of those. Open the `conductor-brand` brand-feel checklist and `DECISIONS.md`.

"Do not write anything yet."

---

## The Linear-agent bar — full acceptance checklist (agent-actions FILE_06 shape + 2 new items)

For EVERY action shipped in FILE_02–07, all eight must hold (test in ar and en):

- [ ] **Org toggle OFF** — proposal AND confirm both refuse calmly, naming Settings → Organization;
      no card ever appears (**new for this plan**)
- [ ] **Org toggle ON, retype mismatch** — confirm returns 400, the card stays pending and reusable,
      no write happened (**new for this plan**)
- [ ] **Propose** — card shows real numbers (minor-unit totals via the `challenge` label), real
      record links, risk/precondition lines in blame-free language
- [ ] **Confirm (right retype + right role)** — creates/mutates the real record + one
      `audit.record(module="assistant")` row + result card links to the affected document
- [ ] **Dismiss** — nothing written; card settles, reload-safe
- [ ] **Double-confirm** — a second confirm 409s (single-use)
- [ ] **Permission** — an actor without the module role is refused calmly at BOTH proposal and
      execute; never a card they can't spend
- [ ] **No status invented** — every proposal-time precondition refusal (wrong PO/PR/journal
      status) names the ACTUAL status and the real next step, never a generic error

Coverage roll-call:

- [ ] Accounting: post a drafted journal entry (+ the new manual "Post" button works identically)
- [ ] Purchasing: receive a PO, bill a PO (3-way match refusal path), pay a PO (full + partial),
      approve a purchase request
- [ ] Inventory: issue stock (estimate-vs-actual value both checked)

## Regression

- [ ] The 17 drafts-only actions from `agent-actions-plan` still pass their original smoke steps
      unchanged (spot-check 3: `create_sales_order_draft`, `create_journal_entry_draft`,
      `advance_opportunity_stage`) — this plan added guard code shared by ALL actions
      (`_can_post`), so a regression here is the single highest-risk failure mode to check first
- [ ] `catalog_text()` still lists every action (23 total now) without exceeding the planner
      prompt's practical size — spot-check the actual generated text length against FILE_06's
      original note on this
- [ ] `pytest erp/assistant` (full) + `pytest erp/accounting erp/purchasing erp/inventory
      erp/identity` (full) + i18n parity + `tsc --noEmit` + gate03 — all green
- [ ] Dark mode: the new retype-confirm input + the new `settings.org.assistantPosting` checkbox
      + the new "Post" button on `JournalDetailPage.tsx` all render on tokens, no hardcoded colour

## Benchmark wiring (coordinate with ai-reliability FILE_05, same rule as agent-actions FILE_06)

If ai-reliability FILE_05 T5.6 (agent benchmark suite) is `_done` by the time this session runs
(check `erp-status` — as of this plan's design session it is NOT), add ≥ 1 task per new action to
`evals/datasets/agent_bench_v1.jsonl`, including at least one deliberately-wrong-retype case per
the unsafe-write predicate (a write that happens without a correct confirm = suite failure). If
FILE_05 is still not done, leave a one-line note in this file (not built yet) pointing future
FILE_05 work here, same as the original plan did.

## Brand-feel checklist (judgment, not mechanical)

Run the `conductor-brand` checklist on: the retype-confirm input itself (does it read as
deliberate friction, not a bug), a 3-way-match refusal card, an org-toggle-off refusal, and a
settled/dismissed post-action card. Bar: "would Linear ship a 'retype to confirm' pattern for
money — and does this one feel like theirs, not a bank's dark pattern?"

## Close the reopened decision

Update the `DECISIONS.md` addendum written at design time ("Option B reopened, scoped down,
2026-07-19/20") with the outcome: which of the 6 actions shipped as designed, any that changed
shape during implementation (e.g. if FILE_02's `find_journal` status-filter finding required a
contract change beyond what FILE_02 predicted), and the final benchmark-wiring status. This is a
factual close-out, not a new decision — nothing here should re-litigate Option A vs B.

---

## After This Session

```
All checklists passed + DECISIONS.md closure entry written?
→ Rename this file: append _done. The agent-posting-plan is closed.
→ Merge the feature branch → main (full gate:all first).
→ Update erp-status + EXECUTION_ORDER.md (mark position PA done, mirroring how ★ was marked).
→ Start a FRESH session for the next queue position.
```
