# SESSION 11 — Acceptance + Regression + Sign-off
# Files: none new — verification, polish, DECISIONS.md, docs

---

## Before You Start

1. Re-read `FILE_00_INDEX.md` (this plan) — BOTH spec coverage maps (RAG spec + Harness spec)
   are the acceptance contract.
2. Ensure a seeded state: at least two knowledge documents (one Arabic policy, one English
   catalog/SOP), plus normal demo ERP data (`scripts/seed_demo.py` if needed).
3. Both languages get tested; Arabic RTL FIRST.

---

## Full acceptance checklist (the specs, verified end-to-end)

**Source routing**
- [ ] Live-data question (balances/stock/orders) → data tools only; numbers match the module pages
- [ ] Document question (policy/SOP/catalog term) → `search_documents` step + quoted passage + attribution
- [ ] Mixed question → both source kinds gathered before one combined answer
- [ ] General question (explain a concept) → direct answer, zero tool steps
- [ ] "What did I ask before?" → answered from history; history never invents a business fact

**Never invent**
- [ ] Nonexistent customer/supplier/item asked about → honest "not found", no invented values
- [ ] Question with no covering document → "no document covers this" (both languages), nothing fabricated
- [ ] Empty tool result → plain statement + nearest next step, not a guess

**Transparency**
- [ ] Doc-grounded answers carry "وفقاً لمستند…" / "according to…" wording AND the document chip
- [ ] Data-grounded answers carry record citations as before
- [ ] The assistant never claims to have read something it did not retrieve (probe: "did you
      check the contract?" when no search ran)

**Knowledge base**
- [ ] Upload txt / pdf / image / xlsx → ready with sensible chunk counts; unreadable → failed row, calm error
- [ ] Oversize + disallowed type rejected with blame-free copy
- [ ] Role gate: plain user — no nav entry, 403 on API, non-link citation chips
- [ ] Delete cascades; search stops finding deleted content immediately
- [ ] `ASSISTANT_RAG_EMBEDDINGS` off → everything above still passes (FTS-only)

**Harness: context envelope**
- [ ] On a filtered list page: "what am I looking at?" → filters reflected in the answer
- [ ] Unsaved form changes → assistant acknowledges them before suggesting navigation
- [ ] "What did you just do?" after an executed proposal → answered from the recent-actions
      block, no tools re-run
- [ ] Single-shot `/ask` path unaffected (no conversation kwarg — regression)

**Harness: orchestration discipline**
- [ ] Multi-part question → distinct tool steps, outputs reused across rounds, no identical
      step chip twice (duplicate-call guard)
- [ ] `meta.intent` recorded on every assistant turn
- [ ] Planner forced past MAX_ROUNDS still answers with what it has (never spins)
- [ ] Tool failure mid-plan → calm explanation + alternative, never fabricated success

**Harness: action safety**
- [ ] Every registered action declares a kind; destructive kinds cannot exist without
      confirmation (import-time assert verified once)
- [ ] Execute re-checks permission + re-validates before writing; stale/revoked → calm refusal,
      zero writes
- [ ] Double-confirm of one proposal refused (status guard)

**Error handling**
- [ ] Provider key removed → assistant surfaces the existing blame-free unavailable state; no crash
- [ ] Embedding outage (bad key + flag on) → ingestion and search still work

## Regression checklist (must still work untouched)

- [ ] `/ask` single-shot, `/chat` streaming, cancel, regenerate
- [ ] Conversations CRUD, pin/archive/search; attachments in chat (image/PDF/CSV/XLSX)
- [ ] `/extract-document` invoice flow; write proposals + confirm cards (ai-workspace session 10)
- [ ] All pre-existing tools answer correctly; `query_data` grammar unchanged
- [ ] SSE event protocol unchanged (step/token/citations/proposal/done — client renders as before)
- [ ] `pytest erp/assistant` fully green; web gates green
      (`check-i18n-parity`, `tsc --noEmit`, `gate03.py`)

## Micro-polish pass (apply if missing)

- [ ] Knowledge empty-state copy reads like the brand (quiet, precise) in both languages
- [ ] Status chips align vertically with the app's other status words
- [ ] Loading skeleton timing uses the token motion scale
- [ ] `catalog_text()` output reviewed once by eye — tool descriptions read consistently
- [ ] `_LOOP_SYSTEM` re-read once end-to-end — no contradictory or duplicated instructions
      after all the additions

## Sign-off block

Record, then close:

- **Built:** RAG knowledge base (models, ingestion, FTS + optional Gemini-embedding search,
  `search_documents` tool, loop routing, source-of-truth + transparency prompt rules,
  management UI, document citation chips) + harness hardening (richer context envelope:
  filters/dirty/recent-actions/org facts; intent classification; duplicate-call guard;
  declarative confirmation registry with destructive-kind enforcement).
- **Not touched:** audit models, tokens.css, contracts signatures, existing tool entries,
  agent event protocol, no new dependencies.
- **DECISIONS.md:** add — "RAG = Postgres FTS ('simple') baseline + optional Gemini embeddings
  in JSONField (no pgvector); per-document ACLs deferred; document ingestion synchronous.
  Harness = the agent loop itself (no separate orchestrator service); intent is recorded
  metadata, not a router; every destructive action kind requires confirmation by construction."
- Run the `conductor-brand` brand-feel checklist on the knowledge page + chat chips.
- Update the `erp-status` skill anchor: this plan `_done`, next = ai-workspace plan's lowest
  open file (FILE_11 or wherever it stands).

```
All boxes green?
→ Commit, rename this file FILE_11_ACCEPTANCE_done.md
→ Merge to main. Fresh session for the next task.
```
