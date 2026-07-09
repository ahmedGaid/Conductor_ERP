# SESSION 10 — Safe Actions: Propose → Confirm → Execute → Report
# Files: erp/assistant/services/actions.py (new), erp/assistant/api/views.py, erp/assistant/api/urls.py, apps/web/src/assistant/ActionCard.tsx (new), apps/web/src/assistant/MessageList.tsx, apps/web/src/api/assistant.ts, apps/web/src/i18n/locales/*.json, erp/assistant/tests/test_actions.py (new)

---

## Before You Start

1. Re-read the header docstring of `erp/assistant/tools.py` — "Writes stay human-in-the-loop
   through the normal module endpoints (part 1's invoice→draft flow is the template)". This
   session builds exactly that template, generalized.
2. Open the extraction confirm flow end-to-end (find the frontend page that consumes
   `extractDocument` and posts the confirmed draft to purchasing) — UX + API pattern to copy.
3. Open `erp/sales/contracts.py` / `erp/purchasing/contracts.py` → the create-draft functions
   actions will call (find exact names; note required args and validation errors).
4. Open `erp/audit/services.py` → `record(...)` — every executed action writes one entry with
   `module="assistant"`.

"Do not write anything yet."

---

## Task A — Action registry (proposals, not writes)

Create `erp/assistant/services/actions.py`:

```python
"""Write actions the assistant may PROPOSE. Nothing here executes from model output alone.

Flow: agent loop emits a proposal → user sees a card (summary, records, risks) → explicit confirm
→ execute() runs the module contract as the actor → audit.record → result card with links.
The model shapes the payload; only a human click spends it. Drafts only — nothing the assistant
creates is posted/approved; posting stays on the normal module screens.
"""

@dataclass(frozen=True)
class Action:
    name: str
    description: str          # for the loop prompt
    args: dict                # arg -> description
    build_proposal: Callable  # (actor, **args) -> {summary, records, risks, payload}
    execute: Callable         # (actor, payload) -> {links, summary}
```

Ship exactly **three** actions (more later, pattern first):
1. `create_sales_order_draft(customer, items|from_quotation)` — resolves customer + items via
   contracts with candidate matching like extraction; risks: credit/overdue flags from
   `customer_profile`.
2. `create_purchase_request_draft(items|from_low_stock, warehouse?)` — "generate a PO from low
   stock" becomes: low-stock tool → this proposal.
3. `create_customer(name, phone?, tax_id?)` — duplicate-check first; a near-match is a **risk
   line** on the card, not a silent create.

`build_proposal` runs every module validation it can *without* writing (resolve codes, price the
lines, total in minor units) so the card shows real numbers and real record links before anything
exists.

## Task B — Loop + endpoint wiring

- Agent loop (session 9): add a fourth response option `{"action": "propose", "name": ...,
  "args": {...}}`. The loop calls `build_proposal`, emits SSE
  `{"type": "proposal", "proposal": {...}, "proposal_id": ...}`, persists it in the assistant
  Message `meta`, and ends the turn (an answer explaining the proposal streams first).
- `POST /api/assistant/actions/execute` — body `{message_id, decision: "confirm" | "dismiss"}`.
  Confirm: re-run validation, `execute()` as `request.user`, `audit.record(module="assistant",
  action=name, ...)`, mark the proposal consumed in `meta` (single-use — a second confirm 409s),
  return `{links, summary, followups}`. Dismiss: mark dismissed, audit it too.
- Permissions: `build_proposal` and `execute` both run as actor — a user who can't create sales
  orders gets the calm refusal at proposal time, never a card they can't use.

## Task C — ActionCard UI

Create `ActionCard.tsx`, rendered by `MessageList` for `proposal` meta:

- header: action title + affected-records count
- body: summary lines (what will be created, monochrome), record links (`EntityLink`), amounts via
  the money formatting already coming formatted from the server; **risks** as marked lines (icon +
  word — colour only with a word, per brand)
- footer: `Confirm` (primary) / `Dismiss` (quiet); confirming shows inline busy, then the card
  flips to its **result** state: success line, links to the created document, next-action chips
  from `followups`
- consumed/dismissed cards stay in history, visibly settled (reduced opacity + status word) —
  reload-safe because state lives in `meta`

## Task D — i18n + tests

Both locales: `assistant.action.confirm`, `dismiss`, `dismissed`, `executed`, `risks`,
`affected`, `openDocument`, `alreadyExecuted`.

`erp/assistant/tests/test_actions.py`: proposal → confirm creates the draft + audit row + links;
dismiss executes nothing; double-confirm 409s; unpermitted actor blocked at both stages;
`create_customer` near-duplicate surfaces the risk.

---

## Smoke Test

- [ ] "Create a sales order for <customer> with 2 of <item>" → card with priced lines + real links
- [ ] Confirm → draft exists in sales module, audit entry `module=assistant`, card shows document link
- [ ] Dismiss → nothing created; card settles
- [ ] Reload conversation → executed card still shows its result state
- [ ] "Generate a purchase request from low stock" → tool round then proposal, correct items
- [ ] User without sales-create permission asks the same → calm refusal, no card
- [ ] `pytest erp/assistant` + i18n parity + tsc + gate03 green

---

## After This Session

```
Smoke test passed?
→ Rename this file: append _done (e.g. FILE_01_CONVERSATIONS_BACKEND_done.md). A _done file is finished forever - never reopen it.
→ Type /compact in Claude Code
→ Open FILE_11_PAGE_CONTEXT.md and continue
```
