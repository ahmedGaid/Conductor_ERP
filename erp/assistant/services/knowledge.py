"""Knowledge base: chunking, ingestion, and search over uploaded company documents.

RAG for the assistant. Documents are chunked into overlapping slices; each slice carries a
Postgres tsvector (config "simple") so search works for Arabic and English without a stemmer.
Session 02 adds ingestion, session 03 adds search + optional embeddings.
"""
from __future__ import annotations

from django.contrib.postgres.search import SearchVector

from erp.audit import services as audit

from ..client import complete_stream
from ..models import KnowledgeChunk, KnowledgeDocument
from . import files

# ~1200 chars per chunk keeps a retrieved set of 6 chunks well inside the prompt budget;
# 200-char overlap preserves sentences cut at a boundary.
CHUNK_CHARS = 1200
CHUNK_OVERLAP = 200

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


def _extract_text(*, data: bytes, media_type: str, filename: str) -> str:
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
        text = _extract_text(data=data, media_type=media_type, filename=filename)
    except Exception as exc:  # never re-raise — the failure lands on the row, blame-free
        return _fail(doc, str(exc) or "extraction failed")
    text = (text or "").strip()
    if not text:
        return _fail(doc, "no readable text")

    chunks = chunk_text(text)
    KnowledgeChunk.objects.bulk_create(
        [KnowledgeChunk(document=doc, seq=i, text=c) for i, c in enumerate(chunks)]
    )
    KnowledgeChunk.objects.filter(document=doc).update(
        search=SearchVector("text", config="simple")
    )
    doc.status = "ready"
    doc.chunk_count = len(chunks)
    doc.save(update_fields=["status", "chunk_count", "updated_at"])
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
