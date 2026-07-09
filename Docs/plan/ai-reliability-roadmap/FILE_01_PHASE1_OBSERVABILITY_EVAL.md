# Phase 1 (Months 1–3) — Observability, Evaluation & Prompt Registry

## Objectives

1. Every LLM call, agent step, and tool call leaves a trace: model, tokens, latency, cost, outcome.
2. A golden dataset + offline eval harness exists and runs in CI — quality becomes a number.
3. System prompts are versioned artifacts, not inline strings — every trace records which prompt
   version produced it.
4. A weekly quality/cost report exists so regressions are seen within days, not months.

## Architecture decisions (made here, consumed by all later phases)

- **Traces live in Postgres**, same DB, own tables (`assistant_trace`, `assistant_tracestep`).
  No external APM/observability SaaS — customer-hosted constraint holds. Retention handled in
  Phase 7 (partitioning); for now a simple purge command.
- **Tracing is a seam, not a rewrite:** one `traced()` context manager wrapped around the existing
  `client.py` call sites. If tracing itself fails, the AI call must still succeed (same philosophy
  as `embed_text`'s try/except).
- **Evals are offline-first:** recorded fixtures + deterministic graders run in pytest with zero
  live API calls (CI-safe). Live "shadow evals" against real providers are a separate opt-in
  management command, never CI.
- **Grading ladder:** (1) exact/schema checks where possible → (2) programmatic assertions
  (numbers, citations present) → (3) LLM-as-judge only for free text, always with a calibration
  set. Cheapest sufficient grader wins.
- **Prompt registry is files + hash, not a DB:** prompts live in `erp/assistant/prompts/*.md`
  with YAML frontmatter (id, version, changelog). Loader computes content hash; traces store
  `prompt_id@version#hash`. Git is the version history — no admin UI needed.

## Decision points (ask user before the task that needs them)

- None. Phase 1 is deliberately zero-new-dependency. Token counting uses provider-returned usage
  fields (all three providers return them); estimation fallback is `len(text) // 3` (documented
  as heuristic for Arabic-heavy text).

## Success metrics (phase exit)

- 100% of LLM calls traced (assert: no code path calls providers outside the traced seam).
- Golden set ≥ 150 cases (≥ 60% Arabic), eval harness runs in CI < 90s, baseline scores recorded
  in `Docs/plan/ai-reliability-roadmap/BASELINE.md`.
- Cost per call visible per day/model/feature in the ops view.

---

## Tasks

### [x] T1.1 — Trace models + migration

- **Goal:** Postgres tables exist for traces and trace steps.
- **Prereq:** none (phase start).
- **Files:** read `erp/assistant/models.py`; create migration; modify `models.py`.
- **Steps:**
  1. Add `Trace` model: `id (uuid pk)`, `created_at`, `actor` (FK user, nullable for system jobs),
     `feature` (choices: `chat`, `ask`, `agent`, `extract`, `digest`, `suggest`, `embed`, `eval`),
     `conversation_id` (nullable FK), `provider`, `model`, `prompt_ref` (char, blank),
     `input_tokens`, `output_tokens`, `latency_ms`, `cost_microcents` (bigint, integer minor
     units — same money discipline as the ERP), `status` (choices: `ok`, `error`, `timeout`,
     `cancelled`, `guardrail_blocked`), `error_class` (char, blank), `meta` (JSONField, default dict).
  2. Add `TraceStep` model: FK to Trace, `seq` (int), `kind` (choices: `llm`, `tool`, `retrieval`,
     `guardrail`, `validation`), `name` (tool/step name), `latency_ms`, `ok` (bool),
     `detail` (JSONField — arguments/result sizes only, never full payloads).
  3. Indexes: `Trace(created_at)`, `Trace(feature, created_at)`, `TraceStep(trace, seq)`.
  4. `makemigrations assistant` + `migrate`.
- **Accept:** `pytest erp/assistant` green; `python manage.py migrate` idempotent; model docstring
  states payload policy (sizes not contents).
- **Output:** empty trace tables, ready for the seam.

### [x] T1.2 — Tracing seam around client.py

- **Goal:** every provider call records a Trace row without changing any caller's behavior.
- **Prereq:** T1.1.
- **Files:** read `erp/assistant/client.py`; create `erp/assistant/services/tracing.py`; modify
  `client.py` call sites minimally.
- **Steps:**
  1. In `tracing.py` implement `trace_call(feature, *, actor=None, conversation_id=None,
     prompt_ref="")` context manager: records start time; on exit writes Trace with usage fields
     the caller sets on a mutable `TraceHandle` object (`handle.usage(input_tokens=…,
     output_tokens=…)`, `handle.step(kind=…, name=…, ok=…, detail=…)`).
  2. Entire write wrapped in try/except-log — tracing failure must never fail the AI call.
  3. Wrap `complete_json`, `complete_stream` (record TTFT in `meta.ttft_ms` and total latency),
     `groq_chat`, `embed_text`. Streaming: accumulate output tokens from final usage event; if
     provider omits usage, apply the documented `len//3` heuristic and set `meta.tokens_estimated=true`.
  4. Thread `feature`/`actor` down from the existing callers (`ask.py`, `agent.py`, `digest.py`,
     `extraction.py`, `suggestions.py`, `knowledge.py`) — parameter with default so untouched
     callers still work.
  5. Cost: add `PRICING` dict in `tracing.py` mapping model id → (input, output) microcents per
     1K tokens for the three `DEFAULT_MODELS` + any model in settings; unknown model → cost 0 +
     `meta.cost_unknown=true`.
- **Accept:** new test `tests/test_tracing.py`: monkeypatched provider call produces exactly one
  Trace with correct feature/tokens/cost; a raising tracer does not break the call; streaming
  path records ttft. `pytest erp/assistant` green.
- **Output:** every AI call self-reports.

### [x] T1.3 — Agent-step and tool-call tracing

- **Goal:** agent runs produce a full step tree (plan → tool calls → answer) under one Trace.
- **Prereq:** T1.2.
- **Files:** read `erp/assistant/services/agent.py`, `erp/assistant/tools.py`; modify both.
- **Steps:**
  1. Agent loop opens one `trace_call(feature="agent", …)` for the whole run; each iteration adds
     TraceSteps: `llm` (per model call), `tool` (name, ok, latency, result row-count in detail —
     never result rows), `validation` when arguments are rejected.
  2. Tool executor in `tools.py` gets an optional `handle` parameter (default None → no-op) so
     tools stay independently callable.
  3. Record the run's stop reason in `Trace.meta.stop` (`answered`, `step_budget`, `error`,
     `cancelled`).
- **Accept:** `tests/test_tracing.py` extended: a monkeypatched 2-tool agent run yields 1 Trace +
  ≥ 4 TraceSteps in order; detail contains sizes not rows. Gates green.
- **Output:** agent runs are replayable as step trees.

### [x] T1.4 — Prompt registry

- **Goal:** all system prompts are versioned files; traces record `prompt_ref`.
- **Prereq:** T1.2.
- **Files:** create `erp/assistant/prompts/` + `erp/assistant/services/prompt_registry.py`; modify
  `services/context.py`, `services/ask.py`, `services/agent.py`, `services/digest.py`,
  `services/suggestions.py`, `services/extraction.py`.
- **Steps:**
  1. Move every inline system-prompt string into `prompts/<id>.md` with frontmatter:
     `id`, `version` (semver, start 1.0.0), `changelog` list. Body is the prompt template with
     `{placeholders}` exactly as today — no wording changes in this task (diff must show
     move-only; behavior identical).
  2. `prompt_registry.py`: `get(id) -> Prompt` (cached at import), `Prompt.render(**kw)`,
     `Prompt.ref` = `"{id}@{version}#{sha256[:8]}"`. Missing placeholder → raise (fail loud in
     tests, never silently ship a half-rendered prompt).
  3. Pass `prompt_ref` into `trace_call` at every call site.
  4. Add `tests/test_prompt_registry.py`: registry loads all files, refs stable, unknown id raises,
     render with missing key raises.
- **Accept:** grep shows no multi-line system prompt literals left in `services/` (short dynamic
  fragments assembled by `context.py` are allowed — the *template* is what's registered);
  `pytest erp/assistant` green; ask/agent smoke behavior unchanged (existing tests untouched and green).
- **Output:** prompts are diffable, versioned artifacts.

### [x] T1.5 — Golden dataset v1

- **Goal:** ≥ 150 graded eval cases covering real ERP flows, ar + en, stored as fixtures.
- **Prereq:** T1.4 (cases pin prompt refs).
- **Files:** create `erp/assistant/evals/` package: `__init__.py`, `datasets/golden_v1.jsonl`,
  `datasets/README.md`.
- **Steps:**
  1. Case schema (one JSON per line): `id`, `lang` (`ar`/`en`), `feature` (`ask`/`agent`/`extract`/
     `suggest`), `input` (message + optional context envelope fields), `fixtures` (tool name →
     canned result, so evals never hit the DB or a provider), `expected` — one of:
     `schema` (JSON-schema the output must match), `contains` (list of required substrings, e.g.
     the correct total), `citations` (required source ids), `refusal: true` (must decline),
     `judge` (rubric string — graded in T1.7 only).
  2. Author cases from the modules the assistant already serves: purchasing (PO status, supplier
     balances), inventory (stock levels, below-reorder lists), accounting (trial balance
     questions, VAT), CRM, workflows, knowledge-base Q&A with citations, refusal cases
     (out-of-scope asks, other-user data), Arabic number/date formatting cases.
     Minimum split: ≥ 90 Arabic, ≥ 60 English; ≥ 20 refusal; ≥ 20 citation.
  3. `datasets/README.md`: schema doc + rule "never edit a shipped case's `expected` to make a
     failing model pass — add a new case or bump dataset version".
- **Accept:** loader test validates every line against the schema; counts assert the minimum
  split; ids unique.
- **Output:** the quality yardstick every later phase is measured against.

### [x] T1.6 — Offline eval runner

- **Goal:** `manage.py run_evals` + pytest marker grade the golden set with zero network.
- **Prereq:** T1.5.
- **Files:** create `erp/assistant/evals/runner.py`, `erp/assistant/evals/graders.py`,
  `erp/assistant/management/commands/run_evals.py`, `erp/assistant/tests/test_evals_smoke.py`.
- **Steps:**
  1. `runner.py`: for each case, monkeypatch the client seam with a **recorded-response player**
     (responses recorded once by a human-run command, stored per case under
     `evals/recordings/<case_id>.json`) and the tool layer with the case's `fixtures`; execute the
     feature's real service function (`ask`, agent loop, …); collect output.
  2. `graders.py`: implement `schema`, `contains`, `citations`, `refusal` graders (deterministic,
     pure functions). `judge` cases are skipped with status `needs_judge` until T1.7.
  3. Command prints a scoreboard (per feature, per lang) and writes
     `evals/results/<date>.json`; exits non-zero if pass rate < `--min` (default 0).
  4. Also add `record_evals` management command (live calls, dev-only, writes recordings) —
     guarded by `ASSISTANT_ENABLED` and an explicit `--yes-live` flag.
  5. `test_evals_smoke.py`: runs the runner over cases that have recordings; marker
     `@pytest.mark.evals`; CI keeps it green but non-blocking threshold for now.
- **Accept:** `python manage.py run_evals` completes < 90s offline; smoke test green; a case with
  a deliberately wrong recording fails its grader (negative test included).
- **Output:** quality is a command away.

### [ ] T1.7 — LLM-as-judge grader + calibration

- **Goal:** free-text answers get graded by a judge model, and the judge itself is calibrated.
- **Prereq:** T1.6.
- **Files:** modify `evals/graders.py`; create `evals/datasets/calibration_v1.jsonl`,
  `prompts/eval_judge.md`.
- **Steps:**
  1. Judge prompt (registered in the prompt registry): rubric + case input + answer → JSON
     `{pass: bool, reason: str}`. Judge model = the cheapest tier (Gemini Flash / Groq), never the
     model under test (cross-provider judging when possible).
  2. Calibration set: 30 answer/verdict pairs hand-labeled (15 ar / 15 en, half pass half fail).
     `manage.py calibrate_judge` (live, `--yes-live`) reports judge agreement; required ≥ 90%
     before `judge` grades count. Store the latest agreement score in
     `evals/results/judge_calibration.json`.
  3. Judge calls run through the traced seam with `feature="eval"` so eval spend is visible and
     separable.
- **Accept:** offline path: judge grader unit-tested against recorded judge outputs; calibration
  command exists and refuses to run without `--yes-live`.
- **Output:** free-text quality measurable without a human in the loop each run.

### [ ] T1.8 — Ops view: traces, cost, quality

- **Goal:** an admin-only page answers "what did the AI do today, what did it cost, is it healthy".
- **Prereq:** T1.2, T1.6.
- **Files:** create `erp/assistant/api/ops.py` (+ url); frontend
  `apps/web/src/pages/assistant/OpsPage.tsx` + route (admin-gated); `ar.json`/`en.json` keys.
- **Steps:**
  1. Endpoint `GET /api/assistant/ops/summary?days=7`: per-day per-feature counts, error rate,
     p50/p95 latency + TTFT, tokens, cost (integer microcents; format at the edge), top error
     classes, latest eval scoreboard (read from `evals/results/`).
  2. Endpoint `GET /api/assistant/ops/traces?…` paginated trace list with step drill-down.
  3. UI: one calm page — summary tiles, day chart, trace table with expandable steps. Tokens-only
     CSS, logical properties, designed empty state ("no AI activity yet"), both languages. No new
     chart dependency — reuse whatever chart primitive reports/BI already use; if none exists,
     plain table + inline SVG sparkline built in-house.
  4. Permission: staff/admin only; traces show actor names only to admins.
- **Accept:** i18n parity + tsc + gate03 green; endpoint tests for aggregation math; RBAC test
  (non-admin → 403).
- **Output:** the AI stops being a black box.

### [ ] T1.9 — Error taxonomy + weekly report

- **Goal:** failures are classified, counted, and reported weekly.
- **Prereq:** T1.8.
- **Files:** modify `services/tracing.py`, `erp/assistant/errors.py`; create
  `management/commands/ai_weekly_report.py`.
- **Steps:**
  1. Extend `errors.py` with a closed taxonomy: `provider_error`, `timeout`, `rate_limited`,
     `tool_error`, `validation_failed`, `guardrail_blocked`, `context_overflow`, `cancelled`,
     `unknown`. Map exceptions at the seam → `Trace.error_class`.
  2. Weekly command: aggregates last 7 days (volume, cost, error mix, eval delta vs previous
     run), writes `Docs/ops/ai-week-<isoweek>.md`, and reuses the existing digest email path
     (`send_ai_digests` pattern) to notify admins. Schedule note in the command docstring
     (cron — same mechanism as existing digests; no new scheduler).
- **Accept:** command test with seeded traces produces a correct report file; unknown exception
  lands in `unknown`, never crashes the seam.
- **Output:** regressions surface within a week, automatically.

### [ ] T1.10 — Baseline capture + CI wiring (phase acceptance)

- **Goal:** baseline numbers recorded; evals wired into CI; phase signed off.
- **Prereq:** all above.
- **Steps:**
  1. Run `record_evals` + `run_evals` + `calibrate_judge` live once (user runs it — needs keys).
  2. Write `Docs/plan/ai-reliability-roadmap/BASELINE.md`: table of the cross-cutting metrics from
     FILE_00 with measured values + date + prompt refs in force.
  3. Add eval smoke to the CI/gate script chain as **non-blocking** with threshold = baseline − 5
     points (becomes blocking in Phase 8).
  4. Phase acceptance checklist: all tasks checked, all gates green, ops page reviewed in ar + en,
     BASELINE.md committed.
- **Accept:** BASELINE.md exists with real numbers; rename this file `_done`.
- **Output:** Phase 2 can prove it made things better, not different.
