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

## Offline runner (T1.6)

`manage.py run_evals` grades every case that has a recording at `evals/recordings/<id>.json`
(`manage.py record_evals --yes-live` makes live calls to write one); cases without a recording are
skipped, not failed, so the dataset can grow ahead of the recordings that exercise it. `ask` and
`agent` cases run through the real service function end to end; `extract` stubs the provider call
and runs real post-processing; `suggest` has no Python service yet and always reports `no_runner`.
`judge` cases report `needs_judge` in the offline runner (judging needs a live model call). The
real judge grader (T1.7) is `graders.grade_judge()` — called live by `manage.py calibrate_judge
--yes-live` against `calibration_v1.jsonl` (30 hand-labeled ar/en pairs), which requires >= 90%
agreement before judge verdicts count, and unit-tested offline by injecting a recorded judge
output as `judge_call`.
