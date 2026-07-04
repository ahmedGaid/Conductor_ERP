"""Knowledge base: models + chunker (plan session 01)."""
from __future__ import annotations

import pytest
from django.db import IntegrityError, transaction

from erp.assistant.models import KnowledgeChunk, KnowledgeDocument
from erp.assistant.services.knowledge import CHUNK_CHARS, CHUNK_OVERLAP, chunk_text

pytestmark = pytest.mark.django_db


def test_chunk_text_packs_paragraphs_under_budget():
    text = "alpha\n\nbeta\n\ngamma"
    chunks = chunk_text(text)
    assert len(chunks) == 1
    assert "alpha" in chunks[0]
    assert "beta" in chunks[0]
    assert "gamma" in chunks[0]


def test_chunk_text_splits_long_paragraph_with_overlap():
    para = "x" * 3000
    chunks = chunk_text(para)
    assert len(chunks) >= 2
    # chunk[1] starts with the last CHUNK_OVERLAP chars of chunk[0]
    assert chunks[1].startswith(chunks[0][CHUNK_CHARS - CHUNK_OVERLAP:])


def test_chunk_text_empty_input_returns_empty_list():
    assert chunk_text("") == []
    assert chunk_text("   \n\n   ") == []


def test_knowledge_document_defaults():
    doc = KnowledgeDocument.objects.create(
        title="Returns policy", filename="returns.pdf", media_type="application/pdf",
    )
    assert doc.status == "processing"
    assert doc.chunk_count == 0


def test_chunk_unique_per_doc_seq():
    doc = KnowledgeDocument.objects.create(
        title="SOP", filename="sop.txt", media_type="text/plain",
    )
    KnowledgeChunk.objects.create(document=doc, seq=0, text="first")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            KnowledgeChunk.objects.create(document=doc, seq=0, text="dup")
