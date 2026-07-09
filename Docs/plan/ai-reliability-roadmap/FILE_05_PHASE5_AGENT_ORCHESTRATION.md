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

## Decision points

- None. All built on existing loop, tools, confirm registry, gateway, traces.

## Success metrics (phase exit)

- Agent benchmark suite (T5.6): task completion ≥ 85% overall, ≥ 80% per module; zero unsafe
  writes (any write bypassing confirm = automatic suite failure).
- First-attempt tool-argument validity ≥ 97% (was: Phase 1 baseline); repair loop rescues ≥ half
  of the remainder.
- Kill the worker mid-run in staging → run resumes to completion from checkpoint (drill documented).
- Self-verification catches ≥ 90% of seeded numeric-mismatch cases at ≤ 1 extra cheap call per run.

---

## Tasks

### [ ] T5.1 — AgentRun/AgentStep persistence

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

### [ ] T5.6 — Agent benchmark suite per module

- **Goal:** task-completion rate per module is a tracked number.
- **Prereq:** T5.2–T5.5.
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
  5. Phase acceptance: bench suite ≥ targets, validity metric ≥ 97%, resume drill done, all boxes
     checked, BASELINE.md updated, rename `_done`.
- **Accept:** seeded evals pass both directions; latency budget: verification adds ≤ 1.5s p95
  (cheap model, parallel with nothing — it's terminal); acceptance recorded.
- **Output:** the agent double-checks its arithmetic like a careful accountant.
