# SESSION 11 — Embedded Page Assistant
# Files: apps/web/src/assistant/AssistantPanel.tsx, apps/web/src/assistant/context.ts, apps/web/src/assistant/suggestions.ts (new), erp/assistant/services/agent.py, apps/web/src/i18n/locales/*.json, erp/assistant/tests/test_page_context.py (new)

---

## Before You Start

1. Open `apps/web/src/assistant/context.ts` (session 3) → `PageContext` already carries
   `module` + `record`. This session makes the assistant *visibly* use it.
2. Open `erp/assistant/services/agent.py` → where `page` enters the prompt.
3. Open `erp/assistant/tools.py` → which tools can resolve a record given `type` + `id`
   (order, customer, item, journal, workflow — from session 8).
4. Open `apps/web/src/app/DocumentCrumb.tsx` → confirm what record pages actually register
   (spot-check a sales order detail page and an item detail page).

"Do not write anything yet."

---

## Task A — Context chip in the panel

In `AssistantPanel.tsx` header, when `collectContext().record` exists, show a quiet context chip:
single-stroke module icon + record label ("SO-1042"), with a small × to detach for this
conversation (state on the provider: `contextDetached`). Detached ⇒ context still sent, but with
`"detached": true` so the server treats it as background, not subject. The chip re-collects on
route change while the panel is open — walking between records updates it live.

## Task B — "This order" resolution, server-side

In `agent.py`, strengthen the page section handling: when `page.record` exists and is not
detached, prepend a resolution rule to the loop prompt — "Pronouns and bare references ('this
order', 'هذا الأمر', 'it', 'the customer') resolve to the page record: {type} {id} ({label}).
Prefer tools scoped to it." When the user's first loop round references the record, the loop
should reach for the matching detail tool (`find_orders`/`customer_profile`/…) with the id —
verify the catalog covers each DocumentCrumb type and add the missing thin tool if one gap exists
(one only; bigger gaps go back to session 8's pattern).

## Task C — Per-module suggestions

Create `apps/web/src/assistant/suggestions.ts`:

```typescript
// Suggested prompts keyed by module (and record presence). i18n keys, not strings.
export function suggestionKeys(module: string | null, hasRecord: boolean): string[]
```

Map (4 each, both locales under `assistant.pageSuggest.*`):
- `sales` + record: "Explain this order's margin", "Draft the invoice email", "Duplicate as a new
  draft", "Payment history of this customer"
- `sales` bare: overdue invoices, this month vs last, top customers, draft an order…
- `purchasing`, `inventory`, `accounting`, `crm` similarly — write them with the module's tools
  from session 8 in mind so every chip actually works
- `null` (dashboard/settings): keep the original s1–s4

Empty-conversation state in the panel now shows these instead of the static four. Every chip must
route to a real tool/action — no aspirational chips.

## Task D — Tests + i18n

`erp/assistant/tests/test_page_context.py`: prompt carries the resolution rule with record;
detached page renders background-only; scripted loop resolves "this order" to the right tool call.
i18n: all `assistant.pageSuggest.*` keys in both locales (parity gate enforces).

---

## Smoke Test

- [ ] On a sales order: chip shows the order; "what's the margin on this?" answers without asking which order
- [ ] Navigate to a customer with the panel open → chip follows; "does he have overdue invoices?" resolves
- [ ] Detach → "this order" now triggers a clarifying question (proof detach works)
- [ ] Suggestion chips change per module; each fires a working tool round
- [ ] Arabic: "هذا الأمر" resolves identically
- [ ] i18n parity + tsc + gate03 + pytest green

---

## After This Session

```
Smoke test passed?
→ Rename this file: append _done (e.g. FILE_01_CONVERSATIONS_BACKEND_done.md). A _done file is finished forever - never reopen it.
→ Type /compact in Claude Code
→ Open FILE_12_GUIDED_DETOURS.md and continue
```
