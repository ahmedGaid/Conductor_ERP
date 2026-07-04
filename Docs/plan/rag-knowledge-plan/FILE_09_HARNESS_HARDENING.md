# SESSION 9 — Harness Hardening: Intent + Duplicate-Call Guard
# Files: erp/assistant/services/agent.py, erp/assistant/tests/test_agent.py

---

## Before You Start

1. Open `erp/assistant/services/agent.py` → re-read `_LOOP_SYSTEM`, `_LOOP_SCHEMA`, the round
   loop in `run` (the `for _round in range(MAX_ROUNDS)` block) and `_persist`.
2. Open `erp/assistant/tests/test_agent.py` → the fake-planner pattern (scripted
   `complete_json` return values).

Do not write anything yet. The harness spec's orchestration steps (understand → gather →
validate → confirm → answer) ALREADY exist as the loop; this session adds only the two missing
behaviours: explicit intent classification and the no-duplicate-tool-calls rule.

---

## Task A — Intent classification

1. In `_LOOP_SCHEMA["properties"]`, add:

```python
        "intent": {"type": ["string", "null"],
                   "description": "on your FIRST decision only: the request's intent, one of "
                                  "lookup | report | document_search | create | update | "
                                  "workflow | file | explain | conversation | mixed"},
```

   and add `"intent"` to the schema's `required` list (nullable-required, like the others).

2. In `_LOOP_SYSTEM`, after the line listing the four decision JSON shapes, add:

```python
    "On your first decision of a turn, also set intent (lookup/report/document_search/create/"
    "update/workflow/file/explain/conversation/mixed) — it routes nothing by itself but is "
    "recorded; classify honestly.\n"
```

3. In `run`: capture `intent = decision.get("intent")` from the FIRST round only; in
   `_persist`, add it to meta: `meta = {"citations": ..., "used_tool": ..., "steps": steps,
   "intent": intent}`. (Additive meta key — the client ignores unknown keys.)

## Task B — Duplicate-call guard

In the round loop, BEFORE `yield {"type": "step", ...}` / `_run_tool`, add:

```python
        signature = (name, tuple(sorted(
            (k, str(decision.get(k))) for k in _ARG_FIELDS if decision.get(k) is not None
        )))
        if signature in seen_calls:
            results.append({"tool": name, "why": why, "data": {
                "error": "You already ran this exact call this turn. Use its earlier result, "
                         "change the arguments, or answer."}})
            continue
        seen_calls.add(signature)
```

with `seen_calls: set[tuple] = set()` initialised next to `results`. Note: `continue` still
consumes a round (MAX_ROUNDS stays the hard bound — a stuck planner converges to answer).

## Task C — Tests

Extend `tests/test_agent.py`:
- test_intent_recorded_on_message_meta — scripted planner sets intent "report" round 1 →
  saved assistant message meta["intent"] == "report"
- test_duplicate_tool_call_blocked — planner scripts the SAME tool+args twice then answer →
  tool runner executed once, second round's result carries the duplicate error
- test_same_tool_different_args_allowed — two `stock_on_hand` calls with different queries →
  both execute
- test_max_rounds_forces_answer — planner always returns tool decisions → loop stops at
  MAX_ROUNDS, an answer is still produced and persisted (may already exist — check; if it
  exists, extend it to assert `seen_calls` didn't break it)

---

## Smoke Test

- [ ] `pytest erp/assistant` green
- [ ] Dev server: ask a multi-part question → steps show distinct tools, no repeated
      identical step chips
- [ ] Ask anything → saved message meta (check via conversation reload or DB) carries intent
- [ ] Existing SSE event protocol unchanged (client renders steps/tokens/citations as before)

---

## After This Session

```
Smoke test passed?
→ Commit, rename this file FILE_09_HARNESS_HARDENING_done.md
→ Type /compact in Claude Code
→ Open FILE_10_CONFIRM_REGISTRY.md and continue
```
