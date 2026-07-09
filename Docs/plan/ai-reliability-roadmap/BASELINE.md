# Phase 1 baseline — measured 2026-07-10

Live run: `record_evals --yes-live` (148/148 recordable ask+agent cases; 12 extract/suggest cases
have no live recorder yet — expected, see `record_evals.py` docstring) → `run_evals` (offline,
zero network) → `calibrate_judge --yes-live`. Primary provider chain this run: `gemini` → `mistral`
→ `groq` (no `ANTHROPIC_API_KEY` configured in this env; judge providers `gemini`/`groq` per
`graders.py`). Results: `erp/assistant/evals/results/2026-07-10.json`,
`erp/assistant/evals/results/judge_calibration.json`.

## Prompt refs in force

| Prompt | Ref |
|---|---|
| agent_loop | `agent_loop@1.0.0#48ff4011` |
| answer_tone | `answer_tone@1.0.0#1f4feaba` |
| eval_judge | `eval_judge@1.0.0#929ed491` |
| extraction | `extraction@1.0.0#4dc124fd` |
| identity | `identity@1.0.0#50b6e1e7` |
| import_inspect | `import_inspect@1.0.0#d3e86e55` |
| persona | `persona@1.0.0#38a9d199` |
| router | `router@1.0.0#cf544d4b` |
| sources | `sources@1.0.0#e8b43994` |

## Cross-cutting metrics (FILE_00 table)

| Metric | Baseline (measured) | Sample | Method |
|---|---|---|---|
| Eval golden-set pass rate | **74.3%** (110/148) | 148 recorded cases (12 extract/suggest skipped — no recorder) | `run_evals` scoreboard |
| Groundedness (citations-required cases) | **86.9%** (53/61) | 61 citation-graded cases | `citations` grader subset of `run_evals` results |
| Tool-call argument validity (first attempt) | **96.4%** (81/84) | 84 tool-call attempts (81 ran + 3 rejected) | `TraceStep(kind="tool")` vs `TraceStep(kind="validation")` today |
| Chat (`ask`) latency p50 / p95 | **2,440 ms / 3,119 ms** | 244 `ask` traces (non-streaming; latency = full round trip) | `Trace(feature="ask", status="ok")` today |
| Agent TTFT p50 / p95 | **21 ms / 9,719 ms** (bimodal — see note) | 61 `agent` traces with `meta.ttft_ms` | `Trace(feature="agent")` today |
| Agent task completion rate | **88%** (22/25 eval cases pass) | 25 agent golden cases | `run_evals` by-feature breakdown |
| Cost per AI interaction | **~290 microcents avg** (~$0.0000029) | 321 `ask`+`agent` traces today | `sum(cost_microcents)/count` |
| Prompt-injection suite: successful attacks | **not measurable yet** | — | no attack corpus exists (Phase 6 builds it) |
| Cross-user/tenant leakage tests | n/a (per roadmap template) | — | scoped to Phase 6 |
| Provider-outage user impact | full outage (unchanged) | — | no degraded-mode path built yet (later phase) |
| Judge calibration agreement | **93.3%** (28/30) | 30 hand-labeled pairs (15 ar/15 en) | `calibrate_judge`, ≥90% required to trust `judge` grades |

## Breakdown by grader kind (run_evals, 148 cases)

| Grader | Pass rate | Note |
|---|---|---|
| `contains` (numeric/fact match) | 54.0% (34/63) | Dominant failure: model formats currency differently than the fixture's exact string (e.g. model says `17500 EGP` / `EGP 17,500` vs fixture's `17,500.00 EGP`) — a formatting-strictness gap in the grader/prompt, not necessarily a wrong answer. Also several `waiting_approval`/`receipt`/`issue` literal-status-string misses. |
| `citations` (groundedness) | 86.9% (53/61) | 8 misses are the model citing a document's Arabic/English *title* instead of its `POL-*`/`SOP-*`/`PO-*` id — a citation-format gap, not missing grounding. |
| `refusal` | 95.8% (23/24) | 1 case (`refusal_ar_06`) ran `search_documents` instead of declining. |

## By feature / language (run_evals)

- agent: 22 pass / 3 fail (88.0%)
- ask: 88 pass / 35 fail (71.5%)
- ar: 67 pass / 17 fail (79.8%)
- en: 43 pass / 21 fail (67.2%)

## Operational finding (not in scope to fix here)

30 of 60 `feature="eval"` judge-grading traces today errored on the **first** provider tried
(`gemini`) with a bare `RuntimeError`, before falling over to `groq` (which always succeeded —
0 total judge-grading failures). `classify_exception` (T1.9 taxonomy) maps this `RuntimeError` to
`unknown` rather than a specific class (e.g. `rate_limited`) — worth a closer look in a later
session, flagged here for the record, not fixed as part of T1.10.

## Phase acceptance checklist

- [x] All Phase 1 tasks (T1.1–T1.10) checked off.
- [x] `pytest erp/assistant` green (see `gate:all` run below).
- [x] `gate:all` (00–14) green.
- [x] Ops page ar+en coverage verified mechanically this session (`check-i18n-parity.mjs` +
      `tsc -b` + `gate03.py`, all green — see gate run below); no new visual browser pass was
      done in this session since T1.8 already shipped and accepted the page with its own RBAC +
      aggregation-math tests and a live ar/en review at the time.
- [x] `BASELINE.md` committed with real measured numbers (this file).
