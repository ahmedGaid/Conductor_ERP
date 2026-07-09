# SESSION 12 — Guided Detours: Actionable Suggestions with Deep Links
# Files: erp/assistant/services/suggestions.py (new), erp/assistant/services/agent.py, erp/assistant/tools.py, apps/web/src/assistant/SuggestionCard.tsx (new), apps/web/src/assistant/MessageList.tsx, apps/web/src/api/assistant.ts, apps/web/src/i18n/locales/*.json, erp/assistant/tests/test_suggestions.py (new)

---

## Before You Start

1. Open `erp/assistant/services/agent.py` → the loop's response options (`tool` / `clarify` /
   `propose` / `answer` / `import`) and how tool errors feed back into the loop.
2. Open `erp/assistant/tools.py` → the `{"error": ...}` convention. This session upgrades errors
   that mean "missing dependency" into structured, resolvable blockers.
3. Open `erp/identity/rbac.py` → how to check one permission code for an actor (the exact call
   `roles_admin` / contracts use). Suggestions are permission-filtered **server-side**.
4. Open `apps/web/src/App.tsx` routes block (lines ~185–214) → the real route paths for create/
   detail pages per entity. The route registry below must match these exactly — copy from the
   file, never from memory.
5. Open `apps/web/src/assistant/ActionCard.tsx` (session 10) → card anatomy to match.

"Do not write anything yet."

---

## Core principle (carry into every task)

The assistant never stops at "supplier doesn't exist." Every blocker answers three questions:
**what's wrong → fastest fix → how we continue after.** A suggestion without a working path to
resolution does not ship.

## Task A — Blocker vocabulary in tools

In `tools.py` (and `actions.py` where `build_proposal` resolves references), upgrade the
missing-dependency failures from plain `{"error": str}` to:

```python
{"blocker": {
    "kind": "missing" | "inactive" | "ambiguous",
    "entity": "supplier",              # registry key, see Task B
    "query": "ABC Trading",            # what we looked for
    "candidates": [...],               # near matches, when "ambiguous" (reuse extraction's scorers)
}}
```

Only for dependency-shaped failures (record not found, inactive warehouse, no near-match). Plain
errors (permission, validation) keep the existing string convention untouched.

## Task B — Suggestion builder (server-side, permission-aware)

Create `erp/assistant/services/suggestions.py`:

```python
"""Blocker → actionable suggestion. Permission-filtered here, server-side — the client renders
whatever it receives; it never decides what the user may do.

ENTITY_REGISTRY maps entity key → {create_route, detail_route, list_route, permission_code,
create_action (session-10 action name when one exists, e.g. "create_customer")}.
Routes are copied verbatim from apps/web/src/App.tsx — a wrong route here is a broken promise.
"""

def build_suggestion(actor, blocker: dict, resume_hint: str) -> dict:
    """Returns {issue, options: [...], no_permission: str | None}.

    Options, in preference order, only those the actor can actually use:
    - {"kind": "inline_action", "action": "create_customer", "args": {...}}   # stay in chat
    - {"kind": "deep_link", "label_key": "...", "to": "/purchasing/suppliers/new",
       "prefill": {"name": "ABC Trading"}, "expect": {"entity": "supplier", "query": "..."}}
    - {"kind": "review_candidates", "candidates": [...]}                       # ambiguous
    - {"kind": "open_record", "to": "/inventory/warehouses/A"}                 # inactive/config
    """
```

Permission denied ⇒ `options` contains NO unavailable action; instead `no_permission` carries the
calm alternative ("You don't have permission to create suppliers. Ask an administrator, or I can
draft a request note.") — offer `inline_action: assign_task`-style alternatives ONLY if such a
mechanism already exists in the app (check notifications/approvals contracts; if none, plain text).

Deep-link `prefill`: pass extracted values as query params (`?prefill=` JSON, URL-encoded) — Task E
makes the target forms consume it.

## Task C — Loop integration

In `agent.py`: when a tool/action round returns a `blocker`, the loop does NOT retry blindly.
New response option for the model:

```json
{"action": "suggest", "blocker": {...}, "resume": "<what continues after, one sentence>"}
```

The loop calls `build_suggestion`, streams SSE `{"type": "suggestion", "suggestion": {...}}`,
persists it in the assistant Message `meta` (like proposals), and ends the turn with a short
streamed explanation: issue → fix → what happens after ("After you save the supplier, I'll bring
you back to this purchase order and continue."). The pending work (e.g. the unproposed sales
order payload) is stored in `meta.pending` — session 13 consumes it.

## Task D — SuggestionCard UI

Create `SuggestionCard.tsx`, rendered by `MessageList` for `suggestion` meta:

- issue line: icon + plain sentence (kind-specific: missing / inactive / needs review)
- option buttons: `inline_action` → runs the session-10 confirm flow in place;
  `deep_link` → real `<Link>` (module icon + label + a small ↗), navigates while the panel stays
  open (floating/docked persist across routes already — verify, don't rebuild);
  `review_candidates` → compact candidate list with scores, pick-one maps it and resumes
- `no_permission` state: quiet, blame-free text block, zero disabled buttons (unavailable ≠ greyed)
- resolved state (session 13 flips it): settled like consumed ActionCards

Extend `ChatEvent` + citation/link types in `api/assistant.ts`.

## Task E — Prefill on create pages

Pick the three create surfaces the registry links to most (supplier, customer, item — find the
actual form components from the routes). Add a tiny shared hook `usePrefill()` in
`apps/web/src/lib/` that reads the `?prefill=` param once, validates keys against the form's known
fields, and returns initial values. Wire into those three forms only — additive, defaults
unchanged when the param is absent.

## Task F — i18n + tests

Both locales: `assistant.suggest.*` — `missing`, `inactive`, `ambiguous`, `create`, `open`,
`review`, `mapExisting`, `noPermission`, `afterResume` (interpolated).

`erp/assistant/tests/test_suggestions.py`: blocker → options for a permitted actor include
inline action + deep link with correct route; unpermitted actor gets `no_permission` and zero
options; ambiguous blocker returns candidates; registry routes all exist in a hardcoded copy of
the route list (guard test — fails loudly if App.tsx moves a route without updating the registry).

---

## Smoke Test

- [ ] Ask to create an order for a nonexistent customer → suggestion card: issue + Create Customer
      (inline) + deep link; explanation promises the return
- [ ] Deep link opens the create form **prefilled** with the extracted name; panel survives navigation
- [ ] Same ask as a user without customer-create → calm no-permission text, no buttons
- [ ] Extraction with an ambiguous supplier → candidate review, picking one continues the flow
- [ ] Inactive-warehouse style blocker → "open settings" link to the right page
- [ ] `pytest erp/assistant` + i18n parity + tsc + gate03 green

---

## After This Session

```
Smoke test passed?
→ Rename this file: append _done (e.g. FILE_01_CONVERSATIONS_BACKEND_done.md). A _done file is finished forever - never reopen it.
→ Type /compact in Claude Code
→ Open FILE_13_WORKFLOW_RESUME.md and continue
```
