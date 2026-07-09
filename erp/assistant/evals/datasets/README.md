# Golden dataset v1 (ai-reliability T1.5)

`golden_v1.jsonl` — one graded case per line, no DB or provider access. Feeds the offline eval
runner (T1.6) and the LLM-judge grader (T1.7).

## Case schema

```
{
  "id": str,            # unique across the file
  "lang": "ar" | "en",
  "feature": "ask" | "agent" | "extract" | "suggest",
  "input": dict,        # "message" (+ optional context fields like entity_type/entity_id/status,
                         # or document_text for extract)
  "fixtures": dict,     # tool name -> canned result (or feature-specific payload for extract/suggest)
  "expected": dict       # exactly one of the keys below
}
```

`expected` keys (exactly one per case):

- `schema` — a JSON-schema the output must validate against.
- `contains` — list of substrings that must all appear in the answer.
- `citations` — list of citation ids (customer/order/item/document/... value) that must all be
  present in the answer's citations.
- `refusal: true` — the assistant must decline (out-of-scope, other-user data, write action,
  jailbreak/prompt-injection attempt, etc.).
- `judge` — a rubric string, graded only once T1.7 ships the LLM-as-judge grader.

## Minimum split (enforced by `tests/test_evals_dataset.py`)

- total ≥ 150
- Arabic (`lang: ar`) ≥ 90
- English (`lang: en`) ≥ 60
- refusal cases ≥ 20
- citation cases ≥ 20
- all `id`s unique

## Rule

**Never edit a shipped case's `expected` to make a failing model pass.** If a model's behavior
changed on purpose, add a new case (or a new dataset version) — don't silently loosen an existing
one. That would erase the yardstick the whole reliability roadmap is measured against.
