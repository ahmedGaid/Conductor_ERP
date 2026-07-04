"""Knowledge base: chunking, ingestion, and search over uploaded company documents.

RAG for the assistant. Documents are chunked into overlapping slices; each slice carries a
Postgres tsvector (config "simple") so search works for Arabic and English without a stemmer.
Session 02 adds ingestion, session 03 adds search + optional embeddings.
"""
from __future__ import annotations

# ~1200 chars per chunk keeps a retrieved set of 6 chunks well inside the prompt budget;
# 200-char overlap preserves sentences cut at a boundary.
CHUNK_CHARS = 1200
CHUNK_OVERLAP = 200


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
