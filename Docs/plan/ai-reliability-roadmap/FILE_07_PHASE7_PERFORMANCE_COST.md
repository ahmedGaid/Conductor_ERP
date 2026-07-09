# Phase 7 (Months 19–21) — Performance, Scalability & Cost

## Objectives

1. Latency gets budgets and the budgets get met: TTFT p95 ≤ 1.5s chat, agent first-step ≤ 3s.
2. The AI layer survives realistic concurrency (SSE fan-out, ingestion bursts, digest fan-out)
   with load tests that run on demand, not incidents that run on Sundays.
3. Cost per assisted conversation drops ≥ 50% vs Phase 1 baseline — via measured prompt diet,
   cache tuning, and routing tuning, each proven by the eval harness before it ships.
4. Data growth is governed: trace/conversation/embedding tables get retention, partitioning
   where warranted, and index discipline.

## Architecture decisions

- **Optimize from traces, not intuition.** Every task here starts by reading Phase 1–6 trace
  aggregates; the trace `meta` (ttft, envelope composition, routing, cache flags) is the profiler.
  No optimization lands without a before/after number from the same query.
- **Async by queue where a queue exists, by command where it doesn't.** Digest/ingestion/eval
  workloads already run via management commands + cron; keep that unless measured contention
  demands a real queue — adding Celery/RQ is a listed decision point, not a default.
- **Load testing is code in the repo:** `scripts/loadtest/` scenarios runnable against staging.
  Tool choice is a decision point (k6 preferred, external binary, no pip dep; fallback: a
  Python asyncio/httpx script — zero new deps).
- **Retention over partitioning until proven:** traces get a purge policy first (T6.4's command,
  now scheduled); native Postgres partitioning only if the traces table exceeds ~10M rows or the
  ops queries measurably degrade — the task carries the threshold check.
- **Prompt diet is an eval-gated refactor:** shrinking prompts/envelopes is only "done" when the
  golden pass rate holds. Tokens saved at quality cost are a regression, not a saving.

## Decision points

- **k6 binary for load tests** (T7.4) — external tool, staging only. Fallback: asyncio script.
- **Real queue (Celery/RQ + Redis)** (T7.3) — ONLY if measurements show cron/command contention.
- **Postgres partitioning** (T7.6) — only past the documented thresholds.

## Success metrics (phase exit)

- Chat TTFT p95 ≤ 1.5s; ask p95 ≤ 2.5s end-to-end; agent first-plan-step ≤ 3s (7-day trace window).
- Load test: 100 concurrent SSE chats + background ingestion on staging-sized hardware: error
  rate < 1%, TTFT p95 degradation ≤ 2×, zero worker starvation of interactive traffic.
- Cost per assisted conversation ≤ 50% of Phase 1 baseline at ≥ baseline eval pass rate.
- All AI tables have retention or an explicit "grows with business data" exemption note.

---

## Tasks

### [ ] T7.1 — Latency budget definition + measurement hardening

- **Goal:** per-endpoint latency budgets exist; traces measure every component of them.
- **Prereq:** Phase 6 done.
- **Files:** create `Docs/ops/ai-latency-budgets.md`; modify `services/tracing.py` (fill gaps).
- **Steps:**
  1. Budget table per feature: queue-to-first-byte, envelope build, guardrail time, provider
     TTFT, tool time — with p50/p95 targets summing to the top-level SLO. Derived from actual
     Phase 1–6 trace percentiles (query them; put the query in the doc).
  2. Trace gaps: ensure envelope build time and guardrail total are recorded (`meta.envelope_ms`,
     already-stepped guardrails summed) — add where missing.
  3. Ops view: budget-vs-actual bars per feature (reuse T1.8 page; one new tile row).
- **Accept:** doc committed with real numbers; ops tile renders; every budget component visible
  in a sample trace.
- **Output:** slowness gets a location, not a shrug.

### [ ] T7.2 — Envelope & prompt diet (eval-gated)

- **Goal:** median prompt tokens per feature cut ≥ 30% from current, quality flat.
- **Prereq:** T7.1 (numbers), Phase 3 envelope manager.
- **Files:** prompts (registry bumps), `services/envelope.py` shares, distillers (T3.8 registry).
- **Steps:**
  1. Query traces: rank envelope sections by median tokens per feature. Attack the top 3:
     (a) prompt templates — remove instruction redundancy across system+persona (diff-reviewed,
     version-bumped); (b) retrieval — test top-3 vs top-5 chunks on the retrieval+golden suites;
     (c) history — tighten T3.7 trigger (summarize earlier).
  2. Each change: run full golden evals offline; ship only at pass rate ≥ baseline − 1 point;
     record token delta + eval delta pairs in `evals/results/diet_<change>.json`.
  3. Distill two more high-traffic page types (extend T3.8 registry) based on trace frequency.
- **Accept:** trace-measured median prompt tokens −30% per targeted feature; eval evidence files
  committed; no golden regression.
- **Output:** the same answers for two-thirds of the tokens.

### [ ] T7.3 — Interactive/background workload isolation

- **Goal:** background AI work can never starve interactive chat.
- **Prereq:** T7.1.
- **Files:** `gateway/core.py` (priority classes), background commands (throttles).
- **Steps:**
  1. Gateway priority classes: `interactive` (chat/ask/agent) vs `background` (digest, ingestion,
     evals, summaries). Background calls: bounded in-process concurrency (semaphore, settings
     cap), token-bucket pacing, and they yield on breaker half-open states (interactive probes
     first).
  2. Provider rate-limit headroom: background pauses when recent 429 rate > threshold
     (interactive keeps priority through the retry policy).
  3. Measure: run a full re-ingest + digest fan-out while replaying 20 chat requests (script);
     chat TTFT p95 must stay within 1.5× idle baseline. If cron/command contention (not provider
     limits) is the bottleneck → present the queue decision point with the numbers; else record
     "no queue needed" with the numbers.
- **Accept:** isolation test script committed + passing numbers documented; semaphore/pacing
  unit tests.
- **Output:** nightly jobs stop taxing the human at the keyboard.

### [ ] T7.4 — Load-test scenarios + fixes

- **Goal:** repeatable load tests exist; findings fixed to the phase metric.
- **Prereq:** T7.3; decision point answered (k6 or asyncio fallback).
- **Files:** create `scripts/loadtest/` (scenarios + README with run instructions + hardware
  assumptions).
- **Steps:**
  1. Scenarios: (a) 100 concurrent SSE chats (provider monkeypatched to a local stub with
     realistic token pacing — load tests exercise OUR stack, not the provider's); (b) burst: 20
     simultaneous agent runs with parallel tools; (c) mixed: (a) + re-ingest + digest fan-out.
  2. Stub provider: tiny local HTTP server in the scripts dir streaming canned tokens at
     configurable rate — also useful for dev.
  3. Run on staging; capture: error rate, TTFT distribution, DB connection peak, memory. Fix
     what fails the phase metric (likely candidates: SSE connection handling, DB connections in
     parallel tool threads (T5.4), missing indexes) — each fix its own commit with before/after.
  4. README documents how to re-run in one command.
- **Accept:** all three scenarios pass the phase metric on staging; results file committed.
- **Output:** capacity is a known number with a re-run button.

### [ ] T7.5 — Cache & routing tuning pass

- **Goal:** cache hit rates and routing table re-tuned on 6+ months of real data.
- **Prereq:** T7.1.
- **Files:** settings (routing table, cache TTLs, semantic threshold); tuning evidence files.
- **Steps:**
  1. Query traces: hit rates per cache tier, near-miss distribution for the semantic cache
     (similarity 0.90–0.95 band size). If the band is fat, eval a threshold drop to 0.93 against
     the citation golden set (groundedness must hold ≥ 95%) — evidence file either way.
  2. Routing: re-run T2.4's `eval_routing` for `chat` and `agent_answer` with the current
     cheapest tier (models improved in a year); promote per the T2.4 rule only.
  3. Exact-cache allowlist: any new deterministic task classes since Phase 2 (rerank, verify,
     judge) confirmed cached with sensible TTLs.
  4. Update cost dashboards; record cost-per-conversation trend in BASELINE.md.
- **Accept:** evidence files for every threshold/routing change; cost metric trending to target;
  no eval regression.
- **Output:** the cost curve bends with receipts.

### [ ] T7.6 — Data lifecycle: retention, indexes, growth

- **Goal:** AI tables can't grow unbounded; hot queries stay indexed.
- **Prereq:** T7.1.
- **Files:** migration(s); `management/commands/` scheduling docs; `Docs/ops/ai-data-lifecycle.md`.
- **Steps:**
  1. Retention schedule (documented + scheduled via the existing cron pattern): traces 180d
     (T6.4 command), eval results 2y, semantic cache rows 30d or version-dead, superseded
     memories 1y, orphaned attachment extracts 90d. Conversations: user-owned, never auto-purged
     (exemption note).
  2. Index audit: EXPLAIN the ops summary + trace list + conversation search queries at current
     scale ×10 (synthetic fill script in scratch, not committed data); add missing indexes as one
     migration.
  3. Partitioning check: row counts vs the documented thresholds → implement only if exceeded;
     otherwise record the check + thresholds in the lifecycle doc for the next check (Phase 8).
  4. Embedding cleanup deferred from T3.1: drop the legacy JSON embedding column now that
     pgvector has run two phases (skip if flag was never enabled — note it).
- **Accept:** lifecycle doc committed; purge commands scheduled + tested; EXPLAIN evidence for
  index changes; migrations reversible.
- **Output:** the AI layer ages without sagging.

### [ ] T7.7 — Perceived-performance polish + phase acceptance

- **Goal:** the fast system also FEELS fast; phase signed off.
- **Prereq:** T7.2, T7.4; read `Docs/plan/perceived-performance-plan.md` (align, don't duplicate).
- **Files:** frontend assistant panel; phase record.
- **Steps:**
  1. From trace data, find the 3 worst felt-latency moments (likely: agent plan gap before first
     step, knowledge Q&A pre-stream silence, attachment processing). Apply the perceived-perf
     plan's primitives: optimistic skeleton for plan steps, immediate "searching your documents…"
     status line (ar/en, designed, not a spinner), attachment progress from real extract stages.
  2. Honour reduced-motion; settled motion tokens only; brand-feel checklist on touched surfaces.
  3. Phase acceptance: all metrics at top verified with trace queries; BASELINE.md updated
     (latency table, cost per conversation, load-test date); boxes checked; rename `_done`.
- **Accept:** i18n parity, tsc, gate03 green; acceptance recorded with numbers.
- **Output:** speed users feel, spend the finance team feels.
