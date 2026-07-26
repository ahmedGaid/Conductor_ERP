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

## Retrieval suite (T3.3)

A separate suite measures `knowledge.search` quality, independent of the ask/agent golden set.

- `retrieval_corpus_v1.jsonl` — the fixture corpus. One line per doc: `{doc_key, lang, title,
  text}`. Each doc is authored under `CHUNK_CHARS` so it ingests to exactly one chunk, so the
  retrieval unit is the document and a query's relevant map keys cleanly by `doc_key`.
- `retrieval_v1.jsonl` — the query set. One line per query: `{id, lang, query, relevant}` where
  `relevant` is `{doc_key: grade}` with grade 2 (ideal), 1 (related), 0 (irrelevant). Minimums
  (enforced by `tests/test_retrieval_eval.py`): ≥ 80 queries, ≥ 50 Arabic; every `doc_key`
  referenced must exist in the corpus.

Run it: `manage.py run_evals --suite retrieval`. It builds the corpus in a rolled-back transaction
(never pollutes the dev DB), scores three strategies — `fts` (lexical baseline), `blend` (the
removed 0.5·tsrank + 0.5·cosine pre-fusion baseline, reconstructed only to measure against), and
`fusion` (the shipped RRF path) — with recall@5/10, MRR, nDCG@10 (pure functions in
`evals/retrieval_metrics.py`), and writes `evals/results/retrieval_<date>.json` plus the standing
`evals/results/retrieval_baseline_vs_fusion.json`.

Fully offline and deterministic: provider embeddings are replaced by a committed local
bag-of-tokens vector (`evals/retrieval.fixture_embed`), so no network / API key / pgvector binary
is needed. Absolute recall is therefore bounded by the fixture embedding, not live Gemini vectors —
the suite proves the ranking/fusion *pipeline* reproducibly. See the `note` in the results file for
how to read the fts/blend/fusion rows.
