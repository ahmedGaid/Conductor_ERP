"""ai-reliability T3.4 — Arabic normalization wired into ingestion + query preprocessing.

Real-DB tests: prove the normalized-shadow tsvector actually changes matching behavior (a
diacritized/tatweel/hamza-alef spelling variant now matches its plain-spelling counterpart, in
either direction), and that ``reingest_knowledge`` brings pre-T3.4 chunks in line, idempotently.
"""
from __future__ import annotations

from django.contrib.postgres.search import SearchVector
from django.core.management import call_command

from erp.assistant.models import KnowledgeChunk, KnowledgeDocument
from erp.assistant.services import knowledge
from erp.identity.models import User

pytestmark = __import__("pytest").mark.django_db


def _admin(username: str) -> User:
    u = User.objects.create_user(username=username, password="Dev12345!",
                                 email=f"{username}@example.test")
    u.is_superuser = True
    u.save(update_fields=["is_superuser"])
    return u


def _ingest(body: str, title: str, actor) -> KnowledgeDocument:
    return knowledge.ingest_document(
        data=body.encode("utf-8"), media_type="text/plain",
        filename=f"{title}.txt", title=title, actor=actor,
    )


# --- ingestion normalizes the tsvector ------------------------------------------------------------

def test_diacritized_document_matches_plain_query():
    actor = _admin("norm_ingest_diac")
    _ingest("يَجِبُ عَلَى الْمُسَجَّلِ تَقْدِيمُ الْإِقْرَارِ الضَّرِيبِيِّ.", "VAT Filing", actor)
    results = knowledge.search("يجب على المسجل تقديم الاقرار الضريبي")
    assert results
    assert results[0]["title"] == "VAT Filing"


def test_plain_document_matches_diacritized_query():
    actor = _admin("norm_ingest_plain")
    _ingest("يجب على المسجل تقديم الإقرار الضريبي.", "VAT Filing Plain", actor)
    results = knowledge.search("يَجِبُ عَلَى الْمُسَجَّلِ الْإِقْرَارِ الضَّرِيبِيِّ")
    assert results
    assert results[0]["title"] == "VAT Filing Plain"


def test_alef_hamza_variant_matches_bare_alef():
    actor = _admin("norm_alef")
    _ingest("أحمد مسؤول عن اعتماد أمر الشراء.", "Approval", actor)
    results = knowledge.search("احمد مسؤول عن اعتماد امر الشراء")
    assert results
    assert results[0]["title"] == "Approval"


def test_alef_maksura_variant_matches_ya():
    actor = _admin("norm_maksura")
    _ingest("يحتفظ الموظف بنسخة من الطلب حتى يصل إلى المدير.", "Delivery", actor)
    results = knowledge.search("يحتفظ الموظف بنسخة من الطلب حتي يصل الي المدير")
    assert results
    assert results[0]["title"] == "Delivery"


def test_ta_marbuta_not_confused_with_ha():
    # a chunk about "مدرسة" (school) must not surface for a query about "مدره" (a different,
    # unrelated token) — proves MERGE_TA_MARBUTA=False is actually honored end to end.
    actor = _admin("norm_ta_marbuta")
    _ingest("سياسة تدريب الموظفين الجدد في المدرسة الداخلية.", "Training", actor)
    results = knowledge.search("مدره")
    assert not any(r["title"] == "Training" for r in results)


def test_stored_text_stays_raw():
    actor = _admin("norm_raw_storage")
    doc = _ingest("اَلْمُوَظَّفُونَ يَسْتَحِقُّونَ إِجَازَة.", "Leave", actor)
    chunk = KnowledgeChunk.objects.get(document=doc)
    assert chunk.text == "اَلْمُوَظَّفُونَ يَسْتَحِقُّونَ إِجَازَة."  # untouched, diacritics intact


# --- reingest_knowledge: rebuilds legacy (pre-T3.4) chunks -----------------------------------------

def _legacy_chunk(title: str, text: str) -> KnowledgeChunk:
    """A chunk indexed the OLD way (tsvector built straight from raw text, no normalization) —
    simulates a document ingested before the T3.4 normalizer shipped."""
    doc = KnowledgeDocument.objects.create(
        title=title, filename=f"{title}.txt", media_type="text/plain", status="ready",
    )
    chunk = KnowledgeChunk.objects.create(document=doc, seq=0, text=text)
    KnowledgeChunk.objects.filter(id=chunk.id).update(search=SearchVector("text", config="simple"))
    return chunk


def test_reingest_knowledge_fixes_legacy_diacritized_chunk():
    _legacy_chunk("Legacy Refund", "سِيَاسَةُ الِاسْتِرْجَاعِ تَسْمَحُ بِالْإِرْجَاعِ خِلَالَ أَرْبَعَةَ عَشَرَ يَوْمًا.")

    # before reingest: the legacy tsvector still carries raw diacritics, so a plain-spelling query
    # matching only via tsvector (no vector arm) finds nothing — this documents the bug T3.4 fixes.
    before = knowledge.search("سياسة الاسترجاع تسمح بالارجاع")
    assert not any(r["title"] == "Legacy Refund" for r in before)

    call_command("reingest_knowledge", batch=200, sleep=0)

    after = knowledge.search("سياسة الاسترجاع تسمح بالارجاع")
    assert any(r["title"] == "Legacy Refund" for r in after)


def test_reingest_knowledge_is_idempotent():
    _legacy_chunk("Idempotent Doc", "سياسة الإجازات السنوية والمرضية.")
    call_command("reingest_knowledge", batch=200, sleep=0)
    first = list(KnowledgeChunk.objects.filter(document__title="Idempotent Doc").values_list("search", flat=True))
    call_command("reingest_knowledge", batch=200, sleep=0)
    second = list(KnowledgeChunk.objects.filter(document__title="Idempotent Doc").values_list("search", flat=True))
    assert first == second


def test_reingest_knowledge_reports_count(capsys):
    _legacy_chunk("Count Doc A", "نص تجريبي أول.")
    _legacy_chunk("Count Doc B", "نص تجريبي ثاني.")
    call_command("reingest_knowledge", batch=1, sleep=0)  # batch=1 exercises the pagination loop
    out = capsys.readouterr().out
    assert "reindexed" in out
