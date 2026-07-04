# Conductor AI — RAG, Source-Routing & Harness — Master Index

## Project Goal

Implement TWO system-prompt specs on top of the existing assistant: "Conductor AI — RAG & Tool
Usage" (four knowledge sources + a decision procedure) and "Conductor AI — Harness (Agent
Orchestrator)" (the orchestration layer: context collection, intent classification, planning,
tool routing, validation, confirmation, error recovery). Most of both specs is ALREADY built or
already planned — this plan delivers only the missing pieces:

1. **RAG knowledge base** — upload company documents (SOPs, policies, catalogs, manuals),
   chunk + index them, and let the agent loop search them with a `search_documents` tool.
2. **Source-routing system prompt** — encode the spec's decision procedure (live data → tools,
   documents → RAG, both → both, general → reasoning) and the never-invent rules into the
   context envelope and loop prompt.
3. **Transparency** — answers grounded in documents say so ("from company documentation") in
   both the prompt rules and the UI (distinct document-citation chips).
4. **Harness hardening** — richer context envelope (filters, unsaved changes, recent AI
   actions, org facts), intent classification, duplicate-call guard, and a declarative
   confirmation registry that makes destructive-without-confirm impossible by construction.

**Architectural note (harness spec):** the "Harness" is NOT a new service. `services/agent.py`'s
loop already IS the orchestrator — it plans one step at a time, runs typed tools as the actor,
validates, feeds errors back, gates writes behind confirmation, and only then lets the LLM
answer. Sessions 08–10 harden that loop to the spec; they do not build a second layer.

## Spec coverage map — what this plan does NOT redo

| Spec section | Where it lives | Status |
|---|---|---|
| ERP Tools priority, never answer live data from memory | `tools.py` + `services/agent.py` loop | DONE (sessions 08–09) |
| Action safety: explain → validate → confirm | ai-workspace FILE_10_SAFE_ACTIONS | planned there |
| Current page / selected record awareness | `services/context.py` + ai-workspace FILE_11 | done + planned there |
| Smart suggestions + deep links ("create it here…") | ai-workspace FILE_12_GUIDED_DETOURS | planned there |
| File upload → extract → compare with ERP → suggest create | FILE_07 done + ai-workspace FILE_14 | done + planned there |
| Blame-free tool-failure handling | `errors.py`, loop `{"error": …}` feedback | DONE |
| **RAG knowledge base + search tool** | **this plan, sessions 01–04** | NEW |
| **Source-selection decision procedure in prompt** | **this plan, session 05** | NEW |
| **Transparency: doc-sourced answers labeled, in prompt + UI** | **this plan, sessions 05 + 07** | NEW |
| Knowledge-base management UI | **this plan, session 06** | NEW |

## Harness-spec coverage map — what this plan does NOT redo

| Harness spec section | Where it lives | Status |
|---|---|---|
| Orchestration loop (understand → gather → validate → confirm → answer) | `services/agent.py::run` | DONE (session 09) |
| Context: page, module, record, user, permissions, language, company | `services/context.py` + ai-workspace FILE_11 | done + planned there |
| Knowledge-source priority (Tools → RAG → Memory → LLM) | this plan, sessions 04–05 | in this plan |
| Plans invisible unless requested; step progress streamed | loop `step` events | DONE |
| Never invent IDs/balances/prices; hallucination policy | this plan, session 05 | in this plan |
| Multi-step execution, reuse outputs, stop on failure | loop rounds + error feedback | DONE |
| File intelligence (extract → compare → suggest) | FILE_07 done + ai-workspace FILE_14 | done + planned there |
| Missing-entity handling (deep link, permission, "create it?") | ai-workspace FILE_12 | planned there |
| Permission awareness (tools/actions run as actor) | everywhere, by construction | DONE |
| Error recovery (explain, retry, alternatives, never fake success) | loop `{"error": …}` + `complete_json` retries | DONE |
| **Context: filters, unsaved changes, previous AI actions, branch/warehouse/fiscal year** | **this plan, session 08** | NEW |
| **Intent classification (recorded per turn)** | **this plan, session 09** | NEW |
| **Avoid duplicate tool calls (guard, not just prompt)** | **this plan, session 09** | NEW |
| **Confirmation required for destructive kinds, by construction** | **this plan, session 10** | NEW |

**Ordering rule:** finish ai-workspace `FILE_10_SAFE_ACTIONS` first (its work is already in the
working tree; this plan's session 10 builds ON it). Sessions 11–14 of that plan and this plan
are independent — recommended order: ai-workspace 10 → this plan 01–11 → ai-workspace 11–15,
so FILE_15 acceptance covers everything.

## Architecture decisions (locked)

- **Postgres full-text search is the baseline** (`django.contrib.postgres.search`, config
  `"simple"` — works acceptably for Arabic + English without stemming). Zero new dependencies.
- **Embeddings are an optional upgrade**, behind `ASSISTANT_RAG_EMBEDDINGS` (default off), using
  the Gemini embeddings API through the already-installed `google-genai` SDK. Stored in a
  `JSONField`, cosine computed in Python — fine at SMB scale (thousands of chunks). **No
  pgvector, no new packages.**
- **PDF/image text extraction reuses the vision path** (`client.complete_stream` with media) —
  a transcription prompt, not a new PDF library.
- **Search runs as the user; management needs an elevated role.** Same posture as everything
  else: tools run as `actor`. (Per-document ACLs are explicitly out of scope — note it in
  DECISIONS.md at acceptance.)
- **Tool-use, never free-text-to-SQL** (DECISIONS.md) still holds — `search_documents` is just
  another typed tool in the catalog.

## Session Map

| # | File | What gets built | Est. |
|---|---|---|---|
| 01 | FILE_01_KNOWLEDGE_MODELS.md | KnowledgeDocument + KnowledgeChunk models, chunker, migration | 20 min |
| 02 | FILE_02_INGESTION_API.md | Upload → extract text → chunk → index pipeline + CRUD API | 30 min |
| 03 | FILE_03_SEARCH_SERVICE.md | FTS search service + optional embeddings blend | 25 min |
| 04 | FILE_04_SEARCH_TOOL.md | `search_documents` tool in catalog + loop-prompt RAG routing | 25 min |
| 05 | FILE_05_SOURCE_ROUTING_PROMPT.md | Spec's source-selection + never-invent + transparency rules in prompts | 20 min |
| 06 | FILE_06_KNOWLEDGE_UI.md | Knowledge-base management page (upload, list, delete, status) | 30 min |
| 07 | FILE_07_DOC_CITATIONS_UI.md | Document citations rendered distinctly in chat | 20 min |
| 08 | FILE_08_CONTEXT_ENVELOPE_PLUS.md | Filters, unsaved-changes, recent AI actions, org facts in the envelope | 30 min |
| 09 | FILE_09_HARNESS_HARDENING.md | Intent classification + duplicate-call guard in the loop | 25 min |
| 10 | FILE_10_CONFIRM_REGISTRY.md | Declarative action kinds + destructive-requires-confirm enforcement | 25 min |
| 11 | FILE_11_ACCEPTANCE.md | Acceptance + regression + gates + sign-off (both specs) | 30 min |

Natural checkpoints (`---`): after session 05 (RAG backend + prompts → merge) and after
session 07 (RAG UI → merge); 08–10 are the harness slice.

## Affected files (exhaustive)

Backend (`erp/assistant/` unless noted):
- `models.py` (add two models), `migrations/0003_knowledge.py` (new)
- `services/knowledge.py` (new: chunker, ingestion, search, optional embeddings)
- `api/views.py`, `api/urls.py` (knowledge endpoints)
- `tools.py` (one new tool), `services/agent.py` (loop-prompt routing lines, intent field,
  duplicate-call guard)
- `services/context.py` (source-routing + transparency block; filters/dirty/recent-actions
  blocks), `services/ask.py` (answer-tone line)
- `services/actions.py` (kind + requires_confirm metadata, execute re-validation)
- `config/settings/base.py` (one setting: `ASSISTANT_RAG_EMBEDDINGS`)
- `tests/test_knowledge.py` (new), `tests/test_context.py`, `tests/test_agent.py`,
  `tests/test_actions.py` (extend)

Frontend (`apps/web/src/`):
- `api/assistant.ts` (knowledge API calls)
- `pages/assistant/KnowledgePage.tsx` (new) + route + nav entry
- `assistant/MessageList.tsx` (document-citation chip)
- `assistant/context.ts` (filters + dirty-flag collection)
- `assistant/assistant-panel.css` or the page css (chip + page styles, tokens only)
- `i18n/locales/ar.json`, `i18n/locales/en.json`

## Never touch

- `erp/audit/models.py` — append-only; write only via `erp.audit.services.record(...)`
- `apps/web/src/styles/tokens.css` — no new raw hex
- Existing module `contracts.py` signatures
- `TOOLS` entries that already exist — additive only
- The event protocol of `services/agent.py::run` (step/token/citations/proposal/done) — extend
  meta, never rename events
- No new npm or pip dependencies. Full stop.

## Ground Rules (every session)

1. **Read before write.** Every session starts with the named reads. Never write from memory.
2. **Additive.** Existing endpoints (`/ask`, `/chat`, `/extract-document`, `/status`,
   conversations CRUD) keep working untouched.
3. **AI runs as the user.** `search_documents` executes as `actor` like every other tool.
4. **Frontend hard rules:** tokens only, logical CSS only, every string in BOTH `ar.json` and
   `en.json`, designed empty/error/loading states, monochrome chrome, settled motion.
5. **Gates before "done":** `apps/web`: `node scripts/check-i18n-parity.mjs` + `npx tsc --noEmit`;
   repo root: `python scripts/gates/gate03.py`; backend: `pytest erp/assistant`.
6. **Done means renamed.** Session green + committed → rename its file with `_done` appended.
   Never reopen a `_done` file; next session = lowest-numbered file without the suffix.
7. **Prompt text is code.** Every prompt change lands with a test asserting its key phrases
   (pattern: `tests/test_context.py`). Keep prompts compact — they ride on every request.

## How to use this plan

1. New Claude Code session → paste `FILE_00_INDEX.md` + the next `FILE_NN` file.
2. Claude does the "Before You Start" reads, then the tasks, then the smoke test.
3. Smoke test green → run the gates → commit → rename with `_done` → `/compact` → next file in
   a fresh session.
4. One session file = one Claude session.

## After all sessions complete

- Run FILE_11 acceptance + regression in both languages (ar RTL first).
- Record in `DECISIONS.md`: RAG = Postgres FTS baseline + optional Gemini embeddings, no
  pgvector, per-document ACLs deferred; harness = the agent loop itself (no separate
  orchestrator service), destructive kinds require confirmation by construction.
- Update the `erp-status` skill anchor; resume the ai-workspace plan at its next open file.

*Generated by ag-plan skill. Do not edit this index manually.*
