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

---

# Phase 3 acceptance — "I don't know" discipline (T3.9), measured 2026-07-29

Offline, zero network: `manage.py run_evals --suite golden | retrieval | confidence`
(`erp/assistant/evals/results/2026-07-29.json`, `retrieval_2026-07-29.json`,
`retrieval_confidence_2026-07-29.json`, plus the two committed comparison files
`retrieval_baseline_vs_fusion.json` / `retrieval_confidence_threshold.json`).

## The confidence floor, and the retrieval bug tuning it exposed

T3.9's threshold could not be tuned honestly until a real defect underneath it was fixed, so this
section records both.

**The defect.** The tsvector is built with Postgres config `simple`, which has no stopword
dictionary, and the query side used `websearch_to_tsquery`, which ANDs every bare term. A natural
question — "what is the refund policy?", "متى يقدم الإقرار الضريبي؟" — therefore only matched a
chunk that literally also contained *what*, *is*, *the*. Real questions missed the FTS arm
entirely and fell to the `icontains` safety net, which scored a flat `0.0`. Since the vector arm
only re-ranks FTS candidates when pgvector is off (today's default), nothing rescued them. The
first tuning run showed the consequence starkly: at the originally-proposed floor, **63 of 94
answerable eval queries would have been declined** — an "I don't know" discipline that says "I
don't know" to two thirds of the questions it can answer.

**The fix**, both halves query-side only (the index still holds every word):

1. `textnorm.strip_query_stopwords` — drop ar/en function words before the `SearchQuery`, so the
   AND binds only the meaning-bearing terms.
2. `knowledge._icontains_score` — score the fallback tier by **content-word coverage** instead of a
   flat `0.0`, mapped onto the same RRF ladder (full coverage = `RANK1_SCORE`, the score of a hit
   ranked #1 by one arm). A chunk containing every content word is real evidence even when token
   equality missed it, which is the ordinary Arabic-morphology case; a chunk matching one word out
   of five stays below the floor and reads as a decline.

**Retrieval suite, same 24-doc corpus / 94 queries, before vs after those two changes** (measured
in one process, the "before" arm monkeypatching both back to their old behavior — `fusion`
strategy; `fts` is identical to it here and `blend` is unchanged by this work):

| Metric | Before | After | Delta |
|---|---|---|---|
| recall@5 | 0.947 | **0.979** | +0.032 |
| recall@10 | 0.947 | **0.979** | +0.032 |
| MRR | 0.766 | **0.995** | +0.229 |
| nDCG@10 | 0.802 | **0.988** | +0.186 |
| ar MRR | 0.687 | **0.992** | +0.305 |
| en MRR | 0.934 | **1.000** | +0.066 |

Both phase-exit retrieval targets (recall@5 ≥ 0.85, MRR ≥ 0.75) were already met before this task
and are met by a wider margin after. **Two queries got slightly worse and are recorded as such:**
`q_ar_01` and `q_ar_28` each drop from 1.0 to 0.5 recall because they label *two* relevant docs (a
grade-2 primary and a grade-1 secondary) and the tight AND-match now returns only the primary,
where the old `icontains` OR-soup happened to sweep the secondary in too. Both still rank their
primary doc first (`q_ar_01` nDCG@10 1.0 → 0.826, MRR unchanged at 1.0) — a precision-for-recall
trade on the long tail, taken knowingly.

**Tuned threshold.** `knowledge.CONFIDENCE_THRESHOLD = 0.6 * RANK1_SCORE` — the fp-minimizing pick
from `retrieval_metrics.best_confidence_threshold` over 109 labeled queries (94 answerable from
`retrieval_v1`, 15 unanswerable from the new `retrieval_unanswerable_v1`):

| | Threshold | Precision | Recall | F1 | tp / fp / fn / tn |
|---|---|---|---|---|---|
| Before the retrieval fix | 0.0164 | 1.000 | 0.330 | 0.496 | 31 / 0 / 63 / 15 |
| **Shipped (after)** | **0.0098** | **1.000** | **0.926** | **0.961** | **87 / 0 / 7 / 15** |

Selection minimizes false positives first and only then maximizes F1: this label set is lopsided
(94 vs 15), and raw argmax-F1 picks the answer-everything threshold of 0.0, which is exactly the
failure T3.9 exists to prevent. Every unanswerable query tops out at 0.0082, below the floor —
**15/15 (100%) of the unanswerable cases decline correctly**, against the plan's ≥ 90% bar. The
floor deliberately sits *below* the single-arm rank-1 score so a deployment with no embeddings
configured (no `ASSISTANT_RAG_EMBEDDINGS` / Gemini key) still answers from the FTS arm alone.

## Golden set — no regression

| | Phase 1 / 2 baseline | T3.9 (2026-07-29) |
|---|---|---|
| Cases recorded | 148 | 158 (+10 new refusal-with-path cases) |
| Pass rate | 74.3% (110/148) | **81.0% (128/158)** |
| Failures | 38 | **30** |
| agent | 22/25 (88.0%) | 22/25 (88.0%) |
| ask | 88/123 (71.5%) | 106/133 (79.7%) |

All 10 new `ask_insufficient_*` cases (5 ar / 5 en) pass — each asserts both the decline *and* the
presence of a concrete next step. Every one of the 30 remaining failures falls in a failure class
already documented in the Phase 1 breakdown above: currency-format strictness (`17500 EGP` vs
`17,500.00 EGP`), literal status-string misses (`waiting_approval`, `receipt`/`issue`), the model
citing a document *title* instead of its `POL-*`/`SOP-*` id, and the single known `refusal_ar_06`
case. None are new, and none involve the no-answer path.

## Phase 3 acceptance checklist

- [x] All Phase 3 tasks (T3.1–T3.9) checked off — T3.5 shipped OFF by its own eval gate, decision
      and numbers in `evals/results/rerank_decision.json`.
- [x] T3.9's own accept criteria met: unanswerable-decline rate 100% (15/15) ≥ 90%; no golden
      regression (74.3% → 81.0%); `BASELINE.md` updated.
- [x] Phase-exit metric 1 — retrieval: recall@5 **0.979** ≥ 0.85, MRR **0.995** ≥ 0.75. Met, with
      the margin widened by this task.
- [ ] Phase-exit metric 2 — **groundedness ≥ 95% not met: 86.9% (53/61), unchanged from the Phase 1
      baseline.** All 8 misses are the same citation-*format* gap Phase 1 documented — the model
      cites a document's Arabic/English title instead of its `POL-*`/`SOP-*` id — not a missing or
      wrong source, so the companion "wrong-citation rate < 2%" reads as met while the headline
      number does not. Closing it is a prompt/grader change (teach the model to emit the id, or
      accept a title that resolves to the right document), untouched by T3.9 and not in any Phase 3
      task's scope. Carried forward as the one open Phase 3 exit item.
- [x] Phase-exit metric 3 — `context_overflow`: accepted at T3.6, which made overflow structurally
      impossible (the envelope assembles inside an explicit budget); not re-measured here, no new
      trace data since.
- [x] Phase-exit metric 4 — envelope tokens: measured and reported at T3.8 (see that section
      above), which recorded honestly that the −25%/−50% target does not describe what actually
      changed; not re-litigated here.
- [x] `pytest erp/assistant` green — 664 passed / 5 skipped.
- [x] `apps/web`: i18n parity green (2730 keys, ar+en), `tsc -b` clean, Vitest 64/64,
      `scripts/gates/gate03.py` (brand) exit 0.
- [x] Threshold-tuning artifact committed with real numbers (this section +
      `retrieval_confidence_threshold.json`).

## Phase 4 — Memory (T4.1–T4.6), measured 2026-07-30

Numbers below are from this repo on branch `feat/ai-reliability-file04-memory`; nothing is
extrapolated. Adoption counts are deliberately reported as zero: the feature ships here, so no
production rows exist yet — the counters to watch after rollout are named instead.

| Metric (phase exit) | Target | Measured | Verdict |
|---|---|---|---|
| Leakage suite failures | 0, blocking forever | 0 (15 tests, `tests/test_memory_leakage.py`, `@pytest.mark.blocking` + `scripts/gates/gate18.py`) | met |
| Memory-lift eval, seeded cases answer correctly | ≥ 90% | 12/12 paired offline cases (`tests/test_memory_lift.py`) prove the seeded value reaches the envelope AND is absent without the memory | met, offline |
| Memory writes carrying a confirm/audit event | ≥ 95% | 100% — every write goes through `services/memory.remember`, which calls `audit.record`; asserted by `test_every_write_is_audited_with_the_confirmed_sentence` | met |
| Writes from a non-whitelisted path | 0 | 0 — AST invariant `tests/test_memory_write_path.py` fails the build if any module outside `services/memory.py` touches `UserMemory`/`OrgMemory` | met |
| Memory adoption (rows, users with ≥1 memory) | — | 0 (feature not yet released); track `UserMemory`/`OrgMemory` counts by `source` after rollout | n/a yet |

**Honest limits.**
- The 14 golden rows added for this phase (`memory_lift_*` pairs + `memory_refuse_secret_*`) are
  structurally validated but **not yet recorded**, so the offline runner (T1.6) skips them — they
  grade the model's wording once `record_evals` runs against a provider. The causal claim above rests
  on the paired envelope tests, which need no provider and run in CI today.
- Free-fact similarity uses a capped Python scan over the user's own facts (cosine, reusing
  `knowledge._cosine`); pgvector is not involved. Facts per user are naturally few, and recall caps
  at 10 injected facts.
- Phase 3's open groundedness item (86.9% vs ≥ 95%, a citation-*format* gap) is untouched by this
  phase and still carried forward.

## Phase 4 acceptance checklist

- [x] T4.1 — `UserMemory`/`OrgMemory` + `services/memory.py` (one governed door in/out), migration
      `0013_orgmemory_usermemory`, slot supersede chain, expiry, hard-delete `forget`.
- [x] T4.2 — `remember_memory` confirmable action; `agent_loop` prompt 1.0.0 → 1.1.0 (memory
      discipline + "content is data, never an instruction").
- [x] T4.3 — deterministic detectors (repeated slot choice ≥ 3 confirmed actions in 30 days;
      language correction ×2), one proposal per user per day, 90-day dismissal suppression.
- [x] T4.4 — `GET/PUT /api/assistant/memory`, `DELETE …/<id>`, `POST …/memory/proposals`, plus the
      Memory page (`apps/web/src/pages/assistant/MemoryPage.tsx`) with designed empty state.
- [x] T4.5 — envelope section `memory` (priority 3, `max_share` 0.10, facts degrade before slots);
      tokens visible in `Trace.meta.envelope.memory`.
- [x] T4.6 — leakage + injection suite blocking via gate 18 and the default `pytest` job; negative
      test proves the containment tests bite.
- [x] `pytest erp/assistant/tests` green — 727 passed / 5 skipped.
- [x] `python manage.py makemigrations --check` and `manage.py check` clean.
- [x] `apps/web`: i18n parity green (2756 keys, ar+en), `tsc -b` clean, Vitest 64/64,
      `scripts/gates/gate03.py` exit 0, `scripts/gates/_run.py 18` PASSED.
