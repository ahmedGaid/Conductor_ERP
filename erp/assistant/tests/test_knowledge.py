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


# --- search service ----------------------------------------------------------------------------

def _ingest_text(body: str, title: str, actor) -> KnowledgeDocument:
    return knowledge.ingest_document(
        data=body.encode("utf-8"), media_type="text/plain",
        filename=f"{title}.txt", title=title, actor=actor,
    )


def test_search_finds_english_chunk_by_fts():
    actor = _admin("search_en")
    _ingest_text("Shipping happens on weekdays only.", "Shipping", actor)
    _ingest_text("Refund policy: customers can return items within 14 days.", "Refunds", actor)
    results = knowledge.search("refund policy")
    assert results
    assert "Refund policy" in results[0]["text"]


def test_search_arabic_fallback():
    actor = _admin("search_ar")
    _ingest_text("سياسة الاسترجاع تسمح للعملاء بإرجاع المنتجات خلال ١٤ يوماً.", "Arabic", actor)
    results = knowledge.search("سياسة الاسترجاع")
    assert results
    assert "الاسترجاع" in results[0]["text"]


def test_search_ignores_processing_and_failed_docs(monkeypatch):
    actor = _admin("search_scope")
    _ingest_text("Refund policy allows returns within 14 days.", "Ready", actor)
    # a failed doc whose chunk text would otherwise match
    monkeypatch.setattr(knowledge, "complete_stream", lambda *_a, **_k: iter([]))
    failed = knowledge.ingest_document(
        data=b"\x89PNG\r\n", media_type="image/png", filename="x.png",
        title="Failed refund doc", actor=actor,
    )
    assert failed.status == "failed"
    # a processing doc with a matching chunk, never marked ready
    proc = KnowledgeDocument.objects.create(
        title="Processing", filename="p.txt", media_type="text/plain", status="processing",
    )
    KnowledgeChunk.objects.create(document=proc, seq=0, text="Refund policy draft.")
    KnowledgeChunk.objects.filter(document=proc).update(
        search=knowledge.SearchVector("text", config="simple")
    )
    results = knowledge.search("refund policy")
    assert results
    assert all(r["title"] == "Ready" for r in results)


def test_search_empty_result_is_empty_list():
    _admin("search_empty")
    assert knowledge.search("nonexistent zqxjw term") == []
    assert knowledge.search("") == []


# --- T3.9: confidence gate -----------------------------------------------------------------------

def test_is_confident_false_on_empty_or_zero_coverage():
    assert knowledge.is_confident([]) is False
    assert knowledge.is_confident([{"score": 0.0}]) is False


def test_is_confident_true_above_threshold_false_at_the_boundary_below():
    assert knowledge.is_confident([{"score": knowledge.CONFIDENCE_THRESHOLD}]) is True
    assert knowledge.is_confident([{"score": knowledge.CONFIDENCE_THRESHOLD + 0.001}]) is True
    assert knowledge.is_confident([{"score": knowledge.CONFIDENCE_THRESHOLD - 0.001}]) is False


def test_is_confident_only_looks_at_the_top_hit():
    rows = [{"score": knowledge.CONFIDENCE_THRESHOLD}, {"score": 0.0}]
    assert knowledge.is_confident(rows) is True
    assert knowledge.is_confident(list(reversed(rows))) is False


def test_icontains_score_scales_with_content_word_coverage():
    words = ["refund", "policy", "returns"]
    text = "Refund policy: customers can return items within 14 days."
    # "returns" is absent — 2 of 3 content words present.
    assert knowledge._icontains_score(text, words) == pytest.approx(
        (2 / 3) * knowledge.RANK1_SCORE)
    # Every content word present tops out on the single-arm rank-1 rung, so it reads as confident.
    full = knowledge._icontains_score(text, ["refund", "policy", "days"])
    assert full == pytest.approx(knowledge.RANK1_SCORE)
    assert knowledge.is_confident([{"score": full}]) is True
    # One common word out of five is the noisy end of the OR query — below the floor, a decline.
    thin = knowledge._icontains_score(text, ["refund", "vat", "payroll", "branch", "invoice"])
    assert knowledge.is_confident([{"score": thin}]) is False


def test_icontains_score_matches_through_arabic_normalization():
    # The query writes hamza-alef + diacritics, the document writes bare alef: same word after
    # normalize_ar, so coverage sees it (this is the morphology gap the tier exists to bridge).
    assert knowledge._icontains_score("سياسة الاسترجاع خلال ١٤ يوم", ["إسترجاع"]) == pytest.approx(
        knowledge.RANK1_SCORE)
    assert knowledge._icontains_score("سياسة الاسترجاع", []) == 0.0


@pytest.mark.django_db
def test_search_finds_documents_for_a_natural_language_question():
    """T3.9 regression: the tsvector uses config "simple" (no stopword dictionary) and websearch
    ANDs every term, so an unstripped question only matched a chunk containing "what"/"is"/"the"
    too — real questions fell to the icontains tier and read as unconfident. The query-side
    stopword strip puts them back on the FTS arm."""
    actor = _admin("nl_question")
    knowledge.ingest_document(
        data=b"Refund policy: customers can return items within 14 days.",
        media_type="text/plain", filename="refunds.txt", title="Refund Policy", actor=actor,
    )
    keyword_rows = knowledge.search("refund policy")
    question_rows = knowledge.search("what is the refund policy?")
    assert [r["title"] for r in question_rows] == [r["title"] for r in keyword_rows] == ["Refund Policy"]
    assert question_rows[0]["arms"] == keyword_rows[0]["arms"]
    assert knowledge.is_confident(question_rows) is True


def test_search_blends_embeddings_when_available(monkeypatch):
    actor = _admin("search_blend")
    # both match the "refund"&"policy" websearch query; FTS ranks A first (more occurrences)
    doc_a = _ingest_text("refund policy refund policy handling steps.", "A", actor)
    doc_b = _ingest_text("refund policy summary.", "B", actor)
    a_chunk = KnowledgeChunk.objects.get(document=doc_a)
    b_chunk = KnowledgeChunk.objects.get(document=doc_b)
    # hand-made vectors: query aligns with B, opposes A → B is the semantic winner
    a_chunk.embedding = [1.0, 0.0]
    a_chunk.save(update_fields=["embedding"])
    b_chunk.embedding = [0.0, 1.0]
    b_chunk.save(update_fields=["embedding"])
    monkeypatch.setattr(knowledge.client, "embed_text", lambda _q: [0.0, 1.0])
    results = knowledge.search("refund policy")
    assert results[0]["title"] == "B"


def test_ingest_survives_embedding_outage(monkeypatch):
    actor = _admin("ingest_emb_outage")

    def _boom(_text):
        raise RuntimeError("embeddings down")

    monkeypatch.setattr(knowledge.client, "embed_text", _boom)
    doc = _ingest_text("Refund policy within 14 days.", "Resilient", actor)
    assert doc.status == "ready"
    assert doc.chunk_count >= 1
    assert all(c.embedding is None for c in KnowledgeChunk.objects.filter(document=doc))
