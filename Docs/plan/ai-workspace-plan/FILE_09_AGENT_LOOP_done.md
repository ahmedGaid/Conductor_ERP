# SESSION 9 — Agentic Loop: Plan → Tools → Validate → Answer
# Files: erp/assistant/services/agent.py (new), erp/assistant/api/views.py (ChatView), apps/web/src/assistant/MessageList.tsx, apps/web/src/api/assistant.ts, apps/web/src/i18n/locales/*.json, erp/assistant/tests/test_agent.py (new)

---

## Before You Start

1. Open `erp/assistant/services/ask.py` → today's single-round router (one tool, one answer). The
   agent loop is its multi-round sibling; `ask.py` stays for the legacy `/ask` endpoint.
2. Open `erp/assistant/client.py` → `complete_json` (loop rounds) and `complete_stream` (final
   answer only).
3. Open `erp/assistant/tools.py` → the catalog + the `{"error": ...}` convention from session 8.
4. Open `erp/assistant/api/views.py` → `ChatView`'s SSE generator and event serializer helper from
   session 2 — new event types plug into it.

"Do not write anything yet."

---

## Task A — The loop

Create `erp/assistant/services/agent.py`:

```python
"""The agentic loop: understand → gather via tools → validate → answer.

Hard bounds keep it predictable: max 6 tool rounds, read-only catalog only (write actions are
session 10's proposal objects — the loop itself NEVER mutates). Runs as the actor; a tool
permission error is information for the model, not an exception.
"""

MAX_ROUNDS = 6

def run(actor, conversation, user_message: str, page: dict | None, attachments=None):
    """Generator yielding SSE-ready event dicts (see protocol below)."""
```

Per round, call `complete_json` with: system prompt (`context.build_system_prompt`), the
conversation tail (last ~20 messages), tool results so far, and the loop instruction — respond with
exactly one of:

```json
{"action": "tool", "tool": "<name>", "args": {...}, "why": "<≤8 words, user-visible>"}
{"action": "clarify", "question": "..."}   // only if genuinely blocked
{"action": "answer"}                        // enough gathered — produce the final answer
```

- `tool` → execute from the catalog (unknown tool / bad args ⇒ feed the validation error back as
  the tool result; the model self-corrects — this is the recovery path), append result, next round.
- `clarify` → stream it as the final text and stop (counts as the answer; no dead-end states).
- `answer` (or MAX_ROUNDS reached) → stream the final answer via `complete_stream`, grounded in the
  accumulated tool results; merge all rounds' citations, deduplicated.

Persist the assistant Message with `meta={"steps": [...], "citations": [...], "followups": [...]}` —
steps are `{tool, why, ok}` summaries, never raw payload dumps.

## Task B — Stream the thinking

New SSE event types through the session-2 serializer:

```
data: {"type": "step", "label": "<why>", "tool": "sales_summary", "state": "running"}
data: {"type": "step", "label": "<why>", "tool": "sales_summary", "state": "done"}
```

`ChatView` switches from the ask pipeline to `agent.run(...)` — the generator shape means the view
body barely changes. Legacy `/ask` keeps using `ask.py` untouched.

## Task C — Inline progress UI

In `MessageList.tsx`: while streaming, render `step` events as a quiet progress stack above the
forming answer — single-stroke icon per state (⋯ running → ✓ done, from `icons.tsx`, no spinner
carnival), label from `why`. After `done`, the stack collapses into one summary line
(`assistant.stepsSummary`: "Checked 3 sources" /「راجع ٣ مصادر」-style with proper Arabic plural
rules via i18n count forms) that expands on click — the "expandable reasoning" surface, calm by
default. Extend `ChatEvent` in `api/assistant.ts` accordingly.

## Task D — Tests

`erp/assistant/tests/test_agent.py` with a scripted fake `complete_json` (sequence of responses):
- two tool rounds then answer → events in order, steps persisted in meta
- unknown tool name → error fed back, model corrects, loop completes
- MAX_ROUNDS runaway script → loop force-answers at 6, never spins
- clarify short-circuits cleanly

---

## Smoke Test

- [ ] "Compare this month's sales with purchases and flag anything odd" → 2+ steps visible, then a
      grounded streamed answer with citations from both modules
- [ ] Step labels are human ("Checking sales…"), collapse to a summary, expand on click
- [ ] Cancel mid-loop: stream stops, partial persists, no server traceback
- [ ] Vague ask ("handle the thing") → one calm clarifying question, not six tool rounds
- [ ] `pytest erp/assistant` + tsc + i18n parity green

---

## After This Session

```
Smoke test passed?
→ Rename this file: append _done (e.g. FILE_01_CONVERSATIONS_BACKEND_done.md). A _done file is finished forever - never reopen it.
→ Type /compact in Claude Code
→ Open FILE_10_SAFE_ACTIONS.md and continue
```
