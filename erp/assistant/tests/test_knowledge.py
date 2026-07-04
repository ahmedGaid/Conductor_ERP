"""Knowledge base: models + chunker (session 01) + ingestion pipeline + API (session 02)."""
from __future__ import annotations

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import override_settings
from rest_framework.test import APIClient

from erp.assistant.models import KnowledgeChunk, KnowledgeDocument
from erp.assistant.services import knowledge
from erp.assistant.services.knowledge import CHUNK_CHARS, CHUNK_OVERLAP, chunk_text
from erp.identity.models import User

pytestmark = pytest.mark.django_db

KNOW_URL = "/api/assistant/knowledge"


def _admin(username: str = "know_admin") -> User:
    u = User.objects.create_user(username=username, password="Dev12345!",
                                 email=f"{username}@example.test")
    u.is_superuser = True  # admin-level → the knowledge gate passes
    u.save(update_fields=["is_superuser"])
    return u


def _nobody(username: str = "know_nobody") -> User:
    return User.objects.create_user(username=username, password="Dev12345!",
                                    email=f"{username}@example.test")


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


# --- ingestion service -------------------------------------------------------------------------

def test_ingest_text_document_creates_ready_chunks():
    actor = _admin("ingest_text")
    doc = knowledge.ingest_document(
        data=b"First paragraph.\n\nSecond paragraph.", media_type="text/plain",
        filename="sop.txt", title="SOP", actor=actor,
    )
    assert doc.status == "ready"
    assert doc.chunk_count >= 1
    chunks = KnowledgeChunk.objects.filter(document=doc)
    assert chunks.count() == doc.chunk_count
    assert all(c.search is not None for c in chunks)  # tsvector populated


def test_ingest_failure_lands_on_row(monkeypatch):
    actor = _admin("ingest_fail")

    def _boom(*_a, **_k):
        raise RuntimeError("provider down")

    monkeypatch.setattr(knowledge, "complete_stream", _boom)
    doc = knowledge.ingest_document(  # no exception must escape
        data=b"\x89PNG\r\n", media_type="image/png", filename="scan.png",
        title="Scan", actor=actor,
    )
    assert doc.status == "failed"
    assert doc.error_text
    assert doc.chunk_count == 0


def test_ingest_empty_text_is_failed(monkeypatch):
    actor = _admin("ingest_empty")
    monkeypatch.setattr(knowledge, "complete_stream", lambda *_a, **_k: iter([]))
    doc = knowledge.ingest_document(
        data=b"\x89PNG\r\n", media_type="image/png", filename="blank.png",
        title="Blank", actor=actor,
    )
    assert doc.status == "failed"
    assert doc.error_text == "no readable text"


# --- API ---------------------------------------------------------------------------------------

@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_knowledge_api_requires_role():
    client = APIClient()
    client.force_authenticate(user=_nobody())
    txt = SimpleUploadedFile("s.txt", b"hello", content_type="text/plain")
    assert client.get(KNOW_URL).status_code == 403
    assert client.post(KNOW_URL, {"file": txt}, format="multipart").status_code == 403
    assert client.delete(f"{KNOW_URL}/1").status_code == 403


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_knowledge_upload_and_delete_roundtrip():
    client = APIClient()
    client.force_authenticate(user=_admin("roundtrip"))
    txt = SimpleUploadedFile("policy.txt", b"Returns within 14 days.", content_type="text/plain")
    created = client.post(KNOW_URL, {"file": txt, "title": "Returns"}, format="multipart")
    assert created.status_code == 201
    data = created.json()["data"]
    assert data["status"] == "ready" and data["chunk_count"] >= 1

    listed = client.get(KNOW_URL).json()["data"]
    assert any(d["id"] == data["id"] for d in listed)

    assert client.delete(f"{KNOW_URL}/{data['id']}").status_code == 204
    assert not KnowledgeDocument.objects.filter(id=data["id"]).exists()
    assert not KnowledgeChunk.objects.filter(document_id=data["id"]).exists()  # cascade


@override_settings(ASSISTANT_ENABLED=True, ASSISTANT_PROVIDER="anthropic")
def test_upload_rejects_oversize_and_bad_type(monkeypatch):
    from erp.assistant.api import views

    client = APIClient()
    client.force_authenticate(user=_admin("reject"))

    monkeypatch.setattr(views, "MAX_UPLOAD_BYTES", 4)
    big = SimpleUploadedFile("big.txt", b"way too many bytes", content_type="text/plain")
    assert client.post(KNOW_URL, {"file": big}, format="multipart").status_code == 400

    bad = SimpleUploadedFile("a.zip", b"PK\x03\x04", content_type="application/zip")
    assert client.post(KNOW_URL, {"file": bad}, format="multipart").status_code == 400
