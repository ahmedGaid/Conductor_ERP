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

---

# Phase 2 — measured 2026-07-12

Same golden set (`golden_v1.jsonl`, 160 cases / 148 recorded), same offline harness
(`manage.py run_evals`) — the only change is that `ask`/`agent`'s real service code now calls
`gateway.complete_json` (T2.1) instead of the pre-gateway `services/llm.py`, so this run proves
the gateway's caching/budget/breaker layers (T2.2–T2.8) didn't move the needle on answer quality.

| Metric | Phase 1 baseline | Phase 2 (2026-07-12) | Note |
|---|---|---|---|
| Eval golden-set pass rate | 74.3% (110/148) | **74.3% (110/148)** | byte-identical result set — same failures, same case ids (`erp/assistant/evals/results/2026-07-12.json`) |
| Exact-match cache hit rate (`digest`/`suggest`/`judge`) | n/a (didn't exist) | **not yet measurable** | no production traffic exists pre-launch in this customer-hosted, single-tenant deployment; the ≥60% target is a live-ops metric (`OpsSummaryView.cache.hit_rate`), proven mechanically instead by `tests/test_response_cache.py` (hit on repeat input, miss after TTL/version bump) |
| Knowledge Q&A semantic cache hit rate | n/a (didn't exist) | **not yet measurable** | same reason; proven mechanically by `tests/test_semantic_cache.py` (9 cases — paraphrase hit ≥0.95 cosine, cross-user isolation, ingestion-bump invalidation) |
| Provider-outage user impact | full outage (unchanged, Phase 1) | **no outage — automatic failover** | breaker + chain-walk (T2.3); drill below |
| Failover drill date | — | **2026-07-12** | see FILE_02 "Phase 2 acceptance" section — breaker-level simulation (`full → degraded → down → full`); a live real-key run is a user-initiated follow-up (`--yes-live` posture, same as T2.4) |
| `/api/assistant/status` mode surface | didn't exist | **shipped (T2.9)** | `full`/`degraded`/`down`, derived from breaker + budget state; ar/en panel notice |

## Phase 2 acceptance checklist

- [x] All Phase 2 tasks (T2.1–T2.9) checked off.
- [x] `pytest` green — 859 tests (repo-wide, up from 852 at T2.8).
- [x] `gate:all` (00–15) green.
- [x] i18n parity (1834 keys) + `tsc -b` + `gate03` (brand) green; bundle budget green (239.4 kB
      gzip main chunk, within the 250 kB budget).
- [x] Golden evals re-run offline through the gateway — 74.3% (110/148), not below Phase 1.
- [x] Staging failover drill documented (see FILE_02).
- [x] This file committed with the Phase 2 columns above.

---

# T3.8 — page-context distillation, measured 2026-07-29

Method: `context._page_block(actor, page)` called directly for one real fixture record per type
(real DB rows via each module's own model, actor a superuser so scope never narrows the fixture
out), token count via `tracing.estimate_tokens` — the exact heuristic `envelope.assemble` uses to
budget the real `page` section. "Before" = the same call with that type's entry popped out of
`page_distill.DISTILLERS` (reproduces pre-T3.8 behavior exactly); "after" = the shipped registry.

| Page type | Before (tokens) | After (tokens) | Delta |
|---|---|---|---|
| sales.orders | 103 | 137 | +34 |
| sales.customers | 104 | 121 | +17 |
| purchasing.orders | 106 | 133 | +27 |
| inventory.items | 104 | 123 | +19 |
| accounting.journals | 106 | 126 | +20 |
| **median** | **104** | **126** | **+22 (+21%)** |

**The plan's "−50% on the page section" target is not met — and isn't the real story.** The
`page` section was never a raw dump: even before T3.8 it was one short generic line ("They are
viewing sales.orders SO-2026-000042.") carrying zero business facts, so there was nothing
oversized in *this* section to cut. T3.8 adds real facts (status/amounts/counts/open issues) to a
section that used to have none — a deliberate, bounded growth (every distiller stays well under
the 150-token/record ceiling; see `test_page_distill.py::test_longest_snapshot_stays_under_150_tokens`).

The token saving T3.8 actually targets shows up **outside** this section: before T3.8, answering
"what's the status/outstanding on this order" required the planner to spend a full extra loop
round on a detail tool (`find_orders`/`get_order` etc.), whose raw JSON result — for
`sales.orders`/`purchasing.orders` — includes every line item, routinely hundreds of tokens, plus
the round-trip's own planning overhead. That avoided round-trip isn't captured by "page section
tokens before/after" and isn't measured here (it would need live/recorded conversation traces,
out of scope for this offline check) — flagged for a later session with real ops trace data
(`OpsSummary`/`Trace.meta.envelope`) if it's worth quantifying precisely.

- [x] Real numbers measured and recorded here (not adjusted to fit the plan's aspirational number).
- [x] Every distiller's longest real snapshot confirmed < 150 tokens (unit test).
- [x] `pytest erp` green (1775 passed / 6 skipped, up from 1758/6 at T3.7 — 17 net new, all T3.8's).
