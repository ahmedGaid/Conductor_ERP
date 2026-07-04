# SESSION 3 — Search Service (+ optional embeddings)
# Files: erp/assistant/services/knowledge.py, config/settings/base.py, erp/assistant/client.py, erp/assistant/tests/test_knowledge.py

---

## Before You Start

1. Open `erp/assistant/services/knowledge.py` → re-read `ingest_document` as committed.
2. Open `config/settings/base.py` → find the block where `ASSISTANT_*` settings are read from
   env (ASSISTANT_ENABLED, ASSISTANT_MAX_TOKENS, keys) — note the exact env-reading idiom.
3. Open `erp/assistant/client.py` → confirm `get_gemini_client()` exists (it does) — the
   optional embedding call goes through it.

Do not write anything yet.

---

## Task A — The setting

In `config/settings/base.py`, next to the other `ASSISTANT_*` settings, using the same
env idiom:

```python
ASSISTANT_RAG_EMBEDDINGS = <env bool>("ASSISTANT_RAG_EMBEDDINGS", default=False)
```

## Task B — Embedding seam in `client.py`

At the end of `erp/assistant/client.py`:

```python
# --- knowledge-base embeddings (rag plan session 03) -------------------------------------------
# Optional semantic ranking for document search. Gemini-only (the SDK is already a dependency);
# any other provider or a failure returns None and search falls back to full-text alone.

EMBEDDING_MODEL = "text-embedding-004"


def embed_text(text: str) -> list[float] | None:
    """One embedding vector, or None when embeddings are off/unavailable. Never raises."""
    if not getattr(settings, "ASSISTANT_RAG_EMBEDDINGS", False) or not settings.GEMINI_API_KEY:
        return None
    try:
        resp = get_gemini_client().models.embed_content(
            model=EMBEDDING_MODEL, contents=text[:8000],
        )
        return list(resp.embeddings[0].values)
    except Exception:  # embeddings are an enhancement — search must survive their outage
        return None
```

## Task C — Search in `services/knowledge.py`

Append:

```python
def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


def search(query: str, *, limit: int = 6) -> list[dict]:
    """Top matching chunks across ready documents.

    Ranking: Postgres full-text (websearch syntax, config "simple") is the baseline. When a
    query embedding is available, full-text candidates are re-ranked by blending cosine
    similarity with the FTS rank. When FTS finds nothing (common for Arabic morphology),
    fall back to icontains on the raw query terms.

    Returns [{"document_id", "title", "seq", "text", "score"}], best first. Empty list =
    genuinely nothing found — the tool layer turns that into an honest "no document covers
    this" (never fabricated documentation).
    """
```

Body rules:
- FTS: `SearchQuery(query, config="simple", search_type="websearch")`, filter
  `document__status="ready"`, annotate `SearchRank(F("search"), sq)`, order by rank desc,
  take `limit * 4` candidates.
- Embedding blend: `q_emb = client.embed_text(query)`; if not None, for candidates that have a
  stored embedding compute `score = 0.5 * norm_rank + 0.5 * cosine`; else `score = rank`.
  Re-sort, cut to `limit`.
- Fallback when FTS yields zero rows: split the query into words ≥ 3 chars, OR-filter
  `text__icontains` on each, take `limit`, `score = 0.0`.
- Also update `ingest_document` (Task C of session 02): after chunks are created, when
  `client.embed_text` returns vectors, store one per chunk (loop; skip on None). Keep this
  inside the same try/except — an embedding outage must not fail ingestion.

## Task D — Tests

Extend `tests/test_knowledge.py`:

- test_search_finds_english_chunk_by_fts — ingest "Refund policy: customers can return items
  within 14 days." → `search("refund policy")` returns it first
- test_search_arabic_fallback — ingest an Arabic paragraph containing "سياسة الاسترجاع" →
  `search("سياسة الاسترجاع")` returns it (FTS or icontains fallback — either path)
- test_search_ignores_processing_and_failed_docs
- test_search_empty_result_is_empty_list — no fabricated rows
- test_search_blends_embeddings_when_available — monkeypatch `client.embed_text` to return
  hand-made vectors making the SECOND FTS candidate the semantic winner → it ranks first
- test_ingest_survives_embedding_outage — monkeypatch `embed_text` to raise/return None →
  status still "ready"

---

## Smoke Test

- [ ] `pytest erp/assistant/tests/test_knowledge.py` green
- [ ] `pytest erp/assistant` green
- [ ] Shell: ingest two small docs, `knowledge.search("<term from doc 1>")` → doc 1's chunk
      first, sensible score
- [ ] Arabic term search returns the Arabic chunk
- [ ] With `ASSISTANT_RAG_EMBEDDINGS` unset → search works (FTS-only path)

---

## After This Session

```
Smoke test passed?
→ Commit, rename this file FILE_03_SEARCH_SERVICE_done.md
→ Type /compact in Claude Code
→ Open FILE_04_SEARCH_TOOL.md and continue
```
