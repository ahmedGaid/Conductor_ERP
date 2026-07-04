# SESSION 5 — Source-Routing + Transparency in the Prompts
# Files: erp/assistant/services/context.py, erp/assistant/services/ask.py, erp/assistant/tests/test_context.py

---

## Before You Start

1. Open `erp/assistant/services/context.py` → re-read `_IDENTITY`, `_PERSONA`,
   `build_system_prompt` (the section order matters).
2. Open `erp/assistant/services/ask.py` → find `_ANSWER_TONE` → read it fully (this session
   appends to it; know what is already said so nothing is duplicated).
3. Open `erp/assistant/tests/test_context.py` → see the assertion style for prompt content.

Do not write anything yet. Prompt text is code: keep it COMPACT — every line below rides on
every request.

---

## Task A — Sources block in `context.py`

Below `_PERSONA`, add:

```python
_SOURCES = (
    "Sources of truth, in order: (1) live ERP data comes ONLY from data tools — never from "
    "memory, never guessed; (2) company knowledge (policies, SOPs, catalogs, contracts) comes "
    "ONLY from document search; (3) conversation history carries context (current task, "
    "selected records, preferences) but is never a source of business facts; (4) your own "
    "reasoning serves explanation, writing, and math over numbers already retrieved. Never "
    "invent IDs, quantities, prices, balances, suppliers, customers, or document content. "
    "When something needed is missing, say exactly what is missing. Be transparent about "
    "provenance: facts from document search are 'from company documentation' (من مستندات "
    "الشركة); facts from data tools are live ERP data. Never imply you accessed something "
    "you did not retrieve."
)
```

In `build_system_prompt`, find:

```python
    sections.append(_PERSONA)
    return "\n\n".join(sections)
```

and change to:

```python
    sections.append(_PERSONA)
    sections.append(_SOURCES)
    return "\n\n".join(sections)
```

## Task B — Answer-tone additions in `ask.py`

Append to `_ANSWER_TONE` (string concatenation at its definition, matching its formatting) —
ONLY the parts not already covered by what you read in step 2:

```python
    " Keep answers concise and action-oriented: lead with the answer, use short lists or a "
    "compact table for multiple records, never long paragraphs. When part of the answer came "
    "from company documents, attribute it (e.g. 'according to <document title>' / "
    "'وفقاً لمستند <العنوان>'). When a data result was empty or a tool failed, say what "
    "happened plainly and offer the nearest next step; never fill gaps with invented values."
)
```

(If `_ANSWER_TONE` already states conciseness/format rules, keep only the attribution +
gap-honesty sentences. Both `ask.py`'s single-shot path and `agent.py`'s `_answer_system`
consume `_ANSWER_TONE`, so this lands on both paths with one edit.)

## Task C — Tests

Extend `tests/test_context.py` in its existing style:

- test_prompt_names_the_four_sources — prompt contains "data tools", "document search",
  "never a source of business facts", "Never invent"
- test_prompt_orders_sources_after_persona — index of the sources text > index of the persona
  text (guards section order)
- test_prompt_carries_arabic_provenance_phrase — "من مستندات الشركة" present

And one in `tests/test_ask.py` (or wherever `_ANSWER_TONE` is asserted today — follow the
codebase): test_answer_tone_requires_attribution_and_honest_gaps — `_ANSWER_TONE` contains
"according to" and "never fill gaps".

---

## Smoke Test

- [ ] `pytest erp/assistant` green
- [ ] Dev server: ask "اشرح لي الفرق بين أمر البيع والفاتورة" (general knowledge) → answered
      directly, NO tool steps fired
- [ ] Ask a policy question → answer includes attribution wording ("وفقاً لمستند…")
- [ ] Ask about a customer that does not exist → answer says it was not found, suggests the
      nearest step; no invented balance
- [ ] Ask "what did I ask you before?" → answered from history, no tool call (memory = context)

---

## After This Session

```
Smoke test passed?
→ Commit, rename this file FILE_05_SOURCE_ROUTING_PROMPT_done.md
→ Backend + prompts are complete — natural merge checkpoint.
→ Type /compact in Claude Code
→ Open FILE_06_KNOWLEDGE_UI.md and continue (fresh session)
```
