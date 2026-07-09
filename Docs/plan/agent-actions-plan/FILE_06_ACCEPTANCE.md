# SESSION 06 — Acceptance, benchmark wiring, the posting-actions decision
# Files: none new — fixes only + evals wiring; the deferred-decision record

**Model:** Opus (judgment + a founder decision to frame).

---

## Before You Start

1. Read `FILE_00_INDEX.md` and every `_done` file 01–05.
2. Start the dev backend + `apps/web`; log in as (a) admin and (b) a limited-role user. Test
   **Arabic first**, then English.
3. Open the `conductor-brand` brand-feel checklist and `DECISIONS.md`.

"Do not write anything yet."

---

## The Linear-agent bar — full acceptance checklist

For EVERY action shipped in 01–05, all six must hold (test in ar and en):
- [ ] **Propose** — card shows real numbers (minor-unit totals), real record links, risk lines with
      an icon + word (colour only paired with a word, per brand)
- [ ] **Confirm** — creates the DRAFT record + one `audit.record(module="assistant")` row + result
      card links to the created/updated document
- [ ] **Dismiss** — nothing written; card settles (reduced opacity + status word), reload-safe
- [ ] **Double-confirm** — a second confirm 409s (single-use)
- [ ] **Permission** — an actor without the module permission is refused calmly at BOTH proposal and
      execute; never a card they can't spend
- [ ] **Drafts only** — assert (in tests AND by manual check) that NO action posted / received /
      paid / approved / reversed anything. Any posted state = a failed acceptance.

Coverage roll-call (the everyday write jobs of each module now doable by the agent):
- [ ] Sales: quote, quote→order, edit order draft, create SO draft (pre-existing), create customer
      (pre-existing)
- [ ] Purchasing: PO draft, request→PO, create supplier, purchase-request draft (pre-existing)
- [ ] Inventory: transfer draft, count draft, set reorder point
- [ ] Accounting: journal-entry draft (balanced-only), create account
- [ ] CRM: create opportunity, advance stage, log activity

## Regression

- [ ] The three original actions still pass their FILE_10 smoke steps unchanged
- [ ] `catalog_text()` lists all actions grouped sensibly; the planner prompt isn't bloated past its
      budget (spot-check token size — if the catalog is now large, group/trim descriptions, don't
      drop actions)
- [ ] `pytest erp/assistant` (full), i18n parity, tsc, gate03 — all green
- [ ] Dark mode: every new card renders on tokens, no hardcoded colour

## Benchmark wiring (coordinate with ai-reliability FILE_05)

If ai-reliability **FILE_05 T5.6** (agent benchmark suite) is `_done`, add ≥ 2 tasks per module to
`evals/datasets/agent_bench_v1.jsonl` exercising the new actions, with the unsafe-write predicate
(any executed write without a confirmed card = suite failure). If FILE_05 is NOT yet done, leave a
one-line note in that file's T5.6 pointing here so the bench author covers these actions. Do not
build the bench harness in this plan — just feed it.

## Brand-feel checklist (judgment, not mechanical)

Run the `conductor-brand` checklist on: a priced sales card, an unbalanced-journal refusal, a
duplicate-supplier risk card, and a settled/dismissed card. Bar: "would Linear ship this?" —
monochrome chrome, calm blame-free copy, colour only inside content with a word, no chatbot
theatrics.

## DEFERRED DECISION (record in DECISIONS.md, ask the founder) — posting actions

Everything above is **draft-creating**, honouring the standing "drafts only" rule. The natural next
step to fully match a Linear agent's reach is **posting actions**: receive a PO, pay/invoice an
order, post a journal, adjust/issue stock, approve a request. These MUTATE the books/ledger, not
just drafts. They are deliberately out of this plan.

Frame the choice for the founder (do NOT decide it here):
- **Option A — stay drafts-only forever.** Safest; the human always finishes the post on the module
  screen. Simplest audit story. (Current standing decision.)
- **Option B — allow posting actions, still confirm-gated, with extra guards.** Each posting action
  requires confirm (already enforced for destructive kinds), plus: irreversible/period-affecting
  posts get a stronger card (a typed confirmation, e.g. re-enter the amount), and posting is gated
  behind an explicit setting + permission. Needs the FILE_05 self-verification pass live first so
  numbers are cross-checked before a post card is even shown.

Write the founder's answer into `DECISIONS.md`. If Option B, it becomes a NEW plan (agent-posting),
inserted into EXECUTION_ORDER after ai-reliability FILE_05 — not started from this file.

---

## After This Session

```
All checklists passed + decision recorded?
→ Rename this file: append _done. The agent-actions plan is closed.
→ Merge the feature branch → main.
→ Update erp-status. Start a FRESH session for the next queue position.
```
