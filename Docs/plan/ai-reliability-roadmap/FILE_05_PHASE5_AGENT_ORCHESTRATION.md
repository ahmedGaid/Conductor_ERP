# Phase 5 (Months 13–15) — Agent Orchestration & Planning v2

## Objectives

1. Agent runs become **plan → validate → execute → verify** instead of react-loop-until-done:
   plans are typed objects users can watch, argument validation catches bad tool calls before they
   run, and a self-verification pass checks numbers before display.
2. Runs are durable: checkpointed per step, resumable after interruption — completing the
   ai-workspace FILE_13 detour/resume story at the engine level.
3. Multi-step ERP workflows (month-end checklist, three-way match run, reorder review) execute as
   declarative task graphs with human gates — the "Agentic" in ARP, made real and safe.
4. Agent quality is benchmarked per module with a task-completion suite; routing for agent task
   classes becomes eval-gated like everything else.
5. `[Twenty study 2026-07-16]` Turns survive reality end-to-end: execution detaches from the
   HTTP request (queue job + liveness + checkpoints + retry), and a pause for the user
   (clarify/confirm) is a parked state, not a dead end. Grounding: `TWENTY_AI_STUDY.md`.

## Architecture decisions

- **Plan-then-execute, single agent.** One planner emits a typed `Plan` (list of steps: tool +
  args-intent + rationale) before any tool runs; the executor walks it, re-planning only on step
  failure (max 2 replans). No multi-agent swarms — an ERP needs auditability, not agent theater.
- **Validation is a layer, not a prompt hope.** Every tool call passes: (1) JSON-schema of the
  tool signature, (2) semantic checks (referenced ids exist AND are visible to `actor` — reusing
  the tool layer's own scoping so validation can't be looser than execution), (3) enum/date/range
  sanity. Reject → one structured repair attempt (error fed back verbatim) → then the step fails
  typed. Validation results are TraceSteps (`kind="validation"`).
- **Checkpointing is DB rows, not process state.** `AgentRun` + `AgentStep` tables; every step
  transition persisted before execution proceeds. Resume = load run, rebuild envelope (fresh data,
  same goal), continue from the first non-terminal step. Survives process restart by construction.
- **Workflows are data.** `WorkflowSpec` (JSON: steps, dependencies, tool bindings, human-gate
  markers) validated against a schema; the SAME executor runs ad-hoc plans and specs. Human-gate
  steps emit the existing confirm cards and park the run until confirmed — write safety is the
  one thing that never changes shape.
- **Self-verification is cheap-model cross-check.** After the final answer, a `verify` task-class
  call receives ONLY the tool outputs (not the chat) + the drafted answer → flags numeric/entity
  mismatches → one silent regeneration with flags attached; still failing → the answer ships with
  a designed "check these figures" caveat rather than silent confidence. Fail-open, never blocks.
- `[Twenty study 2026-07-16]` **Execution detaches from the request.** Chat/agent turns run in a
  Celery worker (already in stack); the SSE view claims the conversation, subscribes to a Redis
  channel, and relays chunks. Liveness = Redis heartbeat; a dead worker becomes a typed, retryable
  failure, never a silent hang. Partial answers checkpoint to the Message row under an idempotent
  id (derived from the run id) so job retries can't duplicate. The loop's SEMANTICS do not change —
  only where it runs and how its output survives. (Twenty pattern, verified in
  `stream-agent-chat.job.ts` / `agent-chat-streaming.service.ts`; details in `TWENTY_AI_STUDY.md`.)
- `[Twenty study 2026-07-16]` **A pause is a parked state.** `clarify` emits a typed options card
  (2–4 options, one recommended, free text always allowed) and parks the run exactly like
  `waiting_confirm`; the answer resumes the SAME run with its gathered results intact — the planner
  never restarts from scratch after asking. One rule everywhere: the agent never ends a turn with a
  wall of text when a structured card can carry the decision.

## Decision points

- None. All built on existing loop, tools, confirm registry, gateway, traces.

## Success metrics (phase exit)

- Agent benchmark suite (T5.6): task completion ≥ 85% overall, ≥ 80% per module; zero unsafe
  writes (any write bypassing confirm = automatic suite failure).
- First-attempt tool-argument validity ≥ 97% (was: Phase 1 baseline); repair loop rescues ≥ half
  of the remainder.
- Kill the worker mid-run in staging → run resumes to completion from checkpoint (drill documented).
- Self-verification catches ≥ 90% of seeded numeric-mismatch cases at ≤ 1 extra cheap call per run.
- `[Twenty study 2026-07-16]` Refresh-the-page drill: reload mid-answer → the partial answer is on
  screen after reload and the turn finishes (or lands as a typed, retryable failure). No turn ends
  as a spinner; every stop has a reason in `Trace.meta.stop`
  (`answered | step_budget | budget | clarify | confirm | cancelled | interrupted | error`).

---

## Tasks

### [x] T5.1 — AgentRun/AgentStep persistence

- **Goal:** every agent run is a durable DB object with typed step states.
- **Prereq:** Phase 4 done.
- **Files:** modify `models.py` (+migration); refactor `services/agent.py` state handling.
- **Steps:**
  1. `AgentRun`: uuid pk, actor FK, conversation FK, goal (text), status (`planning` | `running` |
     `waiting_confirm` | `paused` | `done` | `failed` | `cancelled`), plan JSON, current_step int,
     result JSON, trace FK, timestamps. `AgentStep`: run FK, seq, tool, args JSON, status
     (`pending` | `validated` | `running` | `ok` | `repaired` | `failed` | `skipped`), result
     summary JSON (sizes/ids, not payloads), error, timestamps.
  2. Refactor the loop to write state transitions BEFORE acting (write-ahead): plan persisted →
     each step persisted `pending` → `running` → terminal. In-memory flow otherwise unchanged —
     this task adds durability, not behavior.
  3. SSE step events now derive from the same transitions (one source of truth for UI progress).
- **Accept:** existing agent tests green unchanged; new test walks a monkeypatched 3-step run and
  asserts row states at each phase; a mid-run exception leaves an accurate `failed` row.
- **Output:** runs you can inspect, resume, and audit.

### [x] T5.9 — Detached durable streaming `[Twenty study 2026-07-16 — NEW]`

> Numbered T5.9 because T5.2–T5.8 are pinned by cross-references (DECISIONS.md, FILE_06/07/08,
> os-foundations, agent-actions). **Executes HERE, second in the phase, right after T5.1.**

- **Goal:** a chat/agent turn survives page refresh, network drop, and worker restart; no turn
  ever ends as a silent hang.
- **Prereq:** T5.1. Celery + Redis already operated (existing stack facts) — no new infra.
- **Files:** modify `erp/assistant/api/views.py` (SSE endpoints become claim + subscribe + relay),
  `services/agent.py` entry, `tasks.py` (new Celery task); new `services/stream_relay.py`
  (Redis pub/sub publish/subscribe + heartbeat helpers); frontend panel reconnect handling.
- **Steps:**
  1. **Claim:** `Conversation` gains `active_stream_id` (+ `last_stream_error` JSON). Start turn =
     optimistic UPDATE (`active_stream_id IS NULL → new id`). Busy → typed 409 the panel renders
     calmly ("still answering — it will appear here"); v1 rejects rather than queues (queueing is a
     follow-up if real usage demands it).
  2. **Detach:** the generator (`agent.run` / `ask.stream_answer`) executes inside a Celery task on
     a dedicated queue (`ai_stream`); every yielded SSE event publishes to Redis channel
     `assistant:conv:{id}`. The HTTP view subscribes and relays — thin, stateless, reconnectable.
  3. **Heartbeat + reap:** worker refreshes `assistant-stream-alive:{stream_id}` (TTL 30 s, refresh
     5 s). Any read path finding a claim with no heartbeat → clear claim, set `last_stream_error`
     (`interrupted`, blame-free ar/en message), emit `stream-error` event, `Trace.meta.stop =
     "interrupted"`.
  4. **Idempotent checkpoints:** partial answer upserts into the assistant Message row every ~2 s
     under a deterministic id derived from the stream id — job retry can't duplicate; reload
     mid-stream shows the partial via normal message fetch + a catch-up event on resubscribe.
  5. **Retry affordance:** `POST .../retry-turn` re-enqueues the last failed turn (claim must hold
     `last_stream_error`; deletes that turn's assistant message first). Panel shows a retry button
     on the error state.
  6. **Cancel:** stop button publishes on `assistant:cancel:{stream_id}`; worker checks between
     rounds/chunks and closes with `stop="cancelled"` (persisting the partial, as today).
  7. Settings flag `ASSISTANT_DETACHED_STREAMING` (default on in dev after the drill passes;
     documented in RUNBOOK) — the in-request path remains as fallback for installs without a
     running worker, chosen at view level.
- **Accept:** drills documented + repeatable: (a) refresh mid-answer → partial visible after
  reload, turn completes; (b) `kill -9` the worker mid-turn → reap fires, error card + retry
  button, retry completes; (c) two rapid sends → second gets the calm busy response. Existing
  agent/ask tests green (in-request path untouched); new tests for claim race (two claimants, one
  wins), reap, idempotent checkpoint, retry. Gates green.
- **Output:** Twenty-grade delivery mechanics under the existing loop — turns that cannot be lost.

### [ ] T5.2 — Typed planner

- **Goal:** the model emits a validated Plan object before any tool executes.
- **Prereq:** T5.1.
- **Files:** create `services/planner.py`, `prompts/agent_plan.md`; modify `services/agent.py`.
- **Steps:**
  1. Plan schema: `[{step, tool, args_intent (free text), why (one line), needs_confirm (bool,
     derived from the tool's write flag — model's value is overwritten by the registry's truth)}]`,
     max 8 steps. Planner call = `agent_plan` task class, strict JSON, schema-validated; invalid →
     one retry with the validation error; still invalid → fall back to today's reactive loop
     (flagged in trace `meta.plan_fallback=true`) — never a dead end.
  2. Trivial-goal shortcut: single-tool answers skip planning (heuristic: planner prompt itself
     returns `direct: true`) — don't tax simple questions.
  3. Plan streams to the panel as the existing step-progress UI (steps shown as pending, ticking
     to done) — reuse components, no new UI concepts.
  4. Executor walks the plan; a failed step triggers replan-from-current-state (max 2, then
     typed failure with a designed message naming the step that failed and what the user can do).
- **Accept:** golden agent cases run through planner path (recordings updated); fallback +
  replan-cap tests; UI smoke ar/en; plan visible in ops trace.
- **Output:** users watch a plan execute, not a spinner.

### [ ] T5.3 — Tool-call validation layer + repair loop

- **Goal:** invalid tool calls are caught before execution and repaired once, structurally.
- **Prereq:** T5.1.
- **Files:** create `services/toolguard.py`; modify `services/agent.py` executor + `tools.py`
  metadata.
- **Steps:**
  1. Ensure every tool in the catalog declares a complete JSON-schema for args (audit the
     registry; fill gaps — this is the bulk of the task; list every tool touched in the commit).
  2. `toolguard.validate(tool, args, actor)`: schema check → id-existence/visibility check
     (execute the tool layer's own `get`-scoped lookup for each FK-like arg) → range/enum/date
     sanity (dates parseable + within 1900–2100, quantities ≥ 0, enums from schema). Returns
     typed `Valid | Invalid(reasons)`. Pure + fast; unit-tested per check.
  3. Executor: `Invalid` → feed reasons back to the model as a structured repair message → one
     re-emit → still invalid → step `failed`, replan handles it. All attempts = TraceSteps.
  4. Metric: validity-rate per tool per model queryable from traces (ops summary tile).
- **Accept:** per-check unit tests; integration test: wrong-id call repaired then executes;
  invariant: executor cannot call a tool without a `Valid` token (enforced by type/assert).
- **Output:** garbage args die before they touch data.

### [ ] T5.4 — Parallel-safe read steps

- **Goal:** independent read-only plan steps execute concurrently; writes never do.
- **Prereq:** T5.2, T5.3.
- **Files:** modify `services/agent.py` executor.
- **Steps:**
  1. Dependency inference: step B depends on A if B's args_intent references A's output (planner
     marks `after: [seq]`; executor trusts but re-checks: any unresolved reference forces
     sequential). Read-only tools (registry flag) with no dependency edge → run in a batch via
     `ThreadPoolExecutor(max_workers=4)` — Django ORM per-thread connections; close connections
     per worker (`db.connections.close_all()` in worker teardown; note: this is the known Django
     threading footgun — test it explicitly).
  2. Any write/confirm step is a hard barrier: everything before completes, it runs alone.
  3. SSE events remain ordered by seq for calm UI (buffer out-of-order completions).
- **Accept:** test: 3 independent reads complete in ~max(latency) not sum (fake tools with
  sleeps); write-barrier test; no connection-leak warnings under the parallel test.
- **Output:** multi-lookup answers get faster for free.

### [ ] T5.5 — Resume + human-gate parking (detour completion)

- **Goal:** runs survive restarts and park cleanly on confirmations — FILE_13's engine half.
- **Prereq:** T5.1, T5.2; read `Docs/plan/ai-workspace-plan/FILE_13_WORKFLOW_RESUME.md` (if not
  `_done`, coordinate: this task provides the engine; FILE_13 provides the UX — neither
  duplicates the other).
- **Files:** modify `services/agent.py`, `services/actions.py`, api endpoints
  (`POST /api/assistant/runs/<id>/resume`), frontend resume affordance.
- **Steps:**
  1. Confirm-needing step → run status `waiting_confirm`, card emitted (existing flow), executor
     exits. Confirm/deny endpoint transitions the step and resumes the executor (deny → replan
     or graceful stop with summary of what WAS done — never silent abandonment).
  2. `paused`/orphan recovery: `resume` loads the run, refreshes envelope data, revalidates the
     next step's args against current data (records may have changed — stale ids → replan), and
     continues. Idempotency: completed write steps are never re-executed (check step status +
     the action registry's existing idempotency guard; document which of the two is authoritative:
     the step status is).
  3. Startup sweep command `recover_agent_runs`: runs stuck `running` > 10 min → `paused` +
     panel notice with a resume button.
  4. Staging drill (documented): kill worker mid-run → sweep → resume → completes correctly.
- **Accept:** resume tests (confirm path, deny path, stale-id path, double-resume no-ops); drill
  documented in the phase record; ar/en strings; gates green.
- **Output:** agent work that survives reality.
- `[Twenty study 2026-07-16]` Note: with T5.9 landed, orphan detection in step 3 uses the stream
  heartbeat (dead within ~30 s), not only the 10-minute staleness sweep — the sweep stays as the
  backstop for installs running the in-request fallback.

### [ ] T5.10 — Structured clarify + mid-turn cost stop `[Twenty study 2026-07-16 — NEW]`

> Numbered T5.10 for the same cross-reference reason as T5.9. **Executes HERE, right after T5.5
> and before the benchmark suite** (the bench must exercise both behaviors).

- **Goal:** asking the user a question pauses the run instead of ending it, and a runaway turn
  stops on budget between rounds instead of after the money is spent.
- **Prereq:** T5.2 (plan objects), T5.5 (parking machinery). Read Twenty's `ask-questions.tool.ts`
  contract in `TWENTY_AI_STUDY.md` §1 — adapt the shape, not the code.
- **Files:** modify `services/agent.py` (clarify decision schema + parking), `services/actions.py`
  (reuse card plumbing), api confirm/answer endpoint, panel clarify card component, prompts
  (`agent_loop` clarify rules), `gateway/budgets.py` (round-level check helper).
- **Steps:**
  1. **Clarify schema:** the planner's `clarify` decision gains `options: [{label, description?,
     recommended?}] (2–4, ≤1 recommended)` + `allow_free_text` (always true in UI). Free-text-only
     clarify stays legal (not every question has options).
  2. **Parking:** clarify with options parks the run (`waiting_clarify`, mirrors
     `waiting_confirm`): gathered results + plan persist on the AgentRun; the card rides message
     meta like proposals do. The user's pick (or typed answer) resumes the SAME run — the answer is
     appended to `gathered` as `{tool: "user_answer", ...}`; the planner continues, it does not
     restart.
  3. **Prompt rules (imported from Twenty, verbatim intent):** never ask what a tool can look up;
     never ask on trivial choices with an obvious default; at most a few focused questions; mark
     one recommended option.
  4. **Mid-turn budget:** between planner rounds, `budgets.check_round(actor, spent_so_far)` —
     over → stop gathering, answer from what's gathered with a designed ar/en note, `Trace.meta
     .stop = "budget"`. Never mid-sentence: the check sits at round boundaries only.
  5. Stop-reason taxonomy unified in `Trace.meta.stop` (see phase success metrics) + ops tile
     counting stops by reason.
- **Accept:** parked clarify survives reload and resumes with prior results intact (test);
  free-text answer path; budget stop test (fake spend → calm partial answer, correct stop reason);
  prompt-rule eval cases (≥ 6, ar+en: 3 that MUST clarify with options, 3 that must NOT ask);
  i18n parity + tsc + gate03 + brand checklist on the card.
- **Output:** the conversational twin of the confirm card — decisions pause, money can't run away.

### [ ] T5.6 — Agent benchmark suite per module

- **Goal:** task-completion rate per module is a tracked number.
- **Prereq:** T5.2–T5.5, T5.9, T5.10 (the bench must cover parked-clarify and budget-stop paths).
- **Files:** create `evals/datasets/agent_bench_v1.jsonl` + runner mode.
- **Steps:**
  1. ≥ 40 benchmark tasks (≥ 60% ar) across purchasing, inventory, accounting, CRM, workflows:
     realistic multi-step goals ("compare last 3 supplier quotes for X and draft PO to the
     cheapest with delivery < 2 weeks") with fixture data + machine-checkable success predicates
     (final answer contains the right supplier id; a draft-PO proposal action exists with the
     right args; NO executed write without confirm).
  2. Runner mode `--suite agent`: recordings-based like T1.6; success predicate functions live
     next to the dataset, unit-tested.
  3. Scoreboard per module + per model; wire into `run_evals` output and ops view.
  4. Unsafe-write detector: any executed write action in a bench run without a confirmed card =
     suite-level failure regardless of other scores.
- **Accept:** suite runs offline; a deliberately-sabotaged predicate fails (negative test);
  baseline scores recorded.
- **Output:** "the agent works" becomes a per-module percentage.

### [ ] T5.7 — Declarative workflow specs + two shipped workflows

- **Goal:** repeatable ERP workflows run as data-defined graphs with human gates.
- **Prereq:** T5.5, T5.6.
- **Files:** create `services/workflows_ai.py` (name avoids clashing with `erp/workflow` app —
  read that app's adapters first: `erp/workflow/adapters/`), `workflow_specs/` JSON dir + schema;
  panel entry point.
- **Steps:**
  1. Spec schema: id, title (ar+en keys), steps [{id, tool | gate | subplan-goal, args template
     with `{placeholders}`, after: [ids], gate: bool}], version. Loader validates against
     JSON-schema; specs are code-reviewed files, not user-editable v1.
     `[Twenty study 2026-07-16]` A spec MAY carry an `instructions` field: a versioned
     prompt-registry doc (skill-style domain playbook — month-end close rules, VAT filing steps)
     injected into the planner ONLY while that workflow runs — knowledge loaded on demand, never
     resident in every prompt.
  2. Executor: translate spec → AgentRun plan (same tables, same UI, same confirm cards, same
     resume) — zero new execution machinery; gates park exactly like T5.5.
  3. Ship two specs end-to-end: **reorder review** (below-reorder items → supplier suggestions →
     draft PO proposals per supplier, each gated) and **month-start checklist** (unposted
     journals, pending approvals, stale drafts → summary + per-item deep links). Choose from
     existing tool coverage only — no new tools in this task.
  4. Panel: workflows listed in a calm picker; run history via AgentRun.
  5. Bench: add both workflows to the agent suite with fixtures.
- **Accept:** both specs green in bench; gates park/resume correctly; i18n parity, tsc, gate03,
  brand-feel checklist on the picker.
- **Output:** the ARP demo: work that runs itself, with a human hand on every gate.

### [ ] T5.8 — Self-verification pass + phase acceptance

- **Goal:** numeric/entity claims are cross-checked before display; phase signed off.
- **Prereq:** T5.6 (to measure), gateway `verify` task class.
- **Files:** create `services/verify.py`, `prompts/answer_verify.md`; modify agent finalization.
- **Steps:**
  1. Extract-and-check: `verify` call gets tool outputs (structured) + drafted answer → JSON
     `{ok | mismatches: [{claim, expected}]}`. Runs only when the answer contains numbers/amounts
     (regex gate incl. Arabic-Indic digits ٠-٩) — cheap and targeted.
  2. Mismatch → one regeneration with mismatches attached → re-verify → still bad → ship with a
     designed caveat block naming the uncertain figures (ar/en, blame-free) + trace flag.
  3. Seeded eval: 15 cases with recordings containing deliberate draft/tool mismatches — verifier
     must catch ≥ 90%; 10 clean cases must not trigger (false-positive guard ≤ 10%).
  4. Fail-open: verifier error → answer ships unverified, trace `meta.verify="skipped"`.
  5. Phase acceptance: bench suite ≥ targets, validity metric ≥ 97%, resume drill done, T5.9
     refresh/kill drills done, T5.10 clarify-park + budget-stop tests green, all boxes checked
     (including T5.9 and T5.10 — they execute out of numeric order, see their placement notes),
     BASELINE.md updated, rename `_done`.
- **Accept:** seeded evals pass both directions; latency budget: verification adds ≤ 1.5s p95
  (cheap model, parallel with nothing — it's terminal); acceptance recorded.
- **Output:** the agent double-checks its arithmetic like a careful accountant.
