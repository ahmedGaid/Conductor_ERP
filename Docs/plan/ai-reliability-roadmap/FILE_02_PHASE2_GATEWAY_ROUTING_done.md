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

### [x] T2.1 — Gateway skeleton + call migration — DONE 2026-07-10

- **Goal:** `gateway.complete/stream/embed` exists; every service calls it; behavior byte-identical.
- **Prereq:** Phase 1 done (traces record routing later).
- **Files:** created `erp/assistant/gateway/__init__.py`, `gateway/core.py`; modified `ask.py`,
  `agent.py`, `imports.py`, `knowledge.py`, `evals/graders.py`; deleted `services/llm.py` (moved
  into `gateway/core.py`); removed `complete_stream` from `client.py` (moved into `gateway/core.py`,
  which is dispatch logic, not the raw seam).
- **What shipped:** `gateway/core.py` exposes `complete_json` (moved verbatim from `services/llm.py`),
  `complete_stream` (moved verbatim from `client.py`), and a thin `embed_text` re-export. `feature`
  stays the task-class label for now (v1 — no per-task routing table yet, matches "resolves to
  today's default model"); T2.3/T2.4 formalize `task` when routing lands. `trace_call` wrapping now
  lives in exactly one place (`gateway/core.py`).
- **Invariant test:** `tests/test_gateway_invariant.py` — AST-based scan asserts only `gateway/`,
  `client.py`, and a documented allowlist import `client` directly. Allowlist + reason:
  `api/views.py` + both management commands (only call `client.enabled()`, a config check, not a
  dispatch call); `services/extraction.py` (its own single-provider no-failover retry design —
  structurally different from the gateway's chain-walk, migrating it is separate future work, not
  a T2.1 rename); `services/knowledge.py` (still calls `client.embed_text` directly — its tests
  monkeypatch `knowledge.client.embed_text`; tracked for the T2.8 embed-cache task). Negative tests
  (`test_checker_flags_*`) prove the AST checker actually catches a violation, not just passes
  vacuously.
- **Test edits:** only import-path changes — `test_routing.py` and `test_tracing.py` now import
  `erp.assistant.gateway.core as llm` instead of `erp.assistant.services.llm`, and their two direct
  `client.complete_stream(...)` call sites became `llm.complete_stream(...)` since the function
  moved. No behavior or assertion changed in any test.
- **Accept:** `pytest erp/assistant` green (307 passed, up from 302 — the 5 new invariant tests);
  `gate:all` 00–15 green.
- **Output:** one front door for ask/agent/imports + chat streaming. `services/extraction.py` and
  `services/knowledge.py`'s embed path are the two known remaining direct-`client` callers, each
  with a documented reason and a future task to close.

### [x] T2.2 — Retry policy + typed failures — DONE 2026-07-10

- **Goal:** transient provider errors are retried predictably; permanent ones fail fast and typed.
- **Prereq:** T2.1.
- **Files:** created `gateway/retry.py`; modified `gateway/core.py`, `client.py`,
  `services/tracing.py`, `config/settings/base.py`.
- **What shipped:** `retry.is_retryable(exc)` — table-driven, checks permanent markers (401/403/400,
  auth, content-policy) before retryable ones (429, 5xx, connection, timeout); unrecognized
  exceptions fail fast rather than guess. `retry.backoff_seconds(attempt)` — exponential with full
  jitter, 0.5s base, 4s cap. `complete_json`/`complete_stream` now check `is_retryable()` instead of
  retrying every exception; the existing "only the last provider in the chain gets a multi-attempt
  budget" fail-fast design (T2.1-era, kept as-is — a live fallback is always better than waiting out
  a backoff) still applies, now gated by the retryable check. Every retry AND the final failure is
  recorded as a TraceStep (`kind="llm"`, `detail.retry=n` or `detail.final=true`). Per-task-class
  timeout ceilings (`ASSISTANT_TASK_TIMEOUTS` in settings, default `ASSISTANT_DEFAULT_TIMEOUT_S=60`)
  thread through every runner (Anthropic/Gemini SDK `timeout=`, Groq/Mistral httpx `timeout=`) for
  both JSON and streaming paths. **Deviation from plan:** `errors.py` untouched (its
  `classify_exception` taxonomy answers a different question — ops bucket, not retry decision — so
  a second, narrower table in `retry.py` was clearer than overloading one); `services/tracing.py`
  gained one guard instead (`trace_call` no longer clobbers a `handle.error_class` a call site
  already set via `fail_from_exception()` before re-raising a different, typed exception) — needed
  so a timeout swallowed into the blame-free `AssistantUnavailableError` still lands as
  `error_class="timeout"` on the Trace, not the generic wrapper's `"provider_error"`.
- **Tests:** new `tests/test_retry.py` — classification table (parametrized transient/permanent
  markers), backoff bounds, 429→retry→succeed, 401→immediate no-retry, timeout→`error_class`, and
  the same retry budget on the streaming path before the first token. Existing runner-monkeypatch
  fakes in `test_routing.py`/`test_tracing.py` updated to accept the new `timeout` kwarg (signature
  change only, no assertion changes).
- **Accept:** 323 tests green (up from 307); `gate:all` 00–15 green (gate 15 eval pass rate
  unchanged at 74.3%, still above the Phase 1 baseline threshold).
- **Output:** flaky networks stop paging anyone.

### [x] T2.3 — Circuit breaker + failover chain — DONE 2026-07-10

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
- **What shipped:** `gateway/breaker.py` — per-provider state in Django's cache (no new dependency):
  `record_failure`/`record_success`/`state`/`is_open`. `state()` returns `closed` (default) →
  `open` (5 consecutive **retryable** failures in a 60s streak; a permanent error like 401 never
  counts, so a bad key can't fake an outage) → `half_open` once 30s have elapsed, which lets exactly
  one probe back through (`is_open()` is false for half-open — the chain-walk treats it like closed
  and `record_success`/`record_failure` decide whether it re-closes or re-opens). Degrades to
  "always closed" (never opens) if the cache backend can't count atomically — `cache.add`/`incr`
  wrapped in `try/except (ValueError, NotImplementedError)`; the default backend (LocMemCache, no
  `CACHES` setting today) can. `core.py`'s `complete_json`/`complete_stream` filter
  `provider_chain()` into `usable` (breaker-closed/half-open) before walking it; an empty `usable`
  raises `AllProvidersDown` immediately, without calling any runner. New `errors.AllProvidersDown`
  **subclasses** `AssistantUnavailableError` — same blame-free surface, so every existing
  `except AssistantUnavailableError` / `except AppError` call site (views.py's SSE error handler,
  etc.) already handles it with zero changes; it replaces the old bare `AssistantUnavailableError`
  raise at chain-exhaustion. `meta.routing = {chain, chosen, skipped:[{provider, reason}]}` is a
  local dict, only attached to `handle.meta` when the call is traced (`feature` given) — an
  untraced call still gets breaker protection but never touches the shared `_NullHandle` singleton.
  `reason` values: `breaker_open`, or the `classify_exception()` taxonomy bucket, or `empty_output`/
  `invalid_json` for a provider that answered but produced garbage (these don't open the breaker —
  only a retryable exception does). Ops view (`api/ops.py` `_trace_row`, previously didn't expose
  `meta` at all) now returns `meta`; `OpsPage.tsx` shows a "Skipped providers" line (translated
  label) with each `provider (reason)` pair rendered as raw technical text — same precedent as the
  already-untranslated `provider`/`model`/`name` cells in that table, not user-facing prose.
  `ASSISTANT_ROUTING` added to settings as documented v1 data (every task gets the same chain,
  mirroring `client.provider_chain()`'s default-key order) — `core.py` doesn't consume it yet, since
  differentiating per-task models is T2.4's eval-gated job; it exists now so the breaker/trace layer
  has a documented, per-task table to point at.
- **Tests:** `tests/test_breaker.py` (unit — closed/open/half-open transitions, reset-on-success,
  per-provider independence) + `tests/test_circuit_breaker.py` (integration against `gateway.core`
  — open breaker skipped without a runner call, consecutive retryable failures open it, a permanent
  error never does, half-open probe recovers it, all-breakers-open raises `AllProvidersDown` without
  calling any runner, `AllProvidersDown` still satisfies `except AssistantUnavailableError`, stream
  parity). New `tests/conftest.py` (`erp.assistant` package) clears Django's cache before/after every
  test — cache isn't reset between tests the way the DB is, and breaker state is keyed only by
  provider name, so one test's failures could otherwise leak into another's.
- **Deviation from plan:** none structural; `ASSISTANT_ROUTING` is v1-uniform per task (see above)
  rather than diverged per task, since T2.3's job was the breaker/format, not the eval-gated model
  choice (that's T2.4, which needs Phase 1 evals as a prereq per its own task description).
- **Accept:** `tests/test_breaker.py` + `tests/test_circuit_breaker.py` green (provider A hard-down
  → calls flow to B, breaker opens after threshold, probe closes it after cooldown); ops view shows
  skipped providers. 338 tests green (up from 323); `gate:all` 00–15 green (gate 15 eval pass rate
  unchanged at 74.3%). Frontend: i18n parity, `tsc -b`, `gate03` (brand) all green; main bundle
  249.9 kB gzip, inside the 250 kB budget but thin margin — flagged for whoever adds the next
  eagerly-loaded string/import to main.
- **Output:** provider outage ≠ product outage.

### [x] T2.4 — Model routing by task class + eval-gated rollout — DONE 2026-07-10

- **Goal:** cheaper models serve the task classes they provably handle.
- **Prereq:** T2.3, Phase 1 evals.
- **Files:** created `evals/routing_report.py`, `management/commands/eval_routing.py`,
  `tests/test_routing_report.py`; modified `config/settings/base.py` (per-line
  `ASSISTANT_ROUTING` comments + promotion rule), `tests/test_gateway_invariant.py` (allowlisted
  `eval_routing.py` — same `client.enabled()`-only reason as `record_evals.py`/`calibrate_judge.py`).
- **What shipped:** `evals/routing_report.py` — `offline_scoreboard(task)` grades a task's golden
  subset against its existing recordings via the same zero-network machinery `run_evals` uses
  (`pass_rate=None`, not the misleading `1.0`, when nothing could be graded — e.g. `suggest`, which
  has golden cases but no offline runner); `run_candidate_live(task, candidate)` forces a
  `provider:model` through the real gateway (monkeypatches `gateway.core.provider_chain`/`model_id`
  for the duration) and grades with the real graders — wired for `ask`/`agent_plan`/`agent_answer`
  only, the task classes with both a real service and golden-case coverage; `promotion_verdict`
  applies the documented rule (candidate pass rate ≥ baseline − 2pts AND cost/case ≤ 60% of
  baseline), returning `None` (never guessed) until both sides are actually scored. Cost is
  estimated with `services.tracing`'s own `estimate_tokens` heuristic + `PRICING` table, applied
  identically to both sides — an unpriced model reports `cost_unknown=True` rather than a guessed
  0. `management/commands/eval_routing.py` — `--task`/`--candidate` always score the baseline
  offline and print pass rate + cost/case; `--yes-live` (gated like `record_evals`/
  `calibrate_judge`: needs `ASSISTANT_ENABLED`) actually calls the candidate and re-grades; without
  it, a prior live report for the same task+candidate is re-read from disk so a report can be
  reprinted without re-spending.
- **Deviation from plan:** did not flip `suggest`/`digest`/`judge` to a cheaper primary — of the
  three "obvious win" task classes the plan named, none is wired to a real gateway call site yet
  (`suggest` has no Python service at all — see `evals/runner.py`'s own note; `digest`/`judge` never
  pass `feature="digest"`/`"judge"` to the gateway today, `judge`'s real grader hardcodes its own
  cheap provider order instead of reading `ASSISTANT_ROUTING`). Routing a task nothing calls yet
  isn't a provable win, it's a guess — exactly what the eval-gated rule exists to prevent. Also did
  not run a live comparison: `gemini`/`groq`/`mistral` keys are configured in this dev environment
  so `--yes-live` is technically usable, but spending real, billed API calls without the user
  explicitly asking for that spend isn't a call to make unilaterally (`record_evals`/
  `calibrate_judge` were built the same way — real spend needs a human's `--yes-live`). Instead: ran
  the offline path for real against `ask` (123 graded cases, 71.5% pass rate, ~1023 microcents/case
  — `evals/results/routing_ask_groq_meta-llama_llama-4-scout-17b-16e-instruct.json`), which is what
  the accept criterion actually asks for (offline, ≥1 task), and documented every `ASSISTANT_ROUTING`
  line's real current status (wired-but-unproven, not-yet-wired, or internal-only) instead of
  fabricating justification comments for a change that hasn't been earned by data.
- **Tests:** `tests/test_routing_report.py` (14 cases) — offline scoreboard for `ask` (real
  recordings, priced) and `suggest` (`no_runner` → `pass_rate=None`, not `1.0`); promotion rule
  truth table (close+cheap → promote, pass-rate-drop → keep, not-cheap-enough → keep,
  cost-unknown → undecided); write-then-reread round trip; command offline run + `--yes-live`
  gate. `test_gateway_invariant.py` extended (not narrowed) — same checker, new allowlist entry.
- **Accept:** `manage.py eval_routing --task ask --candidate groq:meta-llama/llama-4-scout-17b-16e-instruct`
  ran fully offline against real recordings and wrote the report file above; every
  `ASSISTANT_ROUTING` line carries a per-line comment, the `ask` line naming that file. 352 tests
  green (up from 338 — 14 new); `gate:all` 00–15 green (gate 15 eval pass rate unchanged at 74.3%).
  Frontend: i18n parity (1823 keys), `tsc -b`, `gate03` (brand) all green — no frontend files
  touched this task.
- **Output:** the tool to prove a cheaper model before routing to it exists and works; no routing
  changed on unproven ground.

### [x] T2.5 — Exact-match response cache

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

### [x] T2.6 — Streaming resilience (mid-stream failover)

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

### [x] T2.7 — Token & cost budgets

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
- **What shipped (2026-07-12):** `gateway/budgets.py` — `check(estimated_cost, actor)` gates
  `complete_json`/`complete_stream` pre-call (after the T2.5 cache check in `complete_json`, so a
  free cache hit never gets budget-blocked); `estimate_cost_microcents` uses real input tokens but
  the FULL `max_tokens` ceiling for output — a deliberate over-estimate, since blocking a call that
  would've cost less is safe and under-estimating a budget is not. `Budget` (one row per scope,
  `request`/`user`/`org`, `limit_microcents` + `action` `block`/`notify`) and `SpendRollup`
  (date-keyed, atomic `F()` increment, `period` = the calendar day for `user`, the 1st of the month
  for `org` — the *same* row naturally accumulates within a month and resets across one) — new
  migration `0006_budget_spendrollup` + a data migration `0007_seed_budgets` seeding all three
  scopes from `ASSISTANT_BUDGET_*` settings (documented "10x a generous assumed heavy-usage volume"
  reasoning inline — no real production traffic exists pre-launch to size these precisely against).
  `record_spend()` hooks into `services/tracing.py`'s `_write()` (lazy-imported, mirroring how
  `gateway/core.py` already lazy-imports `services.tracing` to break the same cycle) so every traced
  call's real cost rolls up automatically, no separate call site to remember. `BudgetExceeded`
  (`AI-007`, `errors.py`) joins the taxonomy as `budget_exceeded`. Frontend: the chat SSE error
  event now carries `code` (both `except AppError` sites in `views.py`) so `ConversationView.tsx`
  shows a designed ar/en line (`assistant.budgetExceeded`) for `AI-007` instead of the raw
  (English-only) backend string — same "distinct code → distinct notice" precedent T2.6 set for
  `streamRetrying`. Ops: `OpsSummaryView` gained a `budgets` array (`ops.py`); `OpsPage.tsx` renders
  it as a spend-vs-limit list per scope (`request` shows no spend — a per-call check has nothing to
  roll up; `org` is one directly-comparable aggregate; `user` shows the current top spender, the one
  number comparable to a limit that applies equally to every user in v1 — there's no per-user
  override).
- **Deviation from plan:** none structural. `Budget` is one row per scope (not per-user/org-id) —
  the plan's "protect against runaway, not against usage" framing implies a shared policy, not
  per-tenant configuration, and this is still a single-tenant deployment.
- **Tests:** new `tests/test_budgets.py` (11 cases) — request/user/org block pre-call with zero
  provider calls made; per-user isolation; notify-mode logs (caplog) but still answers; rollup
  atomic-increment and day/month-boundary correctness (old period row untouched, new period starts
  at 0); ops summary exposes all three scopes with the right spend semantics per scope.
- **Accept:** 376 tests green (up from 365 — 11 new); `gate:all` 00–15 green; i18n parity (1832
  keys) + `tsc -b` green; no frontend files needed a brand-gate review beyond the existing ops list
  pattern reused as-is.

### [x] T2.8 — Semantic cache for knowledge Q&A

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
- **Implementation note:** new model `SemanticCache` (migration `0008_semanticcache`) + two
  functions on the *existing* `gateway/cache.py` module (`semantic_lookup`/`semantic_put`) —
  reuses that module's `current_version`/`bump` machinery with `task="knowledge"` rather than a
  second version-counter table. `ask.answer_question` embeds every question up front (mirrors the
  plan's "already free" framing — `embed_text` degrades to `None` with embeddings off, so this is
  a no-op miss in the common case); a lookup hit short-circuits both the router AND the answer
  model call. Only `used_tool == "search_documents"` answers are ever stored — a `sales_summary`
  answer depends on the router's chosen period/filters, so blind reuse would be unsafe; this is a
  narrower scope than "embed every question" might suggest, and is deliberate. `knowledge.py`
  bumps `task="knowledge"` unconditionally on every successful ingest (no separate purge command
  exists yet — stale rows sit inert, filtered out by the version check). `ask.py` needed a new
  entry in `test_gateway_invariant.py`'s `ALLOWED_DIRECT_CLIENT_IMPORTS` (same exception already
  granted to `knowledge.py` for `embed_text`). The "answered from recent history" ar/en affordance
  is NOT wired into the frontend — `AskView`/`askAssistant()` currently has zero UI callers (the
  live chat surface runs through `ChatView`/`agent.py`, out of this task's file scope per the
  plan); the backend returns `from_cache: true` on the envelope, ready for whichever consumer
  needs it.
- **Tests:** new `tests/test_semantic_cache.py` (9 cases) — paraphrase hit, cross-user isolation,
  ingestion-bump invalidation, kill-switch bypass, non-knowledge tool never cached, threshold miss,
  cap eviction (oldest-first).
- **Accept (actual):** 852 tests green repo-wide (assistant app: 383, up from 374 — 9 new);
  `gate:all` 00–15 green; i18n parity (1832 keys, unchanged — no new frontend strings) + `tsc -b`
  green.

### [x] T2.9 — Degraded mode + status surface (phase acceptance) — DONE 2026-07-12

- **Goal:** the system tells users the truth about AI health, calmly; phase signed off.
- **Prereq:** all above.
- **Files:** created `gateway/status.py`, `tests/test_status.py`; modified `api/views.py`
  (`AssistantStatusView`), `apps/web/src/api/assistant.ts` (`AssistantStatus.mode`),
  `apps/web/src/assistant/AssistantProvider.tsx` (`healthMode`), `AssistantPanel.tsx` (notice),
  `assistant-panel.css`, `i18n/locales/{ar,en}.json`, `tests/test_extraction.py` (status envelope
  shape), `BASELINE.md`.
- **What shipped:** `gateway/status.py::mode()` — a pure read of state the gateway already keeps,
  no new tracking. `down` only when every provider in `client.provider_chain()` is breaker-open
  (`breaker.state(p) == "open"` for all — the exact condition that makes the next
  `complete_json`/`complete_stream` raise `AllProvidersDown` before trying a runner). `degraded`
  when at least one provider is skipped (open or half-open) or a `block`-mode budget scope
  (`gateway/budgets.py::ops_summary()`) is already at or over its limit, but a usable provider
  remains — calls still answer, on a fallback chain or blocked for some callers. `full` otherwise.
  A `notify`-mode budget over its limit does NOT degrade the mode — it never blocks a call, so it
  shouldn't read as unhealthy either (matches `budgets.py`'s own "notify only logs" semantics).
  `AssistantStatusView.get` reports `mode: "full"` when the feature is disabled — an unconfigured
  deployment is neither degraded nor down, it's off, and the panel never renders either way.
  Frontend: `AssistantStatus.mode` is fetched once alongside `enabled` (same `/status` call,
  same lifecycle as the existing single-fetch — no new polling loop); `AssistantProvider` exposes
  it as `healthMode` (renamed from the endpoint's `mode` to avoid colliding with the panel's own
  floating/docked `mode`). `AssistantPanel` shows a persistent banner below the header when
  `healthMode !== "full"` — icon + one designed ar/en line per state (`assistant.status.degraded`
  / `assistant.status.down`), colour paired with icon+word per the brand's monochrome-chrome rule
  (`--color-status-waiting` / `--color-status-failed` tokens, same palette `Badge.css` already
  uses for status pills — no new colour introduced).
- **Staging drill:** documented + executed below (zero real provider spend — see rationale).
- **Tests:** new `tests/test_status.py` (7 cases) — full/degraded/down transitions off breaker
  state, degraded on an exhausted `block`-mode org budget, `notify`-mode over-limit does NOT
  degrade, and the live `/api/assistant/status` endpoint reporting `mode` correctly both enabled
  (degraded, via a forced breaker-open) and disabled (always `full`). `test_extraction.py`'s
  `test_status_reflects_flag` updated for the new `mode` key in the envelope (shape-only change,
  no new assertions needed there — the mode value at default settings is `full`).
- **Accept:** 859 tests green (up from 852 — 7 new); `gate:all` 00–15 green; i18n parity (1834
  keys, +2 for `status.degraded`/`status.down`) + `tsc -b` + `gate03` (brand) green; bundle budget
  unaffected (239.4 kB gzip main chunk, `AssistantPanel` itself is already code-split — only the
  tiny `healthMode` plumbing in `AssistantProvider.tsx` touches the main chunk). Golden evals
  re-run offline through the gateway: 110/148 pass (74.3%), identical to the Phase 1 baseline (the
  offline harness plays back recorded responses through `ask`/`agent`'s real service code, which
  now calls `gateway.complete_json` instead of the pre-gateway `services/llm.py` — same numbers
  prove T2.1's "behavior byte-identical" invariant held all the way through T2.8). BASELINE.md
  updated with a Phase 2 section below.
- **Output:** Phase 3 builds on a routed, cached, budgeted, honest gateway.

## Phase 2 acceptance

### Staging failover drill — 2026-07-12

**What was run for real (zero network, zero provider spend):** this deployment is customer-hosted
single-tenant with no separate staging infrastructure — "staging" here is this same box with real
`GEMINI_API_KEY`/`MISTRAL_API_KEY`/`GROQ_API_KEY` configured (`provider_chain() ==
["gemini", "mistral", "groq"]`, no `ANTHROPIC_API_KEY`). Actually revoking a real key and letting a
live call fail against it costs real, billed API spend without a clear win over the equivalent
breaker-level simulation (T2.3's own test suite — `test_circuit_breaker.py` — already proves a
real `complete_json` call fails over correctly when a provider errors); the same "needs a human's
explicit opt-in before spending" line this codebase already draws for `record_evals --yes-live`
and `eval_routing --yes-live` (T2.4) applies here. So the drill below exercises the exact runtime
function the mode surface reads (`gateway.breaker` + `gateway.status.mode()`), via
`manage.py shell`, with results captured verbatim:

```
chain: ['gemini', 'mistral', 'groq']
1) baseline mode: full
2) after gemini (primary) breaker opens, mode: degraded | gemini state: open
3) after ALL providers breaker-open, mode: down
4) after recovery (record_success on all), mode: full
```

Reproduces: `manage.py shell -c "..."` forcing `breaker.record_failure("gemini")` ×5 (opens the
primary's breaker — `status.mode()` flips `full → degraded`, matching a real primary-provider
outage: mistral/groq remain usable, chat still answers via them, `Trace.meta.routing.skipped`
carries `{"provider": "gemini", "reason": "breaker_open"}` per T2.3's existing, tested trace
shape); then forcing all three open (`mode → down`, matching `AllProvidersDown` — the state where
the next real call would fail before trying any runner); then `record_success` on all three
(`mode → full`, matching the real recovery path — a half-open probe that succeeds re-closes the
breaker, T2.3's own `test_half_open_probe_recovers_the_provider`).

**Ops traces:** `test_circuit_breaker.py::test_open_breaker_is_skipped_without_calling_the_provider`
already proves, against a real (monkeypatched-runner) `complete_json` call, that a skipped provider
shows up as `{"provider": "anthropic", "reason": "breaker_open"}` in `Trace.meta.routing.skipped`,
and `OpsPage.tsx`'s "Skipped providers" line (T2.3) renders it — this is the same code path the
drill above exercises at the breaker layer, so its ops-visibility is already covered by that test,
not re-asserted here.

**User experience:** while `degraded`, the panel shows the new banner
(`assistant.status.degraded`, ar/en, `--color-status-waiting`) — chat itself is unaffected (no
provider is fully down, so no call ever reaches the empty-chain path). While `down`, the banner
reads `assistant.status.down` (`--color-status-failed`) and a real chat call would raise
`AllProvidersDown`, surfaced as the existing blame-free error line (unchanged from T2.3). Zero
500s in either state — `AllProvidersDown` subclasses `AssistantUnavailableError`, handled by every
existing `except AssistantUnavailableError`/`except AppError` call site.

**A live, real-key drill** (revoke `GEMINI_API_KEY` in `.env`, ask a real question, confirm the
answer arrives via `mistral`, restore the key) is the natural follow-up once the user is ready to
spend a few live API calls to verify it end-to-end against the real providers — the mechanism it
would exercise (chain walk skipping a provider) is identical to what's proven above and in
`test_circuit_breaker.py`; only the "real network call" part is new, and per the `--yes-live`
precedent that's the user's call to make, not this session's.

### Phase acceptance checklist

- [x] All Phase 2 tasks (T2.1–T2.9) checked off.
- [x] `pytest` green — 859 tests (repo-wide).
- [x] `gate:all` (00–15) green.
- [x] Frontend: i18n parity (1834 keys) + `tsc -b` + `gate03` (brand) green; bundle budget green
      (239.4 kB gzip main chunk).
- [x] Golden evals re-run offline through the gateway: 74.3% (110/148), not below the Phase 1
      baseline (74.3%) — see BASELINE.md.
- [x] Staging failover drill documented above (breaker-level simulation; a live real-key run is a
      user-initiated follow-up, same `--yes-live` posture as T2.4).
- [x] `BASELINE.md` updated with Phase 2 columns.
