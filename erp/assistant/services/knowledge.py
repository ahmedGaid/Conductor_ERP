"""Knowledge base: chunking, ingestion, and search over uploaded company documents.

RAG for the assistant. Documents are chunked into overlapping slices; each slice carries a
Postgres tsvector (config "simple") so search works for Arabic and English without a stemmer.
Session 02 adds ingestion, session 03 adds search + optional embeddings.
"""
from __future__ import annotations

from django.conf import settings
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db import connection
from django.db.models import F, Q, Value

from erp.audit import services as audit

from .. import client  # only for client.embed_text (T2.1 exception — see gateway invariant test)
from .. import textnorm
from ..gateway import cache as semantic_cache
from ..gateway.core import complete_stream
from ..models import KnowledgeChunk, KnowledgeDocument
from . import files

# ~1200 chars per chunk keeps a retrieved set of 6 chunks well inside the prompt budget;
# 200-char overlap preserves sentences cut at a boundary.
CHUNK_CHARS = 1200
CHUNK_OVERLAP = 200

# ai-reliability T3.2 — hybrid retrieval by Reciprocal Rank Fusion. The FTS arm and the vector arm
# each produce a ranked id-list; a chunk's fused score is Σ 1/(RRF_K + rank) over the arms it
# appears in. Rank fusion is robust to the incomparable score scales of tsrank vs cosine — which is
# exactly why it replaces the old 0.5/0.5 blend. Each arm contributes its top RRF_ARM_DEPTH ids.
RRF_K = 60
RRF_ARM_DEPTH = 20

# ai-reliability T3.1 — pgvector semantic arm. `embedding_v` is a raw-SQL-managed `vector(768)`
# column (Gemini text-embedding-004 dim), NOT a Django field, so ordinary ORM queries never touch
# it and search stays byte-identical wherever the column is absent. It only comes alive when the
# migration added the column (server has the `vector` extension) AND ASSISTANT_PGVECTOR is on.
EMBED_DIM = 768

_vector_col_present: bool | None = None  # cached; the column only appears/disappears via migration


def _has_vector_column() -> bool:
    """True when the pgvector ``embedding_v`` column exists (migration 0010 added it). Cached for
    the process — schema doesn't change under us; tests that rebuild schema call
    :func:`_reset_vector_cache`."""
    global _vector_col_present
    if _vector_col_present is None:
        if connection.vendor != "postgresql":
            _vector_col_present = False
        else:
            with connection.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_name = 'assistant_knowledgechunk' AND column_name = 'embedding_v'"
                )
                _vector_col_present = cur.fetchone() is not None
    return _vector_col_present


def _reset_vector_cache() -> None:
    """Drop the cached column-presence answer (tests only)."""
    global _vector_col_present
    _vector_col_present = None


def _vector_literal(vec: list[float]) -> str:
    """Format an embedding as a pgvector text literal ('[a,b,...]') for ``%s::vector`` binding.

    Asserts the dimension so a model change that alters the embedding size fails loudly here
    instead of writing a vector Postgres would reject at insert time.
    """
    if len(vec) != EMBED_DIM:
        raise ValueError(f"embedding dim {len(vec)} != expected {EMBED_DIM}")
    return "[" + ",".join(repr(float(x)) for x in vec) + "]"


def _write_vector_column(chunk_id: int, vec: list[float]) -> None:
    """Dual-write the vector column alongside the legacy JSON ``embedding`` (T3.1 keeps both until
    Phase 7 removes the JSON one). No-op safety is the caller's — only called when the column exists."""
    with connection.cursor() as cur:
        cur.execute(
            "UPDATE assistant_knowledgechunk SET embedding_v = %s::vector WHERE id = %s",
            [_vector_literal(vec), chunk_id],
        )


def vector_search_ids(q_emb: list[float], *, limit: int = 20) -> list[int]:
    """Top-``limit`` chunk ids by pgvector cosine distance via the HNSW index scan.

    The dedicated vector arm introduced in T3.1 — an ``ORDER BY embedding_v <=> query LIMIT n``
    that the HNSW index serves directly (the pg-only test asserts the index scan in EXPLAIN).
    T3.2 fuses this arm with the FTS arm by RRF; T3.1 only makes it exist and be indexed. Empty
    list when the flag is off or the column is absent."""
    if not (getattr(settings, "ASSISTANT_PGVECTOR", False) and _has_vector_column()):
        return []
    with connection.cursor() as cur:
        cur.execute(
            "SELECT id FROM assistant_knowledgechunk WHERE embedding_v IS NOT NULL "
            "ORDER BY embedding_v <=> %s::vector LIMIT %s",
            [_vector_literal(q_emb), limit],
        )
        return [row[0] for row in cur.fetchall()]

# Plain-text uploads decoded locally; csv/xlsx flattened via the files.py helpers; everything
# else (images / PDF) is transcribed through the provider's vision path.
_PLAIN_TEXT_TYPES = {"text/plain", "text/markdown"}
_TRANSCRIBE_INSTRUCTION = (
    "Transcribe the full text content of this document faithfully, in its original language. "
    "Output only the transcribed text, no commentary."
)


def chunk_text(text: str) -> list[str]:
    """Split extracted text into overlapping chunks, preferring paragraph boundaries.

    Greedy: pack whole paragraphs up to CHUNK_CHARS; a paragraph longer than the budget is
    hard-split with CHUNK_OVERLAP carry-over. Never returns empty strings.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) + 2 <= CHUNK_CHARS:
            current = f"{current}\n\n{para}" if current else para
            continue
        if current:
            chunks.append(current)
            current = ""
        while len(para) > CHUNK_CHARS:
            chunks.append(para[:CHUNK_CHARS])
            para = para[CHUNK_CHARS - CHUNK_OVERLAP:]
        current = para
    if current:
        chunks.append(current)
    return chunks


def _index_search_vectors(doc: KnowledgeDocument) -> None:
    """Build each chunk's tsvector from the ai-reliability T3.4 normalized shadow of its text — the
    stored ``text`` column stays raw (embeddings and the display text need the original spelling).
    Shared by :func:`ingest_document` and the ``reingest_knowledge`` management command so index-time
    normalization has exactly one code path, never two implementations drifting apart."""
    for chunk in KnowledgeChunk.objects.filter(document=doc):
        chunk.search = SearchVector(Value(textnorm.normalize_ar(chunk.text)), config="simple")
        chunk.save(update_fields=["search"])


def _extract_text(*, data: bytes, media_type: str, filename: str, actor=None) -> str:
    """Plain text out of any allowed upload.

    txt/md: decoded locally. csv/xlsx: flattened through the files.py table helpers (REUSED, not
    reimplemented). pdf/images: transcribed through the existing vision path (``complete_stream``
    with the file as media) — no PDF library, the same seam chat already uses.
    """
    ct = (media_type or "").lower()
    if ct in files.CSV_TYPES:
        return files._describe_csv(filename, data)
    if ct == files.XLSX_TYPE:
        return files._describe_xlsx(filename, data)
    if ct in _PLAIN_TEXT_TYPES:
        return data.decode("utf-8-sig", errors="replace")
    # images / pdf → provider vision transcription; join the streamed chunks into one string.
    parts = complete_stream(
        [{"role": "user", "content": _TRANSCRIBE_INSTRUCTION}],
        media=[{"media_type": ct, "data": data}],
        feature="extract", actor=actor,
    )
    return "".join(parts)


def ingest_document(*, data: bytes, media_type: str, filename: str, title: str, actor):
    """Create the document row, extract → chunk → index. Synchronous and bounded.

    Any extraction failure is captured on the row (status="failed", error_text ≤255) — the caller
    always gets the row back, never an exception (mirrors notifications.dispatch's posture).
    """
    doc = KnowledgeDocument.objects.create(
        title=title, filename=filename, media_type=(media_type or ""), size=len(data),
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
    )
    try:
        text = _extract_text(data=data, media_type=media_type, filename=filename, actor=actor)
    except Exception as exc:  # never re-raise — the failure lands on the row, blame-free
        return _fail(doc, str(exc) or "extraction failed")
    text = (text or "").strip()
    if not text:
        return _fail(doc, "no readable text")

    chunks = chunk_text(text)
    KnowledgeChunk.objects.bulk_create(
        [KnowledgeChunk(document=doc, seq=i, text=c) for i, c in enumerate(chunks)]
    )
    _index_search_vectors(doc)
    # Optional semantic index: one embedding per chunk when ASSISTANT_RAG_EMBEDDINGS is on. An
    # outage returns None per call and never fails ingestion (search stays FTS-only for this doc).
    try:
        vector_col = _has_vector_column()  # dual-write embedding_v when pgvector column exists (T3.1)
        for chunk in KnowledgeChunk.objects.filter(document=doc):
            vec = client.embed_text(chunk.text)
            if vec is None:
                continue
            chunk.embedding = vec
            chunk.save(update_fields=["embedding"])
            if vector_col:
                _write_vector_column(chunk.id, vec)
    except Exception:  # embeddings are an enhancement — ingestion must survive their outage
        pass
    doc.status = "ready"
    doc.chunk_count = len(chunks)
    doc.save(update_fields=["status", "chunk_count", "updated_at"])
    # T2.8: new content invalidates every cached knowledge-Q&A answer at once — cheaper than
    # checking per-row relevance, and correct (an old answer may now be stale or incomplete).
    semantic_cache.bump(semantic_cache.SEMANTIC_CACHE_TASK)
    audit.record(
        module="assistant", action="knowledge_ingest", entity_type="KnowledgeDocument",
        entity_id=doc.id, actor=actor, after={"title": title, "chunks": len(chunks)},
    )
    return doc


def _fail(doc: KnowledgeDocument, error_text: str) -> KnowledgeDocument:
    doc.status = "failed"
    doc.error_text = error_text[:255]
    doc.save(update_fields=["status", "error_text", "updated_at"])
    return doc


def delete_document(doc_id: int, actor) -> None:
    """Delete one document (chunks cascade) + audit. No-op if it's already gone."""
    doc = KnowledgeDocument.objects.filter(pk=doc_id).first()
    if doc is None:
        return
    title = doc.title
    doc.delete()
    audit.record(
        module="assistant", action="knowledge_delete", entity_type="KnowledgeDocument",
        entity_id=doc_id, actor=actor, after={"title": title},
    )


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


def _row(chunk: KnowledgeChunk, score: float, *, arms: list[str] | None = None) -> dict:
    return {
        "document_id": chunk.document_id,
        "title": chunk.document.title,
        "seq": chunk.seq,
        "text": chunk.text,
        "score": round(float(score), 4),
        # T3.2 provenance: which retrieval arms surfaced this chunk (["fts"], ["vec"], or both).
        # Consumed by T3.3 metrics and shown in the ops trace detail.
        "arms": list(arms or []),
    }


def _pgvector_active() -> bool:
    """The pgvector semantic arm is live: flag on AND the migration added the column."""
    return bool(getattr(settings, "ASSISTANT_PGVECTOR", False)) and _has_vector_column()


def _vector_arm(q_emb: list[float] | None, fts_candidates: list[KnowledgeChunk]) -> list[int]:
    """The semantic ranked id-list that RRF fuses with the FTS arm.

    Prefers the pgvector HNSW scan over the whole corpus (T3.1 ``vector_search_ids``) — which can
    surface a chunk the FTS arm missed entirely. Without pgvector it degrades to ranking the FTS
    candidate pool by Python cosine over the legacy JSON ``embedding`` column: a bounded second
    ordering (the decision-point fallback — "RRF fuses FTS + capped-scan lists"). Empty when no
    embedding is available at all, so search degrades to a pure-FTS pass-through with no branching
    at the call site.
    """
    if not q_emb:
        return []
    hnsw = vector_search_ids(q_emb, limit=RRF_ARM_DEPTH)
    if hnsw:
        return hnsw
    scored = sorted(
        ((_cosine(q_emb, c.embedding), c.id) for c in fts_candidates if c.embedding),
        key=lambda t: t[0], reverse=True,
    )
    return [cid for _score, cid in scored]


def _rrf_fuse(arms: dict[str, list[int]], *, k: int = RRF_K) -> list[tuple[int, float, list[str]]]:
    """Reciprocal Rank Fusion over named ranked id-lists (k defaults to the standard 60).

    Each value is an ordered list of chunk ids (position 1 = rank 1). A chunk's fused score is
    ``Σ_arm 1/(k + rank_arm)`` over the arms it appears in; absence from an arm contributes no
    term. Returns ``[(chunk_id, fused_score, arms_present), ...]`` best first.

    A single non-empty arm degrades to that arm's own order (the score is rank-monotonic), so
    callers need no single-arm special case. Exact ties — perfectly symmetric ranks across arms —
    break toward the arm listed LAST in ``arms``: callers pass the semantic (vector) arm last so
    that when lexical and semantic evidence are exactly balanced, semantic similarity decides.
    """
    order = list(arms.keys())
    scores: dict[int, float] = {}
    ranks: dict[int, dict[str, int]] = {}
    for arm_name in order:
        for rank, cid in enumerate(arms[arm_name], start=1):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
            ranks.setdefault(cid, {})[arm_name] = rank

    def _key(cid: int):
        # Highest fused score first; on a tie, better rank in the later-listed (semantic) arms
        # first — absence from an arm sorts last; chunk id is the final deterministic tiebreak.
        by_arm = tuple(ranks[cid].get(a, 1 << 30) for a in reversed(order))
        return (-scores[cid], by_arm, cid)

    return [
        (cid, round(scores[cid], 6), [a for a in order if a in ranks[cid]])
        for cid in sorted(scores, key=_key)
    ]


def _load_chunks(ids: set[int], fts_candidates: list[KnowledgeChunk]) -> dict[int, KnowledgeChunk]:
    """Map fused ids → chunk objects, reusing the already-loaded FTS candidates and fetching only
    the vector-only ids from ready documents (a vector hit from a non-ready doc is dropped here)."""
    have = {c.id: c for c in fts_candidates if c.id in ids}
    missing = [i for i in ids if i not in have]
    if missing:
        for c in (KnowledgeChunk.objects.filter(id__in=missing, document__status="ready")
                  .select_related("document")):
            have[c.id] = c
    return have


def _trace_retrieval(trace, *, fts: int, vec: int, rows: list[dict], fused: bool) -> None:
    """Record the T3.2 retrieval step: per-arm candidate sizes, fused result size, top score."""
    if trace is None:
        return
    trace.step(
        kind="retrieval", name="knowledge",
        detail={"fts": fts, "vec": vec, "fused": len(rows),
                "top_score": rows[0]["score"] if rows else 0.0,
                "mode": "rrf" if fused else "icontains"},
    )


def search(query: str, *, limit: int = 6, trace=None) -> list[dict]:
    """Top matching chunks across ready documents, by hybrid retrieval.

    Two ranked arms — Postgres full-text (websearch, config "simple") and the vector arm (pgvector
    HNSW when ``ASSISTANT_PGVECTOR`` is on, else a bounded cosine re-rank of the FTS pool) — are
    fused by Reciprocal Rank Fusion (T3.2), replacing the old 0.5/0.5 score blend. A missing arm
    degrades to a single-list pass-through. When neither arm finds anything (common for Arabic
    morphology, rare terms) fall back to icontains on the raw query terms.

    ai-reliability T3.4: the FTS arm matches the :mod:`textnorm`-normalized shadow of each chunk
    (:func:`_index_search_vectors`), so the query is normalized the same way before it becomes a
    ``SearchQuery`` — one shared normalizer, index side and query side, never two implementations.
    The vector arm's embedding and the icontains fallback both use the RAW query: embeddings
    handle Arabic morphology natively, and icontains matches the raw stored chunk text.

    Returns [{"document_id", "title", "seq", "text", "score", "arms"}], best first — ``arms`` is
    the per-hit provenance (["fts"], ["vec"], or both). Empty list = genuinely nothing found, which
    the tool layer turns into an honest "no document covers this" (never fabricated documentation).
    ``trace`` (a tracing handle, optional) receives one ``kind="retrieval"`` step.
    """
    query = (query or "").strip()
    if not query:
        return []

    depth = max(RRF_ARM_DEPTH, limit)
    sq = SearchQuery(textnorm.normalize_ar(query), config="simple", search_type="websearch")
    fts_candidates = list(
        KnowledgeChunk.objects.filter(document__status="ready", search=sq)
        .annotate(rank=SearchRank(F("search"), sq))
        .select_related("document")
        .order_by("-rank")[:depth]
    )

    # Embed only when a vector arm can use it: whenever pgvector is live (whole-corpus HNSW scan),
    # or — without pgvector — only when there are FTS candidates to re-rank (no point otherwise).
    q_emb = client.embed_text(query) if (_pgvector_active() or fts_candidates) else None
    vec_ids = _vector_arm(q_emb, fts_candidates)
    fts_ids = [c.id for c in fts_candidates]

    if fts_ids or vec_ids:
        fused = _rrf_fuse({"fts": fts_ids, "vec": vec_ids})[:limit]
        chunks = _load_chunks({cid for cid, _s, _a in fused}, fts_candidates)
        rows = [_row(chunks[cid], score, arms=arms) for cid, score, arms in fused if cid in chunks]
        _trace_retrieval(trace, fts=len(fts_ids), vec=len(vec_ids), rows=rows, fused=True)
        return rows

    # Neither arm produced anything: OR the raw words (≥3 chars) via icontains — a lexical safety
    # net below the tsvector (Arabic morphology, rare terms).
    words = [w for w in query.split() if len(w) >= 3]
    if not words:
        _trace_retrieval(trace, fts=0, vec=0, rows=[], fused=False)
        return []
    term_q = Q()
    for w in words:
        term_q |= Q(text__icontains=w)
    fallback = list(
        KnowledgeChunk.objects.filter(document__status="ready")
        .filter(term_q)
        .select_related("document")[:limit]
    )
    rows = [_row(c, 0.0, arms=["icontains"]) for c in fallback]
    _trace_retrieval(trace, fts=0, vec=0, rows=rows, fused=False)
    return rows
