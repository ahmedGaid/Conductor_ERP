# Twenty CRM AI Study → Conductor AI Upgrades (2026-07-16)

Deep source-level study of Twenty's AI assistant/agent system (github.com/twentyhq/twenty,
main @ 2026-07-15 tarball), compared against `erp/assistant` as built and the ai-reliability
roadmap as planned. This document is the grounding for the amendments made the same day to
FILE_03 / FILE_05 / FILE_07 / FILE_08 (marked `[Twenty study 2026-07-16]` in those files).

**Honesty notes.** Everything below about Twenty is verified by reading its server source
(`packages/twenty-server/src/engine/metadata-modules/ai/*`, `core-modules/tool-provider/*`,
`api/mcp/*`). I did NOT run Twenty's UI — judgments about how it *feels* are inferred from
code + prompts, not from use. Where I am not sure, I say so inline.

---

## 1. Twenty's AI architecture (as verified in source)

**Stack:** NestJS + Vercel AI SDK (`ai` package `streamText`) + BullMQ queue + Redis pub/sub
+ GraphQL subscriptions. One conversational agent; no multi-agent swarm.

**Execution path for one chat turn:**
1. `AgentChatStreamingService.streamAgentChat` — claims the thread via an optimistic UPDATE
   (`activeStreamId IS NULL → streamId`). If busy → the message is **queued** on the thread
   and flushed when the current stream ends. A `pendingQuestionMessageId` on the thread also
   blocks new streams (parked on a question to the user).
2. The turn runs as a **queue job** (`stream-agent-chat.job`), never on the HTTP request:
   - Redis **heartbeat** (`agent-chat-stream-alive:{streamId}`, 30 s TTL, 5 s refresh).
   - Chunks publish to Redis → GraphQL subscription; DB **checkpoint** of the partial
     assistant message every few seconds (tee'd stream); reconnecting clients get catch-up.
   - Assistant message id = `uuidv5(streamId)` → **idempotent** persistence across job retries.
   - `reapDeadStream`: on read, if heartbeat is gone → mark turn failed
     (`STREAM_INTERRUPTED`), release claim, emit stream-error. `retryLastFailedTurn` deletes
     that turn's assistant messages and re-enqueues.
   - Cancel = Redis pub/sub channel → AbortController.
3. `ChatExecutionService.streamChat` — builds actor context (role-scoped), tool index,
   system prompt, then ONE `streamText` call with `stopWhen: maxSteps || ask_questions called
   || credits exhausted`. Native multi-step tool calling; parallel tool calls possible.

**Tool system — progressive disclosure (the standout design):**
- 9 pluggable tool providers (database CRUD, actions, workflow, metadata, views, dashboards,
  logic functions, navigation, webhooks) build a per-role **tool index** (names only).
- The system prompt carries the catalog compressed (CRUD as operation×object matrix, not
  N×M list) + a handful of **preloaded** tools. Everything else: `learn_tools` (returns
  schemas as text, batched, typo suggestions) → `execute_tool` (registry dispatch, compact
  output, large outputs spilled). The ToolSet passed to the model **never mutates** during a
  conversation → stable prompt prefix → provider prompt cache stays hot.
- **Skills as data:** markdown playbooks stored as metadata, listed name+description in the
  prompt, loaded on demand via `load_skill`. Prompt discipline: "Plan → Skill → Learn →
  Execute", with an intent gate (informational question ≠ build request).

**Human-in-the-loop:** `ask_questions` tool = 1–4 multiple-choice questions (2–4 options,
one `isRecommended`, optional multi-select, free-form always allowed). Calling it stops the
loop and parks the thread until answered. NOTE the asymmetry: Twenty's DB **write tools
execute directly** (role-gated, no confirm card) — the human gate exists only for questions,
not for writes. Verified in tool providers; I am not sure whether the UI adds any client-side
confirmation for destructive calls (nothing server-side).

**Context building:** sectioned system prompt (base rules / response format / workspace
instructions / user context / tool catalog / skill catalog / uploaded files) with per-section
token estimates and an **admin preview API**. Page context ("browsing context") is injected
into the LAST USER MESSAGE — not the system prompt — wrapped in a tag with "only use if the
user asks about the current page; do not call tools based on this" (keeps the cached prefix
stable AND stops context-triggered tool spam). Timestamps injected per message; user
name/locale/timezone/date in their own section.

**Memory/pruning:** thread tracks `conversationSize` (last step's input tokens). At 90% of
the model's context window: `pruneMessages` (drop reasoning before last message, tool calls
before last 2 messages). Still over → typed `CONTEXT_WINDOW_EXCEEDED` telling the user to
start a new thread. A `data-compaction` event tells the UI pruning happened. Message
metadata carries usage + conversationSize + contextWindow → the UI can render a context
meter. No rolling summaries (ours planned in T3.7 is stronger).

**Model abstraction:** model registry fed by a models.dev catalog; per-workspace default
`smartModel` + a cheap "speed model" role; per-agent model config; native tool binding
(provider web search); provider-specific middleware (Gemini tool-result sanitizer). No
automatic cross-provider failover and no mid-stream recovery (ours is stronger).

**Reliability details worth naming:**
- `experimental_repairToolCall`: malformed tool args → one structured re-generation against
  the schema with the error text (billed, telemetry-tagged). Invalid tool *names* are not
  repaired (fail fast).
- `finalizeDanglingToolParts` (unclosed tool calls in stored history), unsupported file
  parts replaced per model modality, empty-completion detection with a failure taxonomy
  (`user-cancelled | stream-error | credits-exhausted | empty-completion`) logged + metered.
- Metrics: TTFT, step latency, turn started/completed/failed (with `failure_phase`),
  per-tool success/failure counters, tool output token histograms, cache read/write tokens.
- Anthropic **cache breakpoints injected per step** + `promptCacheKey = threadId`; cache
  creation/read tokens extracted per step and fed into cost accounting.

**Cost:** every step decrements workspace credits; `hasNoMoreAvailableCredits` **stops the
loop mid-turn**; repair calls and native web-search calls are billed too. Cost breakdown
separates input/output/cache-read/cache-write/reasoning tokens. (The credits layer itself is
SaaS monetization — not our problem — but the *granularity* is the lesson.)

**Quality monitoring:** `ai-agent-monitor` — a background job grades EVERY turn with the
cheap model (0–100 + comment, heuristic fallback), stored per turn, shown in an agent
monitor UI. Online, continuous, per-turn — complements (does not replace) offline evals.

**Extensibility:** the same tool registry is exposed as an **MCP server** (auth-guarded,
read-only/closed-world annotations, excluded-tool list) — external agents (Claude, etc.) can
drive Twenty. Code-interpreter sandbox for file analysis. Workflow AI-agent nodes.

## 2. Why Twenty's AI feels reliable (the engineering, not the magic)

1. **A turn cannot be lost.** Queue job + claim + heartbeat + checkpoint + idempotent
   persist + reap + retry — refresh the page mid-answer and the answer is still there;
   a crashed worker becomes a visible, retryable failure instead of a silent hang.
2. **The model's world is stable.** Constant ToolSet, stable prompt prefix, page context in
   the user turn — the prompt cache stays hot (fast TTFT) and behavior doesn't wobble
   between rounds.
3. **Failures are typed and owned.** Every way a turn can end has a name, a metric, a user
   message, and (where possible) a retry affordance. Nothing ends as a spinner.
4. **The model is told how to behave in *this* product.** Data-efficiency rules (small
   limits, filters, batch tools), record-reference format with anti-hallucination rules
   ("never invent IDs; only reference what a tool returned"), a "primitives people mix up"
   section, an intent gate. Product-specific prompt engineering, continuously maintained.
5. **Cost can't run away.** Credit check per step, stop mid-turn, everything billed
   including repairs.
6. **Someone is always watching.** Per-turn online grading + metrics with failure phases.

## 3. Design patterns worth adopting (adapted, not copied)

| # | Pattern | Adaptation for Conductor | Landed where |
|---|---|---|---|
| 1 | Detached durable streaming (queue job + claim + heartbeat + checkpoint + reap + retry + catch-up) | Celery (already in stack) + Redis pub/sub → SSE relay; claim on Conversation; idempotent assistant persist | FILE_05 **T5.9** (new) |
| 2 | Structured clarify (`ask_questions` MCQ card) | `clarify` decision gains typed options (2–4 + recommended + free text); parked turn | FILE_05 **T5.10** (new) |
| 3 | Mid-turn cost stop | budgets re-checked between agent rounds, not just pre-call; typed `stop=budget` | FILE_05 **T5.10** (new) |
| 4 | Provider prompt caching (breakpoints, stable prefix, cache-token accounting) | Anthropic `cache_control` on the stable envelope prefix; volatile material (page/date) moves to the user turn; traces record cache read/write | FILE_07 T7.5 (amended) |
| 5 | Context meter + visible compaction | conversation-size/budget meter in panel; calm "compacted" notice event | FILE_03 T3.6 (amended) |
| 6 | Online per-turn grading (sampled) | cheap-model 0–100 + comment on a sample of live turns → Trace.meta → drift dashboard | FILE_08 T8.3 (amended) |
| 7 | Failure taxonomy for turns | stop-reason taxonomy on Trace.meta.stop already exists — extend with `budget`, `interrupted`, `empty` + ops tile | FILE_05 T5.9/T5.10 accept blocks |
| 8 | Progressive tool disclosure (learn/execute meta-tools) | NOT yet — catalog ~20 read tools + actions is fine inline. Trigger written down: adopt when catalog > ~30 tools or prompt diet (T7.2) demands it | FILE_07 T7.2 (note) |
| 9 | Skills-as-data (domain playbooks loaded on demand) | ERP playbooks (month-end close, VAT filing, three-way match) as versioned prompt-registry docs the planner can load; pairs with T5.7 workflow specs | FILE_05 T5.7 (decision note) |
| 10 | Record-reference anti-hallucination rules | our citations are already server-built from real records (stronger); adopt the *prompt rule* "never name a document/record a tool didn't return" — already enforced by grounding guards | no change needed |

## 4. Patterns NOT to adopt (and why)

- **Direct-execute write tools in chat.** Twenty's CRUD tools write immediately (role-gated
  only). For an ERP this is disqualifying — our propose → confirm → execute law stays.
- **Credits/billing layer.** SaaS monetization machinery. Our budgets protect money in
  microcents; that's the right frame for customer-hosted single-tenant.
- **Metadata-driven auto-generated CRUD tools for arbitrary objects.** Depends on their
  custom-object engine — on our refuse-list ("Configurability is Odoo's disease"). Typed
  contract tools ARE the moat: money formatting, scoping, and citations live server-side.
- **Vercel AI SDK.** No Python equivalent worth importing; our gateway IS that seam, and
  ours does things theirs doesn't (chain failover, breaker, mid-stream recovery, response
  cache, budgets).
- **MCP server exposure.** Genuinely interesting for "agents drive the ERP" later — but it
  widens the attack surface and is premature before guardrails Phase 6. Parked, not refused.
- **Code interpreter sandbox.** New dependency + security surface; our import/extraction
  paths cover the ERP file cases. Revisit only with a real customer need.
- **Message pruning as the only memory strategy.** Ours (budget manager + rolling summaries,
  T3.6/T3.7) is strictly stronger; keep it.

## 5. Gaps in the current Conductor AI vision (found by this study)

1. **Streaming is request-bound.** A refresh, network blip, or worker restart kills the
   turn; the partial is persisted but there is no resume, no retry affordance, no liveness
   signal. Long agent runs occupy a web worker. ← biggest gap, now T5.9.
2. **No per-round cost gate.** Budgets check before the turn; a 6-round agent turn can
   overshoot within the turn. ← T5.10.
3. **Clarify is a dead end.** Free-text question ends the turn; the user types; the planner
   restarts from scratch. No options, no parked state. ← T5.10.
4. **No provider prompt caching.** Every agent round re-sends the whole prompt at full
   price; the envelope is rebuilt fresh each request (correct for permissions, but nothing
   marks the stable prefix). ← T7.5.
5. **Context health is invisible.** 20-turn silent truncation; the user never sees size or
   compaction. (T3.6/T3.7 planned the mechanics; the UI meter was missing.) ← T3.6.
6. **Quality watching is offline-only.** Evals run scheduled/CI; no live sampled grading.
   ← T8.3.
7. **One decision per round.** The planner picks one tool per LLM round; independent reads
   serialize. (T5.4 parallel reads already planned — study confirms its value; native
   parallel tool-calls noted as a later gateway option, not a task.)

## 6–7. Recommended improvements + updated architecture

The architecture does NOT change shape — it gets three missing organs. Everything already
decided stays decided: tool-use only, writes HITL, gateway front door, traces, evals,
Arabic-first.

```
user ── SSE ──► api (thin: claim, subscribe, catch-up)
                 │ enqueue
                 ▼
        Celery agent worker  ── heartbeat ──► Redis
                 │  runs erp/assistant loop (unchanged semantics)
                 │  publishes chunks ──► Redis pub/sub ──► SSE relay
                 │  checkpoints partial answer → Message (idempotent id)
                 ▼
        gateway (chain failover · breaker · budgets/round · caches · traces)
```

- **Durability layer (T5.1 + T5.9):** AgentRun rows + detached execution. The loop's
  semantics (planner rounds, guards, proposals, detours) do not change; where it *runs* and
  how its output *survives* changes.
- **Interaction layer (T5.10):** clarify becomes a first-class parked state with options —
  the conversational twin of the confirm card. One consistent rule: **the agent never ends
  a turn with a wall of text when a structured card can carry the decision.**
- **Economy layer (T7.5):** stable-prefix envelope + cache breakpoints + cache-token
  accounting. Target: agent-round marginal input cost drops to cache-read pricing.

Where we are already ahead of Twenty, the plan keeps our design: chain failover + breaker +
mid-stream continuation (T2.x, shipped), response/semantic caches (shipped), deterministic
grounding guards (shipped), simulation diff + verifier packs (shipped), eval harness with
judge calibration (shipped), prompt registry + canary variants (T8.1).

## 8. Prioritized roadmap changes (all landed today)

| Priority | Change | File |
|---|---|---|
| 1 | NEW T5.9 Detached durable streaming — executes right after T5.1 | FILE_05 |
| 2 | NEW T5.10 Structured clarify + mid-turn cost stop — executes after T5.5 | FILE_05 |
| 3 | T7.5 gains provider prompt caching (breakpoints + accounting) | FILE_07 |
| 4 | T3.6 gains context meter + visible compaction notice | FILE_03 |
| 5 | T8.3 gains sampled live-turn grading | FILE_08 |
| 6 | T7.2 note: progressive tool disclosure trigger (catalog > ~30 tools) | FILE_07 |
| 7 | T5.7 note: workflow specs may carry skill-style instruction docs | FILE_05 |

Phase order unchanged. Task numbers T5.2–T5.8 unchanged (cross-referenced from DECISIONS.md,
FILE_06/07/08, os-foundations, agent-actions `_done` files — those are never renumbered);
the new tasks carry fresh numbers and explicit "executes here" placement notes.

## 9. Risks and trade-offs

- **T5.9 moves chat onto Celery.** New failure modes (worker deploys mid-turn, queue
  backlog). Mitigations are the pattern itself (heartbeat, reap, retry, idempotent persist)
  plus a drill in the task. Redis/Celery are already operated in this stack — no new infra.
- **SSE relay adds one hop** (worker → Redis → view). TTFT impact must be measured
  (T7.1 budgets apply); Twenty pays the same hop and stays fast.
- **Prompt caching constrains envelope freedom.** The stable-prefix rule means permission or
  page changes must ride the user turn or bust the cache knowingly. T7.5 documents the rule;
  the envelope registry (T3.6) enforces section order.
- **Structured clarify can be overused** (question spam). The prompt rule from Twenty is
  imported verbatim: never ask what a tool can look up; never ask on trivial defaults.
- **Online grading costs money per sampled turn.** Sampling rate is a setting; the speed
  model does the grading; budgets cover it.

## 10. Final recommendation

Adopt Twenty's **reliability shell** (durable detached streaming, structured pauses,
step-level cost control, prompt-cache discipline, online grading) around Conductor's
**stronger core** (typed contract tools as the actor, HITL writes with simulation,
gateway failover, deterministic grounding, calibrated evals). Do not adopt its execution
model for writes, its billing layer, or its metadata-generated tool surface — those are
CRM/SaaS answers to problems an Arabic-first, customer-hosted ERP has already answered
better. The result is an AI operating layer neither product has: Twenty-grade delivery
mechanics with ERP-grade safety.

*Study by Claude (Fable 5), grounded in Twenty main @ 2026-07-15 and erp/assistant @ 3cb4f2a.*
