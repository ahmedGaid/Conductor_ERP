# SESSION 8 — Richer Context Envelope (Harness spec)
# Files: apps/web/src/assistant/context.ts, erp/assistant/services/context.py, erp/assistant/services/agent.py, erp/assistant/tests/test_context.py

---

## Before You Start

1. Open `apps/web/src/assistant/context.ts` → read the whole client collector (what the page
   envelope already carries: module, path, record, recent).
2. Open `erp/assistant/services/context.py` → re-read `_page_block` and `_company_block`.
3. Open `erp/identity/services` (follow `get_org_preferences`) → check which of these concepts
   actually exist in this codebase: branch, default warehouse, fiscal year/period. **Only
   context fields that exist get added — never invent a concept the ERP does not have.**
4. Open `erp/assistant/services/agent.py` → re-read how `meta` lands on assistant messages
   (`_persist`: citations/used_tool/steps/proposal).

Do not write anything yet.

---

## Task A — Client collector additions (`context.ts`)

Extend the collected page envelope, following the existing shape:

- `filters`: the current route's query params as `{key: value}` (cap: 10 entries, values
  truncated to 80 chars) — the assistant then knows "the list the user is looking at".
- `dirty`: boolean — true when the current page has unsaved form changes. Implementation:
  a tiny module-level registry in `context.ts`:

```ts
let dirtyFlag = false;
export function markFormDirty(v: boolean) { dirtyFlag = v; }
```

  Wire `markFormDirty` ONLY into forms that already track dirtiness (read one create/edit form
  first; if there is no existing dirty tracking, wire the create forms touched by
  `lib/usePrefill.ts` and leave others for later — additive, no form rewrites).

## Task B — Server blocks (`context.py`)

1. In `_page_block`, after the `recent` lines, render filters + dirty:

```python
    filters = page.get("filters") or {}
    if filters:
        rendered = ", ".join(f"{k}={v}" for k, v in list(filters.items())[:10])
        lines.append(f"- Active list filters: {rendered}.")
    if page.get("dirty"):
        lines.append("- The user has UNSAVED form changes on this page: never suggest "
                     "navigation that would lose them without saying so.")
```

2. In `_company_block`, append branch / default warehouse / fiscal year **only for the
   concepts you confirmed exist in step 3** (same sentence style as the currency line).

3. New `_recent_actions_block(conversation)` — the harness spec's "previous AI actions":
   the last 5 assistant messages carrying `meta.proposal`, rendered one line each:
   `"- Recently proposed/executed: <action name> (<status>)."` Returns None when empty.
   `build_system_prompt` gains an optional `conversation=None` kwarg and appends this block
   after the page section. (`agent._answer_system` passes its conversation through; `ask.py`'s
   single-shot path passes nothing — signature stays backward-compatible.)

## Task C — Tests

Extend `tests/test_context.py`:
- test_filters_rendered_and_capped — 12 filters in → 10 rendered
- test_dirty_flag_warns_about_unsaved_changes
- test_recent_actions_block_lists_proposals — conversation with 2 proposal messages →
  both named with status
- test_prompt_without_conversation_unchanged — no kwarg → prompt identical to before
  (regression guard for ask.py path)

---

## Smoke Test

- [ ] `npx tsc --noEmit` + `pytest erp/assistant` green
- [ ] On a filtered list page, ask "what am I looking at?" → answer reflects the filters
- [ ] Dirty a create form, ask something → assistant's suggestions acknowledge unsaved changes
- [ ] After confirming a proposal, ask "what did you just do?" → answered from the
      recent-actions block without re-running tools
- [ ] Existing envelope tests still green

---

## After This Session

```
Smoke test passed?
→ Commit, rename this file FILE_08_CONTEXT_ENVELOPE_PLUS_done.md
→ Type /compact in Claude Code
→ Open FILE_09_HARNESS_HARDENING.md and continue
```
