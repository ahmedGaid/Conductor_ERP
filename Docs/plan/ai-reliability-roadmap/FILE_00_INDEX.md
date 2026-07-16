# Conductor AI — 24-Month Reliability & Production-Readiness Roadmap — Master Index

## Project Goal

Take the existing Conductor AI assistant (`erp/assistant/` + `apps/web/src/assistant/`) from
"works well in demos" to **enterprise-grade production AI**: measured, routed, guarded, fast,
cheap, and provably reliable. This roadmap is an **implementation blueprint** — every phase is
broken into small, sequential, self-contained tasks that any competent AI coding agent (including
weaker models) can execute in order without hidden context.

**We extend what exists — never rebuild.** Already shipped and NOT to be re-implemented:

| Capability | Where it lives today |
|---|---|
| Multi-provider client (Anthropic / Gemini / Groq), `complete_json`, `complete_stream`, `embed_text` | `erp/assistant/client.py` |
| Multi-step agent loop with streamed step progress | `erp/assistant/services/agent.py` |
| Typed read-tool catalog + query registry (list mode) | `erp/assistant/tools.py`, `erp/assistant/query_registry.py` |
| Human-in-the-loop write actions + confirm registry | `erp/assistant/services/actions.py` |
| RAG knowledge base: tsvector FTS + optional embedding blend | `erp/assistant/services/knowledge.py` |
| Context envelope (page/user/record context → system prompt) | `erp/assistant/services/context.py` |
| Conversations, SSE streaming, attachments, panel UI | ai-workspace-plan sessions 01–12 (done) |
| Harness hardening, suggestions, digest, extraction | rag-knowledge-plan sessions 01–11 (done) |

## The 8 Phases (3 months each)

| Phase | Months | Theme | File |
|---|---|---|---|
| **1** | 1–3 | Observability, Evaluation & Prompt Registry — *measure before improving* | FILE_01 |
| **2** | 4–6 | AI Gateway, Model Routing & Caching — *one policy-driven front door* | FILE_02 |
| **3** | 7–9 | Retrieval & Context Engineering v2 — *right context, right size, every time* | FILE_03 |
| **4** | 10–12 | Memory — *the assistant that remembers, safely* | FILE_04 |
| **5** | 13–15 | Agent Orchestration & Planning v2 — *plan, validate, verify, resume* | FILE_05 |
| **6** | 16–18 | Guardrails & Security — *injection-proof, scope-proof, leak-proof* | FILE_06 |
| **7** | 19–21 | Performance, Scalability & Cost — *fast and affordable at load* | FILE_07 |
| **8** | 22–24 | Production Hardening & Continuous Evaluation — *canary, drift, runbooks, sign-off* | FILE_08 |

Order is deliberate. Phase 1 is the foundation for everything: no phase after it can prove its
success metrics without the traces and eval harness Phase 1 builds. Phase 2 must precede 3–8
because routing/caching decisions get recorded in traces and consumed by later cost work. Do not
reorder phases. Tasks inside a phase are sequential unless a task says "parallel-safe".

## Cross-cutting success metrics (tracked from Phase 1 onward)

| Metric | Baseline (measure in P1) | Month 12 target | Month 24 target |
|---|---|---|---|
| Eval golden-set pass rate | measure | ≥ 85% | ≥ 95% |
| Groundedness (answers backed by tool/RAG output) | measure | ≥ 90% | ≥ 98% |
| Tool-call argument validity (first attempt) | measure | ≥ 95% | ≥ 99% |
| Chat TTFT p95 | measure | ≤ 2.5s | ≤ 1.5s |
| Agent task completion rate (benchmark suite) | measure | ≥ 80% | ≥ 92% |
| Cost per assisted conversation | measure | −30% vs baseline | −50% vs baseline |
| Prompt-injection suite: successful attacks | measure | 0 critical | 0 critical, 0 high |
| Cross-user/tenant leakage tests | n/a | 0 failures (blocking) | 0 failures (blocking) |
| Provider-outage user impact | full outage | degraded-mode answer | transparent failover |

## Hard rules — inherited, non-negotiable, every task

1. **Tool-use, never free-text-to-SQL.** Every data access is a typed tool running as `actor` =
   request user. RBAC + data scope + audit always hold. (`DECISIONS.md` — already decided.)
2. **Writes are human-in-the-loop.** Model proposes; typed confirm executes through module
   contracts + `erp.audit.services.record(...)`. Never write to `erp/audit/models.py` directly.
3. **Additive.** Extend `client.py`, `tools.py`, `api/urls.py` — don't rewrite. Existing endpoints
   keep working until an acceptance task retires them explicitly.
4. **No new dependencies without asking.** Each phase file lists its "Decision points" — new
   packages/extensions are proposed there and require user approval before the task that needs
   them starts. If denied, every such task has a no-new-dep fallback spelled out.
5. **Frontend:** design tokens only, logical CSS only, every string in BOTH `ar.json` and
   `en.json`, designed empty/error/loading states, settled motion, no new npm deps.
6. **Arabic-first.** Every eval set, attack corpus, and golden dataset is ar + en. Arabic is not
   the translation — it is the primary case.
7. **Gates before "done":** backend `pytest erp/assistant`; from `apps/web`:
   `node scripts/check-i18n-parity.mjs` + `npx tsc --noEmit`; repo root
   `python scripts/gates/gate03.py` when UI touched.
8. **`Docs/ARP_STRATEGY.md` governs scope.** If a task here conflicts with strategy or with
   `Docs/plan/arp-roadmap.md` sequencing, the strategy doc wins — stop and flag.

## Task format (identical in every phase file)

Every task is one agent session (~20–40 min) and carries:

- **Goal** — one sentence, testable.
- **Prereq** — tasks/files that must exist first. If a prereq is missing, STOP and report.
- **Files** — exact paths to read and to create/modify.
- **Steps** — numbered, deterministic. No step says "appropriately" or "as needed".
- **Accept** — objective pass/fail criteria, including the test command.
- **Output** — what exists after the task that didn't before.

Execution protocol (same as ai-workspace-plan): new session → paste FILE_00 + the next `FILE_NN`
phase file → do the next unchecked task → run its Accept block → commit → mark the task's
checkbox in the phase file → fresh session. When all tasks in a phase are checked and the phase
acceptance passes, append `_done` to the phase file name. A `_done` file is never reopened.

## Never touch

- `erp/audit/models.py` (append-only; use `erp.audit.services.record`)
- `apps/web/src/styles/tokens.css` (no new raw hex)
- `apps/web/src/lib/money.ts` (one money formatter)
- Existing module `contracts.py` signatures
- Other apps' migrations

## Relationship to other plans

This roadmap is the **AI engineering track**. It runs alongside (not instead of) the product
track in `Docs/plan/arp-roadmap.md`. Phase 6's tenant-isolation tasks assume the SaaS
multitenancy work (`Docs/plan/06-saas-multitenancy.md`) has landed; if it hasn't, those tasks
park (marked in FILE_06). Nothing here blocks the product queue: linear-polish → unified-ui →
ai-workspace 13–15 → smart-import finish first.

## Amendments

- **2026-07-16 — Twenty CRM AI study** (`TWENTY_AI_STUDY.md` in this folder): source-level study
  of Twenty's AI system → FILE_05 gained T5.9 (detached durable streaming, executes after T5.1)
  and T5.10 (structured clarify + mid-turn cost stop, executes after T5.5); FILE_03 T3.6 gained
  the context meter + stable-prefix rule; FILE_07 T7.2/T7.5 gained the progressive-disclosure
  trigger + provider prompt caching; FILE_08 T8.3 gained sampled live-turn grading. All marked
  `[Twenty study 2026-07-16]` in place. T5.2–T5.8 numbering untouched (cross-referenced).

*Generated 2026-07-08. Grounded in erp/assistant as of commit dc8ecc6.*
