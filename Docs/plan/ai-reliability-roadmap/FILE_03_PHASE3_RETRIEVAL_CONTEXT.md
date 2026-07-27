# Phase 3 (Months 7–9) — Retrieval & Context Engineering v2

## Objectives

1. Retrieval quality becomes measurable and state-of-practice: hybrid FTS + vector with rank
   fusion and a rerank stage, Arabic-normalized end to end.
2. The context envelope gets a token budget manager: every section counted, prioritized,
   truncated by policy — context overflow becomes structurally impossible.
3. Long conversations stay coherent via rolling summaries instead of silent truncation.
4. "I don't know" becomes a designed, honest answer backed by a retrieval-confidence threshold.

## Architecture decisions

- **pgvector is the vector store.** No external vector DB (customer-hosted, one database to
  operate). Embeddings move from a Python-scanned column to a `vector` column with an HNSW index.
  Everything keeps working without the extension (feature-flagged fallback to today's blend) so
  installs without pgvector don't break — parity with the existing "assistant is optional" stance.
- **Hybrid = Reciprocal Rank Fusion (RRF).** tsvector ranking and vector similarity each produce a
  ranked list; RRF (k=60) fuses them. Replaces the current 0.5/0.5 score blend — rank fusion is
  robust to incomparable score scales, which is exactly the tsrank-vs-cosine problem.
- **Arabic normalization is one shared function** applied at BOTH index and query time (alef
  variants → ا, ta marbuta → ه handling documented, tatweel + diacritics stripped). One function,
  imported by ingestion and search — never two implementations.
- **Rerank is an LLM task class (`rerank`), not a new dependency.** Top-20 fused candidates →
  cheapest routed model scores relevance 0–3 per chunk in one batched call → top-5 enter the
  prompt. Cached via exact cache. If eval shows no lift over fusion alone, rerank stays off — the
  eval decides, not fashion.
- **Context budget manager owns the envelope.** Sections (system, persona, page context, memory
  [Phase 4], retrieval, history, summary) each declare priority + max share; the manager measures
  (provider tokenizer where available, `len//3` heuristic otherwise), trims lowest-priority first,
  and records final composition in the trace (`meta.envelope = {section: tokens}`).

## Decision points (ask user before dependent task)

- **pgvector Postgres extension** (T3.1) — requires `CREATE EXTENSION vector` + the `pgvector`
  pip package. Fallback if denied: keep Python-side cosine, cap candidates, skip T3.2's vector
  arm (RRF fuses FTS + capped-scan lists instead). All later tasks still work.
- No other new dependencies.

## Success metrics (phase exit)

- Retrieval eval set (built T3.3): recall@5 ≥ 0.85, MRR ≥ 0.75 on golden retrieval queries
  (baseline measured before T3.1 lands for comparison).
- Groundedness on citation golden cases ≥ 95%; wrong-citation rate < 2%.
- Zero `context_overflow` error traces after T3.6 ships (was: whatever Phase 1 measured).
- Envelope median tokens reduced ≥ 25% vs Phase 1 baseline at equal eval pass rate.

---

## Tasks

### [x] T3.1 — pgvector migration (flagged)

> **STATUS 2026-07-25 — code complete, flag-off half verified; flag-on live verify GATED on the
> Postgres `vector` binary.** Built: settings flag `ASSISTANT_PGVECTOR`; guarded reversible
> migration `0010_knowledgechunk_pgvector` (raw-SQL `vector(768)` column + HNSW index, added only
> when the server has the extension — skips silently otherwise, so it's a true no-op on this
> Windows PG16 which has no `vector` extension); `embedding_v` managed by raw SQL **outside the
> ORM** so flag-off search is byte-identical wherever the column is absent; dual-write in
> `ingest_document`; `backfill_embeddings --batch --sleep` (resumable, idempotent); flag-on search
> re-scores the FTS candidate set via the pgvector `<=>` operator (same 0.5/0.5 blend, DB-sourced
> cosine) + a dedicated `vector_search_ids()` index-scan arm for T3.2 to fuse. Verified locally:
> full `pytest erp/assistant` green (flag-off, byte-identical); `makemigrations --check` clean;
> pure `_vector_literal` dim-assert test. **Gated (like the ETA sandbox round-trip):** the pg-only
> tests (`@pytest.mark.pgvector`: HNSW index-scan via EXPLAIN, backfill idempotency, flag-on DB
> cosine) auto-skip until `CREATE EXTENSION vector` is possible — install the pgvector binary into
> PG16, then run `pytest -m pgvector` + `ASSISTANT_PGVECTOR=1` smoke to close the flag-on Accept.

- **Goal:** chunk embeddings live in a `vector` column with an HNSW index; flag-gated.
- **Prereq:** Phase 2 done; user approved the decision point.
- **Files:** read `services/knowledge.py`, `models.py` (Chunk); migration; settings flag
  `ASSISTANT_PGVECTOR`.
- **Steps:**
  1. Migration: `CREATE EXTENSION IF NOT EXISTS vector` (guarded — skip with warning if the DB
     user lacks rights, flag stays off), add `embedding_v vector(<dim>)` (dim from the current
     `embed_text` output; assert at write time), HNSW index (`m=16, ef_construction=64`,
     cosine ops).
  2. Dual-write: ingestion writes both old JSON column and new vector column while the flag is
     off; backfill command `backfill_embeddings --batch 200 --sleep 0.5` (throttled, resumable by
     last-id checkpoint).
  3. Search: when flag on, vector arm = `ORDER BY embedding_v <=> query` LIMIT 20 (index scan)
     replacing the Python cosine loop; semantic cache (T2.8) lookup migrates to the same operator.
  4. Old JSON embedding column removal is deliberately deferred to Phase 7 cleanup — dual columns
     until proven.
- **Accept:** with flag off: all existing knowledge tests green, byte-identical behavior. With
  flag on (dev): same test suite green via the vector path; backfill idempotent (run twice, same
  rows); EXPLAIN shows index scan (assert in a pg-only test marked `@pytest.mark.pgvector`).
- **Output:** vector search that scales past toy corpus size.

### [x] T3.2 — Hybrid retrieval with RRF

> **STATUS 2026-07-26 — done, flag-agnostic (works with or without the pgvector binary).**
> `knowledge.search()` now runs two ranked arms and fuses them by Reciprocal Rank Fusion
> (`RRF_K=60`, `RRF_ARM_DEPTH=20`), replacing the old 0.5/0.5 blend (the T3.1 `_db_cosine_scores`
> blend helper is now removed as dead). Arms: **FTS** (tsvector top-20) and **vector** — the
> pgvector HNSW scan (`vector_search_ids`) when `ASSISTANT_PGVECTOR` is on, else a bounded cosine
> re-rank of the FTS pool over the legacy JSON `embedding` column (the decision-point fallback).
> Pure `_rrf_fuse()` handles single-arm degrade (pass-through) and breaks exact rank-symmetry ties
> toward the semantic arm (passed last). Each hit carries `arms` provenance (`["fts"]`/`["vec"]`/
> both, `["icontains"]` for the last-resort lexical fallback). One `kind="retrieval"` TraceStep
> (arm sizes, fused size, top score, mode) is recorded on the agent run — threaded via a reserved
> `_trace` kwarg through `agent._run_tool` → every tool's `**_` → `search_documents` only. Live
> chat (`views.run_agent`) records it; the ops UI already renders `kind="retrieval"`. Backend-only
> — no apps/web / i18n / model / migration change. **Verified:** `pytest erp/assistant` 534 passed
> / 5 skipped (pgvector-gated auto-skip), new `test_knowledge_rrf.py` 8 tests (5 pure RRF math incl.
> single-arm degrade + tie-break, 3 DB provenance/trace), `makemigrations --check` clean, `manage.py
> check` clean. The three pgvector-gated semantic tests pass unchanged under RRF (the semantic-arm
> tie-break preserves their "vector winner surfaces first" assertion) — re-confirm on a box with the
> `vector` binary when T3.1's flag-on gate is closed.

- **Goal:** FTS and vector lists fuse by rank, replacing the 0.5/0.5 score blend.
- **Prereq:** T3.1 (either arm).
- **Files:** modify `services/knowledge.py` `search()`; keep public signature.
- **Steps:**
  1. Run both arms (tsvector top-20, vector top-20), fuse: `score(d) = Σ 1/(60 + rank_i(d))`.
  2. Missing arm (no embeddings / flag off) degrades to single-list pass-through — same function,
     no branching at call sites.
  3. Return fused top-N with per-arm provenance in each hit (`hit.arms = ["fts", "vec"]`) —
     needed by T3.3 metrics and shown in ops trace detail.
  4. TraceStep `kind="retrieval"` records arm sizes, fused size, top score.
- **Accept:** unit tests with constructed rankings verify RRF math incl. single-arm degrade;
  existing knowledge search tests still green (update expected ordering only where the fixture
  comment explains why fusion reorders it).
- **Output:** retrieval robust to score-scale mismatch.

### [x] T3.3 — Retrieval eval set + metrics

> **STATUS 2026-07-26 — done, fully offline (no provider / key / pgvector binary).** New pure
> metrics `evals/retrieval_metrics.py` (recall@5/10, MRR, nDCG@10 with exponential gain + log2
> discount) unit-tested against hand-computed values (`tests/test_retrieval_metrics.py`, 13 tests).
> Fixture corpus `datasets/retrieval_corpus_v1.jsonl` = 24 single-chunk ERP docs (14 ar / 10 en:
> VAT, e-invoice, supplier/PO, inventory, payroll, leave, GL/assets, AR aging, RMA, cash flow…);
> query set `datasets/retrieval_v1.jsonl` = 84 labelled queries (54 ar / 30 en), graded 0/1/2 by
> `doc_key`. Suite `evals/retrieval.py` builds the corpus in a rolled-back txn and scores three
> strategies — `fts` (lexical baseline), `blend` (the removed 0.5·tsrank+0.5·cosine pre-fusion
> baseline, reconstructed to measure against), `fusion` (shipped RRF). Offline via a committed
> deterministic bag-of-tokens embedding (`fixture_embed`) patched over `client.embed_text`. New
> `run_evals --suite retrieval` writes `results/retrieval_<date>.json` + the standing
> `results/retrieval_baseline_vs_fusion.json`; runs in ~8s (<60s). **Numbers (offline fixture):**
> fts & fusion recall@5 0.935 / recall@10 0.988 / MRR 0.728 / nDCG@10 0.783 (identical — the crude
> fixture cosine adds no lexical signal beyond tsrank and RRF preserves the FTS order); `blend`
> collapses to recall@5 0.310, showing RRF's robustness to an incomparable second signal — the
> score-scale fragility T3.2 removed (fusion vs blend +0.625 recall@5 ≫ the +5-point bar; caveat
> in the results `note`: a live embedding narrows the gap; a true recall lift needs the
> whole-corpus pgvector HNSW arm, still flag/binary-gated from T3.1). Verified: `pytest erp/assistant`
> green incl. new `tests/test_retrieval_eval.py` (6, marked `retrieval`) + metrics (13);
> `makemigrations --check` clean; `manage.py check` clean. No model / migration / apps.web / i18n
> change. **Next (T3.4):** Arabic normalization pipeline — measure the ar recall lift on this suite.

- **Goal:** recall@k and MRR are computed per search, per language, in CI.
- **Prereq:** T3.2.
- **Files:** create `evals/datasets/retrieval_v1.jsonl`, `evals/retrieval_metrics.py`; extend
  `run_evals`.
- **Steps:**
  1. Dataset: ≥ 80 queries (≥ 50 ar) over a fixture corpus (committed sample docs — realistic ERP
     content: policy docs, supplier contracts, VAT circulars), each with labeled relevant chunk
     ids (graded 0/1/2).
  2. Metrics: recall@5, recall@10, MRR, nDCG@10 — pure functions, unit-tested against hand-computed
     examples.
  3. Runner mode `run_evals --suite retrieval`: builds the fixture corpus in a test DB, ingests,
     searches, scores. Fully offline (embeddings for fixtures recorded once like T1.6 recordings).
  4. Record pre-fusion baseline (blend) vs post-fusion in `evals/results/` — the fusion change
     must show ≥ +5 recall@5 points or be investigated before proceeding.
- **Accept:** suite runs offline < 60s; metrics unit tests green; baseline-vs-fusion comparison
  file committed.
- **Output:** retrieval changes are provable, forever.

### [x] T3.4 — Arabic normalization pipeline

> **STATUS 2026-07-26 — done.** New `erp/assistant/textnorm.py::normalize_ar` — one shared pure
> function: strips tatweel + standard harakat + dagger alif, unifies alef-hamza/madda variants
> (أ إ آ ٱ → ا) and alef maksura (ى → ي), keeps ta marbuta distinct from ha by default
> (`MERGE_TA_MARBUTA = False`, documented decision + flip point in the module docstring),
> lowercases Latin. 33 unit tests (`tests/test_textnorm.py` 24 pure-function cases incl.
> idempotency + docstring examples; `tests/test_knowledge_textnorm.py` 9 DB cases proving the
> wiring actually changes matching behavior both directions + ta-marbuta is honored end to end).
> Wired into `services/knowledge.py`: `_index_search_vectors()` builds each chunk's tsvector from
> the normalized shadow of its text (raw `text` column untouched — stored/displayed/embedded text
> stays original spelling); `search()` normalizes the query the same way before building the
> `SearchQuery`. Embeddings and the icontains fallback both stay on RAW text (embeddings handle
> Arabic morphology natively; icontains matches the raw stored column) — stated in code comments.
> New `reingest_knowledge` management command (throttled `--batch`/`--sleep`, resumable by
> last-id, idempotent by construction — the tsvector is a pure recomputation every run) rebuilds
> pre-T3.4 chunks; proven idempotent and effective on a simulated legacy chunk in
> `test_reingest_knowledge_fixes_legacy_diacritized_chunk` / `..._is_idempotent`.
>
> **Eval delta:** added 10 `q_ar_norm_*` queries to `retrieval_v1.jsonl` (realistic hamza-drop /
> alef-maksura spelling variants of terms already in the fixture corpus, referencing existing
> `doc_key`s — 94 queries total, 64 ar / 30 en, both minimums still cleared). Scored the SAME
> shipped `knowledge.search` twice — `textnorm.normalize_ar` patched to identity (before) vs the
> real normalizer (after) — recorded in `evals/results/retrieval_arabic_normalization_delta.json`:
> **ar MRR +0.031, ar nDCG@10 +0.024, ar recall@5/10 unchanged** (the icontains safety-net and
> shared-word cosine overlap already recovered these docs within top-10 pre-normalization; the
> normalizer's effect here is a genuine RANKING lift — the correct doc moves higher — not a
> recall-count change), **en fully unchanged** (0.0000 delta on every metric, as expected — no
> Arabic transform touches Latin text beyond casing). Standing `retrieval_baseline_vs_fusion.json`
> re-run and committed against the expanded 94-query set (the per-run dated file stays gitignored,
> same convention as every earlier task).
> **Verified:** `pytest erp/assistant` 586 passed / 5 skipped (pgvector-gated); `makemigrations
> --check` clean (no model change — tsvector rebuild is data-only); `manage.py check` clean.
> Backend-only — no apps/web / i18n / migration change.

- **Goal:** one shared normalizer applied at index + query time; measurable recall lift on Arabic.
- **Prereq:** T3.3 (to measure the lift).
- **Files:** create `erp/assistant/textnorm.py`; modify `services/knowledge.py` (ingest + search);
  re-ingest hook.
- **Steps:**
  1. `normalize_ar(text)`: strip tatweel + diacritics; unify alef (أإآٱ → ا); unify ya (ى → ي);
     keep ta marbuta distinct by default (ة ≠ ه) with a documented constant to flip — decision
     recorded in the module docstring with examples. Latin text passes through lowercased.
     Pure function, exhaustive unit tests with real Arabic samples.
  2. Apply in ingestion (chunk text stored raw; normalized shadow used for tsvector) and in query
     preprocessing. Embeddings are computed on RAW text (models handle Arabic natively;
     normalization is for lexical matching only) — state this in code comment.
  3. `reingest_knowledge` management command (throttled, resumable) to rebuild search columns.
  4. Run retrieval suite before/after — record Arabic recall@5 delta in `evals/results/`.
- **Accept:** normalizer unit tests green; retrieval suite shows Arabic recall not lower (target:
  higher) and English unchanged; re-ingest idempotent.
- **Output:** Arabic search that survives spelling variance.

### [ ] T3.5 — LLM rerank stage (eval-gated)

- **Goal:** top-20 fused → top-5 by LLM relevance scoring, kept only if evals show lift.
- **Prereq:** T3.3, gateway `rerank` task class routing (add in this task).
- **Files:** create `services/rerank.py`, `prompts/rerank.md`; modify `services/knowledge.py`;
  routing settings.
- **Steps:**
  1. Prompt (registered): query + numbered chunk excerpts → strict JSON `[{i, score 0-3}]`.
     One call for all 20 (batched), cheapest routed model, exact-cached (T2.5 allowlist +
     `rerank`).
  2. Fail-open: rerank error/timeout → fused order stands (TraceStep records `rerank_skipped`).
  3. Flag `ASSISTANT_RERANK`; run retrieval suite with/without: keep ON only if nDCG@10 ≥ +3
     points and added p95 latency ≤ 400ms (cache warm). Record the decision + numbers in
     `evals/results/rerank_decision.json`.
  4. Latency guard: rerank runs only when the fused top-2 scores are close (ambiguity gate,
     threshold in settings) — obvious wins skip it.
- **Accept:** offline tests via recordings; fail-open test; decision file committed with numbers.
- **Output:** better top-5 when it matters, no cost when it doesn't.

### [x] T3.6 — Context budget manager

- **Goal:** the envelope assembles within an explicit token budget; overflow is impossible.
- **Prereq:** T3.2 (retrieval section), Phase 1 traces.
- **Files:** create `services/envelope.py`; modify `services/context.py`, `services/ask.py`,
  `services/agent.py`.
- **Steps:**
  1. Section registry: each envelope contributor registers `(name, priority, max_share,
     content, degrade_fn)`. Priorities (high→low): system+persona, page record snapshot, retrieval,
     recent history, older history, suggestions context. `degrade_fn` produces a shorter form
     (e.g. retrieval: 5→3 chunks; history: drop oldest turns) — degradation is per-section logic,
     owned by the section.
  2. Budget = model context window (per-model table in gateway) − max_tokens − safety margin
     (10%). Manager measures each section (tokenizer via provider SDK when available, else
     heuristic), then trims lowest priority first, calling `degrade_fn` before dropping outright.
  3. Final composition into `Trace.meta.envelope` (tokens per section + trimmed flags).
  4. Replace all ad-hoc truncation currently in `context.py` with manager calls — grep for
     slicing/`[:n]` on context strings; each replaced site listed in the commit message.
  5. `[Twenty study 2026-07-16]` Make context health VISIBLE: the `done` SSE event carries
     `{conversation_tokens, budget_tokens}` (manager already measured both); the panel renders a
     quiet meter (tokens only appear on hover — the bar is enough), and any trim/degrade emits one
     calm, designed notice ("تم تلخيص أجزاء قديمة من المحادثة" / "Older parts of this conversation
     were summarized") instead of silent truncation. Twenty ships this as message metadata +
     a `data-compaction` event; same idea, our SSE protocol.
  6. `[Twenty study 2026-07-16]` Section ORDER is part of the registry contract: stable sections
     (system, persona, tool catalog) always render first and byte-identically across requests;
     volatile sections (page, date, record snapshot) render last or ride the user turn. This is the
     precondition for provider prompt caching (T7.5) — document it in `envelope.py`'s module
     docstring so no later session reorders sections casually.
- **Accept:** unit tests: over-budget input → correct trim order, never exceeds budget; empty
  sections skipped; trace records composition. Golden evals pass rate unchanged. Agent + ask
  smoke green. Meter + compaction notice: i18n parity, tsc, gate03, brand checklist.
- **Output:** `context_overflow` error class goes extinct — and the user can see why the
  assistant never loses the thread.

### [x] T3.7 — Rolling conversation summaries

- **Goal:** threads beyond N turns carry a maintained summary instead of losing early turns.
- **Prereq:** T3.6.
- **Files:** modify Conversation model (add `summary`, `summary_upto_message` FK, migration);
  create `services/summarize.py`, `prompts/thread_summary.md`; hook into chat flow.
- **Steps:**
  1. Trigger: after a completed assistant turn, if tokens(history beyond the last 10 turns) >
     1500 and summary is stale (> 5 turns behind), enqueue summary refresh — runs post-response
     (never blocks the stream; same async pattern as digest tasks).
  2. Summary prompt: prior summary + turns since → updated summary capped 300 tokens, MUST
     preserve: open user goals, referenced record ids, pending confirmations, language of the
     thread. Cheapest routed task class (`digest` tier).
  3. Envelope: "older history" section replaced by the summary via T3.6's registry (summary
     section priority just above older-history).
  4. Eval: 5 long-thread golden cases (ar+en) where the answer depends on turn-3 information at
     turn-25 — must pass with summarization active.
- **Accept:** unit tests for trigger logic + staleness; long-thread eval cases pass; summary
  refresh visible as `feature="digest"` trace.
- **Output:** long threads stay cheap AND coherent.
- **STATUS: DONE 2026-07-28.** `Conversation.summary` + `summary_upto_message` (migration
  `0012_conversation_summary_and_more`); `services/summarize.py` (`TAIL_MESSAGES=20` mirrors
  `agent._HISTORY_TURNS`, `STALE_MESSAGE_GAP=10`, `TOKEN_TRIGGER=1500` — trigger reads as "≥10
  new older messages AND their tokens > 1500"); `prompts/thread_summary.md`; refresh calls
  `gateway.core.complete_json(feature="digest", ...)`, fail-open like rerank.py (a provider
  error just keeps the prior summary). Hooked into both `agent.run` and `agent.resume_detour`
  right after their `_persist()` — fire-and-forget via new Celery task
  `assistant.refresh_thread_summary` (`tasks.py`), never blocking the SSE stream.
  `_recent_turns` now excludes messages already folded into the summary
  (`id__gt=summary_upto_message_id`); `_loop_user` carries the summary as its own envelope
  section (priority 1, between `gathered`@0 and `history`@2) surfaced in the round payload as
  `earlier_conversation_summary`. New eval suite `evals/long_thread.py` (`--suite long_thread`)
  — 5 golden cases (3 ar / 2 en, `datasets/long_thread_v1.jsonl`) each seed a conversation past
  both trigger thresholds with a fact planted at turn 3, drive real `summarize.refresh_summary`
  to convergence through a deterministic fixture summarizer, then run one real `agent.run` round
  with the planner decision captured — asserts the fact reaches the constructed prompt
  specifically via the summary (`found_via_summary`), not raw history. All 5 pass. 12 new unit
  tests (`test_summarize.py`: trigger/staleness/refresh/Celery hand-off) + 4 new `test_agent.py`
  tests (envelope wiring, `_recent_turns` filtering, post-persist hook timing). Verified: full
  `pytest erp` 1758 passed / 6 skipped (was 1650/5 pre-session — 108 net new, all T3.7's), golden
  eval suite unchanged (118 pass / 30 fail, byte-identical failing-id set to the 2026-07-23
  baseline — pre-existing fixture drift, not a T3.7 regression), retrieval suite unchanged,
  `makemigrations --check` + `manage.py check` clean.

### [ ] T3.8 — Page-context distillation

- **Goal:** the page/record context section becomes a compact typed snapshot, not a raw dump.
- **Prereq:** T3.6.
- **Files:** read `services/context.py` + frontend `assistant/context.ts`; modify both.
- **Steps:**
  1. Server-side: for each module's record type already supported by page context, define a
     `distill_<type>()` returning the fields an assistant actually needs (id, display name,
     status, key amounts as formatted strings, counts, open issues) — target ≤ 150 tokens per
     record. Table-driven registry keyed by the existing page-context type strings.
  2. Unknown/unregistered types: fall back to today's behavior but capped by the budget manager
     (no regression, no crash).
  3. Frontend collector unchanged in shape — distillation is server-side only (keeps client thin
     and versionable).
  4. Measure: envelope `page` section median tokens before/after in traces — target −50% on the
     five most-used pages.
- **Accept:** unit tests per distiller (fixture record → expected snapshot); golden page-context
  eval cases (from ai-workspace FILE_11 behavior) still pass; token reduction recorded in
  BASELINE.md.
- **Output:** page awareness at a fraction of the token bill.

### [ ] T3.9 — "I don't know" discipline + phase acceptance

- **Goal:** below-confidence retrieval yields a designed honest no-answer, never a guess; phase
  signed off.
- **Prereq:** T3.2 (fused scores), T3.5 decision.
- **Files:** modify `services/ask.py`; prompts; frontend empty-answer state; eval cases.
- **Steps:**
  1. Threshold: if fused top score < threshold (tuned on the retrieval eval set: pick the value
     that maximizes F1 of answer/no-answer on labeled unanswerable queries — add 15 unanswerable
     queries to the retrieval dataset), the ask prompt switches to a registered "insufficient
     sources" variant that must decline with what it looked for + one next step (upload the doc,
     rephrase, link to knowledge page). Blame-free wording, ar/en, conductor-brand checked.
  2. Designed state in the panel for the no-answer card (icon + one line + action — never bare
     text).
  3. Add 10 golden refusal-with-path cases; grader asserts decline + presence of a next step.
  4. Phase acceptance: run full eval + retrieval suites; update BASELINE.md (recall/MRR/
     groundedness/envelope tokens); verify success metrics at top of this file; check all boxes;
     rename `_done`.
- **Accept:** unanswerable eval cases pass ≥ 90%; no golden regression; BASELINE.md updated.
- **Output:** trust: the assistant that says "I don't know" is the one users believe when it
  says "I know".
