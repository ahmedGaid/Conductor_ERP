# SESSION 3 — Context Envelope + Personas
# Files: erp/assistant/services/context.py (new), erp/assistant/services/ask.py, erp/assistant/api/views.py, apps/web/src/assistant/context.ts (new), apps/web/src/api/assistant.ts, erp/assistant/tests/test_context.py (new)

---

## Before You Start

1. Open `erp/assistant/services/ask.py` → find where the system/router prompt is assembled today.
2. Open `erp/identity/rbac.py` → find how to read a user's effective permissions/modules (see
   `roles_admin.role_detail` for the vocabulary: modules, actions, scopes).
3. Open `apps/web/src/app/AppShell.tsx` → read `moduleFromPath` (line ~25) — the client-side module
   detection to reuse, and `DocumentCrumbProvider` — how the current document is already tracked.
4. Open `apps/web/src/app/DocumentCrumb.tsx` → understand what a page registers when viewing a
   record (label/route); this is our "selected record" source.
5. Open `Docs/Brand/Conductor_Visual_Identity_System.md` §6 → the Arabic lexicon (canonical terms
   the prompt must enforce).

"Do not write anything yet."

---

## Task A — Client context collector

Create `apps/web/src/assistant/context.ts`:

```typescript
// What the assistant already knows without asking. Collected fresh per message send.
export interface PageContext {
  path: string;            // location.hash route, e.g. "/sales/orders/42"
  module: string | null;   // sales | purchasing | inventory | accounting | crm | null
  record: { type: string; id: string; label: string } | null; // from DocumentCrumb
  language: "ar" | "en";
  recent: string[];        // last 5 visited paths (module pages only)
}

export function collectContext(): PageContext
```

`module` reuses the `moduleFromPath` logic (export it from `AppShell.tsx` rather than copying).
`record` reads the current DocumentCrumb value — add a small getter to `DocumentCrumb.tsx`'s
context if none exists. `recent` is a module-scoped ring buffer in `sessionStorage`, updated from a
tiny effect in `AppShell` (5 entries max). No API calls here — collection must be synchronous.

In `api/assistant.ts`, extend `chatStream`'s body type with `context?: PageContext` and pass it
through verbatim.

## Task B — Server context builder

Create `erp/assistant/services/context.py`:

```python
"""Builds the system prompt: who the user is, where they are, what Conductor is.

The model never asks for information this envelope already carries.
"""

def build_system_prompt(actor, page: dict | None) -> str
```

Sections, in order:

1. **Identity** — "You are Conductor AI, part of Conductor ERP for Egyptian SMBs…" Tone rules from
   the brand: calm, precise, blame-free, no exclamation marks; answer in the user's language;
   Arabic uses the canonical lexicon — one word per concept (list the §6 terms relevant to ERP
   entities: عميل، مورد، صنف، أمر بيع، فاتورة…).
2. **User** — username, display name, role names, module list they can access, data scope. Derive
   from `erp.identity` the same way `roles_admin.role_detail` does. State plainly: "Never reveal or
   act beyond these permissions."
3. **Page** — from the `page` dict (the client envelope): current module, route, selected record
   ("The user is viewing sales order SO-1042"), language, recent pages. Skip the section cleanly
   when absent.
4. **Company** — company name, base currency (EGP, integer minor units on the wire), VAT context —
   read from wherever company settings live (find it: grep `company` in `erp/*/models.py` before
   writing; if there is no settings model yet, hardcode the two known facts and leave a TODO).
5. **Personas** — one paragraph: "Adopt the expert lens the question calls for — accountant for
   journal questions, inventory planner for reorder questions, financial controller for cash/margin
   questions — without announcing the persona or changing voice."

Keep the whole prompt under ~120 lines; it is rebuilt per request, never cached stale.

## Task C — Wire it in

- `ChatView` (and `AskView`) parse optional `context` from the body and pass `page=context` down.
- In `services/ask.py`, replace the current hardcoded system-prompt fragment with
  `context.build_system_prompt(actor, page)` — keep the tool-router portion of the prompt intact,
  appended after the envelope.

## Task D — Tests

`erp/assistant/tests/test_context.py`:
- prompt contains username + role + module list for a limited user
- page section renders record line when given, absent when not
- Arabic-language envelope includes the lexicon block
- a user with no sales permission → prompt says sales is not accessible

---

## Smoke Test

- [ ] `pytest erp/assistant` green
- [ ] `npx tsc --noEmit` green
- [ ] Ask "where am I?" from a sales order page → answer names the order without any lookup
- [ ] Ask in Arabic → answer in Arabic using canonical terms
- [ ] Limited user asks about payroll → assistant states it's outside their access, calmly
- [ ] `/ask` without context (old page) still works unchanged

---

## After This Session

```
Smoke test passed?  End of Phase 1 — commit, merge checkpoint.
→ Rename this file: append _done (e.g. FILE_01_CONVERSATIONS_BACKEND_done.md). A _done file is finished forever - never reopen it.
→ Type /compact in Claude Code
→ Open FILE_04_PANEL_SHELL.md and continue
```
