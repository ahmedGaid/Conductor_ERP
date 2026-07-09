# Agent Actions Plan — widen the assistant's write surface to the Linear-agent bar

**Goal (founder, 2026-07-09):** make the Conductor assistant *act* like Linear's agent — a
teammate that gets work done, not just a Q&A box. Gap analysis showed the multi-step loop, the
propose→confirm→execute machinery, ambient page-context, detours/resume, and the deeper
orchestration (typed plans, durable runs, validation, self-verify) are **already built or already
queued** (ai-workspace FILE_09–14 `_done`; ai-reliability **FILE_05** for the engine). The ONE
genuine, unplanned gap is **breadth**: the assistant can only *do* three things today
(sales-order draft, purchase-request draft, create-customer). This plan closes that gap, module by
module, reusing the existing `Action` pattern.

This is a **breadth track**, not new machinery. Every file here adds actions to the registry that
already exists (`erp/assistant/services/actions.py`) and cards to the UI that already exists
(`ActionCard.tsx`). No new execution path, no new confirm flow, no new dependency.

## The one hard rule this plan inherits (do not break it)

**Drafts only. Nothing the assistant creates is posted, approved, received, or paid.** Every
action here produces a DRAFT record (unposted journal, draft order, draft count) that a human
finishes on the normal module screen. This is the standing decision from ai-workspace FILE_10 and
EXECUTION_ORDER §Standing decisions. Any action whose execute() would post/receive/pay/approve is
**out of scope for v1** and lives in the deferred-decision list in FILE_06 — do not sneak one in.

Corollaries (already enforced by the code — keep them true):
- `requires_confirm=True` on every action. Destructive `kind` (`delete`/`reverse`/`cancel`/…)
  **must** require confirm — `actions.py` asserts this at import; a new action that violates it
  fails the test suite by construction. Good. Leave that assert alone.
- `build_proposal` and `execute` both run **as the actor** (`request.user`). A user who lacks the
  module permission gets the calm refusal at proposal time — never a card they can't spend.
- Every executed action writes `audit.record(module="assistant", action=<name>, ...)`.
- Money is integer minor units end to end; format only at the edge.

## The Linear-agent bar (the acceptance target — see FILE_06)

After this plan, "can the agent do the everyday write jobs of each module, safely?" must be YES
for: quote a customer, turn a quote into an order, adjust an order draft, raise a PO (direct or
from a request), onboard a supplier, move stock between warehouses, open a stock count, draft a
journal, open a ledger account, log a CRM opportunity and advance its stage. Each: propose card
with real numbers/links → confirm → draft + audit + document link → dismiss inert → double-confirm
409s → unpermitted actor refused calmly. FILE_06 turns this into a checklist and wires the actions
into the FILE_05 agent-benchmark suite so "the agent works" stays a tracked percentage.

## Files (each = ONE session; strict order)

| File | Session | Model | Actions added |
|---|---|---|---|
| FILE_01 | Sales actions | **Sonnet** | `create_quotation_draft`, `convert_quotation` (→ SO draft), `edit_sales_order_draft` |
| FILE_02 | Purchasing actions | **Sonnet** | `create_purchase_order_draft`, `convert_purchase_request` (→ PO draft), `create_supplier` |
| FILE_03 | Inventory actions | **Sonnet** | `create_stock_transfer_draft`, `create_stock_count_draft`, `set_reorder_point` |
| FILE_04 | Accounting actions | **Opus** (judgment: GL correctness) | `create_journal_entry_draft`, `create_account` |
| FILE_05 | CRM actions | **Sonnet** | `create_opportunity`, `advance_opportunity_stage`, `log_activity` |
| FILE_06 | Acceptance + bench wiring + deferred decision | **Opus** | none — sign-off |

FILE_01–03 and 05 are pattern-replication of FILE_10 — say so at session start and let the
founder `/model` down to Sonnet before burning Opus. FILE_04 (journals must balance) and FILE_06
(judgment + the posting decision) stay on Opus.

## Before you start ANY file in this plan

1. Read `erp/assistant/services/actions.py` end to end — the `Action` dataclass, the three
   existing actions, `build`, `execute`, the `DESTRUCTIVE_KINDS` assert, `ACTION_ARG_FIELDS`.
2. Read one existing action pair fully (e.g. `_build_sales_order` / `_execute_sales_order`) — that
   is the exact template every new action copies.
3. Read the target module's `contracts.py` — the draft-creating function your `execute` will call
   (exact name, required args, the validation errors it raises). Never invent a contract.
4. Read `apps/web/src/assistant/ActionCard.tsx` — new actions render through it unchanged; only add
   i18n keys if a card needs a new label.

## Per-session protocol (same as EXECUTION_ORDER)

Do the tasks → run the smoke test → gates (`pytest erp/assistant`, and for any UI string
`node scripts/check-i18n-parity.mjs` + `npx tsc --noEmit` + `python scripts/gates/gate03.py`) →
commit (reference the file) → rename `_done` → update `erp-status` → tell the founder to start a
fresh session for the next file. One file = one session.

## Coordination with ai-reliability FILE_05

FILE_05 adds a tool-argument **validation layer** (`toolguard.py`) that will also cover actions.
This plan does NOT wait for it — actions ship with their own `build_proposal` validation as the
existing three do. If FILE_05 lands first, new actions inherit toolguard for free; if this plan
lands first, FILE_05's audit step picks the new actions up. Either order is fine; note which in the
commit. No file overlap except `actions.py` (earlier-queued session wins; the later rebases).
