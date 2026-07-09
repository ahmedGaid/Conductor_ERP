# Phase 2 (Months 4–6) — AI Gateway, Model Routing & Caching

## Objectives

1. One policy-driven front door for every AI call: retries, failover, routing, budgets, caching
   live in ONE place instead of scattered per-caller.
2. Provider outage stops being a full outage: automatic failover chain + degraded-mode answers.
3. Each task class runs on the cheapest model that passes evals — routing is data-driven.
4. Repeat questions stop costing money: exact + semantic caches with correct invalidation.

## Architecture decisions

- **Gateway is a module, not a service.** `erp/assistant/gateway/` inside the monolith — no
  sidecar, no proxy process (customer-hosted, keep ops simple). `client.py` stays as the raw
  provider seam; the gateway wraps it and becomes the ONLY caller of `client.py`. All services
  (`ask`, `agent`, `digest`, …) migrate to `gateway.complete(...)` / `gateway.stream(...)`.
- **Task classes, not per-call model names.** Callers declare intent
  (`task="chat" | "agent_plan" | "agent_answer" | "extract" | "digest" | "suggest" | "judge" |
  "embed" | "rerank"`); a routing table in settings maps task → ordered model list
  (primary → fallbacks). Callers never name models again.
- **Failover is chain-walk with circuit breaker.** Breaker state in cache (Django cache
  framework, works with LocMem dev / Redis prod if present — no new dependency): open after N
  consecutive provider failures, half-open probe after cooldown.
- **Caching is two-tier and opt-in per task class.** Exact cache (hash of
  prompt_ref + rendered input + model) for deterministic/system tasks (digest, suggest);
  semantic cache (embedding cosine ≥ threshold on the question, scoped per user + knowledge
  version) ONLY for knowledge Q&A. Agent runs and write actions are NEVER cached.
- **Budgets are integers.** Token/cost budgets per request, per user per day, per tenant per
  month; stored/enforced in microcents, formatted at the edge (same discipline as `money.ts`).

## Decision points (ask user before dependent task)

- **Redis for breaker/budget/cache state in production?** Django cache abstraction is used either
  way; deployment choice only. Fallback: DB-backed cache table (works, slower).
- No other new dependencies.

## Success metrics (phase exit)

- Kill primary provider key in staging → chat still answers via fallback; user sees at most one
  designed "slower than usual" notice. Zero 500s.
- ≥ 99% of traces show a `routing` decision record; 100% of provider calls go through the gateway
  (grep-assert: no `client.complete` outside `gateway/`).
- Digest/suggest cache hit rate ≥ 60%; knowledge Q&A semantic hit rate ≥ 25% — measured in ops view.
- Eval pass rate (golden set) not below Phase 1 baseline on the routed (cheaper) models — proven
  per task class before flipping routing on.

---

## Tasks

### [ ] T2.1 — Gateway skeleton + call migration

- **Goal:** `gateway.complete/stream/embed` exists; every service calls it; behavior byte-identical.
- **Prereq:** Phase 1 done (traces record routing later).
- **Files:** create `erp/assistant/gateway/__init__.py`, `gateway/core.py`; modify `services/*.py`
  callers.
- **Steps:**
  1. `core.py`: `complete(task, messages, *, system=None, media=None, actor=None, **kw)` — v1 just
     resolves task → today's default model and delegates to `client.py` inside the traced seam
     (move the `trace_call` wrapping here so it lives in exactly one place).
  2. Same for `stream(...)` and `embed(...)`.
  3. Migrate every caller in `services/` and `tools.py`; delete their direct `client` imports.
  4. Add a lint-style test: AST/grep check that only `gateway/` imports `client` (guards the
     invariant forever).
- **Accept:** full `pytest erp/assistant` green with zero test edits except import paths; the
  invariant test fails if a service imports `client` (verified by negative test).
- **Output:** one front door.

### [ ] T2.2 — Retry policy + typed failures

- **Goal:** transient provider errors are retried predictably; permanent ones fail fast and typed.
- **Prereq:** T2.1.
- **Files:** create `gateway/retry.py`; modify `gateway/core.py`, `errors.py`.
- **Steps:**
  1. Classify provider exceptions per SDK: `retryable` (429, 5xx, connection, overloaded) vs
     `permanent` (400 schema, 401/403 auth, content-policy). Table-driven, unit-tested.
  2. Retry: max 2 retries, exponential backoff with jitter (0.5s base, cap 4s), only for
     retryable. Streaming: retry only if zero bytes were yielded (mid-stream handling is T2.6).
  3. Every retry recorded as a TraceStep (`kind="llm"`, `detail.retry=n`).
  4. Timeouts: per-task-class ceiling in settings (chat 60s, digest 120s, embed 10s…), enforced
     via SDK timeout params.
- **Accept:** tests: 429 → retried then succeeds; 401 → immediate typed failure, no retry;
  retries visible in trace; timeout maps to `error_class="timeout"`.
- **Output:** flaky networks stop paging anyone.

### [ ] T2.3 — Circuit breaker + failover chain

- **Goal:** a down provider is skipped automatically; recovery is automatic.
- **Prereq:** T2.2.
- **Files:** create `gateway/breaker.py`; modify `gateway/core.py`; settings routing table.
- **Steps:**
  1. Settings: `ASSISTANT_ROUTING = {task: ["provider:model", ...fallbacks]}` — v1 chain per task
     = today's model then the other two providers' nearest-capability model (document the choice
     per task in the settings comment).
  2. Breaker per provider (not per model): failure window 60s, open at 5 consecutive retryable
     failures, half-open probe after 30s. State via Django cache with atomic add/incr; degrade
     gracefully to "always closed" if cache backend lacks atomicity (LocMem dev).
  3. `core.py` walks the chain: skip open breakers; on exhausted chain raise
     `AllProvidersDown` → callers surface the existing designed error state (verify each feature
     has one; add missing ar/en strings).
  4. Trace `meta.routing = {chain, chosen, skipped:[{provider, reason}]}`.
- **Accept:** tests simulate provider A hard-down → calls flow to B, breaker opens after
  threshold, probe closes it after cooldown; ops view shows skipped providers.
- **Output:** provider outage ≠ product outage.

### [ ] T2.4 — Model routing by task class + eval-gated rollout

- **Goal:** cheaper models serve the task classes they provably handle.
- **Prereq:** T2.3, Phase 1 evals.
- **Files:** modify settings routing table; create `evals/routing_report.py` +
  `management/commands/eval_routing.py`.
- **Steps:**
  1. `eval_routing --task suggest --candidate groq:… --yes-live`: runs the golden subset for that
     feature against the candidate model, prints pass rate vs baseline model, writes
     `evals/results/routing_<task>_<model>.json`.
  2. Rule (documented in the settings comment): a candidate may become primary for a task class
     only if its eval pass rate ≥ baseline − 2 points AND cost/case ≤ 60% of baseline.
  3. Apply data-driven routing for the obvious wins first: `suggest`, `digest`, `judge` →
     cheapest passing tier; `agent_plan`/`extract` stay on the strongest model until Phase 5
     improves validation.
  4. Routing table changes are commits (reviewable), never runtime toggles.
- **Accept:** routing report command works offline against recordings for at least one task;
  settings table carries a per-line justification comment with the eval file name.
- **Output:** cost drops with proof, not hope.

### [ ] T2.5 — Exact-match response cache

- **Goal:** deterministic system tasks stop re-paying for identical inputs.
- **Prereq:** T2.1.
- **Files:** create `gateway/cache.py`; modify `gateway/core.py`; models migration
  (`assistant_responsecache` table).
- **Steps:**
  1. Key = sha256(task, prompt_ref, model, canonicalized messages, media hashes). Store: key,
     response JSON, created_at, hit_count, `input_version` (see step 3).
  2. Enabled per task class via settings allowlist — v1: `digest`, `suggest`, `judge` (eval
     re-grading). NEVER `chat`, `agent_*`, `extract`.
  3. Invalidation: TTL per task (digest 20h, suggest 6h, judge ∞) + explicit version bump hook
     (`cache.bump("suggest")`) callable from data-changing services later.
  4. Cache hits recorded as TraceStep `kind="llm"`, `detail.cache="exact"` with cost 0 — hit rate
     becomes visible in ops.
- **Accept:** tests: same input twice → one provider call; TTL expiry → recompute; disallowed
  task never caches; ops summary exposes hit rate.
- **Output:** recurring jobs approach zero marginal cost.

### [ ] T2.6 — Streaming resilience (mid-stream failover)

- **Goal:** a stream that dies mid-answer recovers without the user losing the turn.
- **Prereq:** T2.3.
- **Files:** modify `gateway/core.py` stream path, SSE view in `api/views.py`, frontend stream
  consumer in `apps/web/src/assistant/`.
- **Steps:**
  1. Gateway `stream()` catches mid-stream provider errors after ≥ 1 byte: emit a typed SSE event
     `retrying` and restart the turn on the next chain model with the SAME messages + an
     instruction to continue from the partial text (partial passed as assistant-prefix); if the
     restart also fails, emit `error` with the partial preserved.
  2. Frontend: on `retrying`, keep partial text, show the existing subtle streaming indicator +
     one calm inline notice (ar/en keys, blame-free: "المزوّد تأخر — نُكمل الإجابة"; wording via
     conductor-brand lexicon check).
  3. Trace: `meta.stream_recovered=true`, both attempts as steps.
- **Accept:** simulated mid-stream failure test at the gateway layer; manual smoke in ar (RTL)
  and en; i18n parity + tsc + gate03 green.
- **Output:** streams degrade gracefully, never blank.

### [ ] T2.7 — Token & cost budgets

- **Goal:** hard ceilings exist: per request, per user/day, per tenant/month.
- **Prereq:** T2.1, tracing cost data.
- **Files:** create `gateway/budgets.py`; models migration (`assistant_budget`,
  `assistant_spend_rollup`); modify `gateway/core.py`; ops endpoint.
- **Steps:**
  1. Budget table: scope (`request` defaults in settings; `user`, `org`), period, limit
     (microcents), action (`block` | `notify`). Defaults: request ≤ settings cap; user/day and
     org/month seeded generous (10× observed baseline from Phase 1) — budgets protect against
     runaway, not against usage.
  2. Rollup: increment per-user/org daily spend at trace write (atomic F() update on a
     date-keyed row — no queue needed).
  3. Enforcement in `core.py` pre-call: estimate cost (input tokens × price + max_tokens ×
     price); over-budget → typed `BudgetExceeded` → designed user message (ar/en) telling them
     exactly what to do (contact admin), never a raw error.
  4. Ops view: spend vs budget per scope.
- **Accept:** tests: request over cap blocked pre-call; user/day exhausted → block with typed
  error; rollup math correct across day boundary; notify-mode logs but allows.
- **Output:** cost runaway is structurally impossible.

### [ ] T2.8 — Semantic cache for knowledge Q&A

- **Goal:** near-duplicate knowledge questions reuse verified answers.
- **Prereq:** T2.5, existing `knowledge.py` embeddings.
- **Files:** create migration (`assistant_semanticcache`); modify `gateway/cache.py`,
  `services/ask.py`, `services/knowledge.py` (version hook).
- **Steps:**
  1. Row: question embedding, normalized question text, answer + citations JSON, actor scope
     (user id — answers are permission-scoped, NEVER shared across users in v1), knowledge
     version int, created_at, hit_count.
  2. Lookup: embed incoming question (already free via `embed_text`), cosine ≥ 0.95 against the
     same user's rows at current knowledge version → serve cached answer marked with the existing
     citation UI + a subtle "answered from recent history" affordance (ar/en). Below threshold →
     normal path, store on success.
  3. `knowledge.py` ingestion bumps knowledge version → all older cache rows dead (version
     mismatch, purged by the weekly report command).
  4. Settings kill-switch `ASSISTANT_SEMANTIC_CACHE=False` default ON in dev, decided per deploy.
  5. Cosine scan in Python over the user's rows (bounded — cap 500/user, LRU eviction). Note in
     code: migrates to pgvector index in Phase 3 (T3.1) — keep the interface, swap the scan.
- **Accept:** tests: paraphrase within threshold hits; other user never hits; ingestion bump
  invalidates; kill-switch bypasses. Eval: run citation golden cases through the cache path —
  groundedness unchanged.
- **Output:** popular questions answer instantly and free.

### [ ] T2.9 — Degraded mode + status surface (phase acceptance)

- **Goal:** the system tells users the truth about AI health, calmly; phase signed off.
- **Prereq:** all above.
- **Files:** modify `/api/assistant/status`, frontend panel status affordance; phase checklist.
- **Steps:**
  1. Extend status endpoint: `mode: full | degraded | down` derived from breaker states +
     budgets; panel shows the existing calm indicator with a designed degraded notice (ar/en).
  2. Staging drill (user runs, documented script): revoke primary key → verify failover, ops
     traces, user experience; restore; write results into the phase acceptance section below.
  3. Re-run full golden evals through the gateway (offline) — pass rate ≥ Phase 1 baseline.
  4. Update BASELINE.md with Phase 2 columns (hit rates, failover drill date).
- **Accept:** drill documented; all task boxes checked; gates green; rename file `_done`.
- **Output:** Phase 3 builds on a routed, cached, budgeted, honest gateway.
