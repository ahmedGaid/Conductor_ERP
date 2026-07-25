"""ai-reliability T3.1 — pgvector semantic arm.

The pure formatter test runs everywhere. The DB tests are marked ``pgvector`` and skip themselves
where the Postgres ``vector`` extension is absent (community/Windows installs, most dev boxes) —
migration 0010 skips the column there, so there is nothing to exercise.
"""
from __future__ import annotations

import pytest
from django.core.management import call_command
from django.db import connection

from erp.assistant.models import KnowledgeChunk, KnowledgeDocument
from erp.assistant.services import knowledge
from erp.assistant.services.knowledge import EMBED_DIM, SearchVector
from erp.identity.models import User

pytestmark = pytest.mark.django_db


def _axis(i: int) -> list[float]:
    """A 768-dim unit vector along axis ``i`` — cosine similarity is a clean 0 or 1."""
    v = [0.0] * EMBED_DIM
    v[i] = 1.0
    return v


# --- pure formatter (no DB, runs everywhere) ---------------------------------------------------

def test_vector_literal_formats_and_asserts_dim():
    lit = knowledge._vector_literal([1.0, 0.0] + [0.0] * (EMBED_DIM - 2))
    assert lit.startswith("[1.0,0.0,") and lit.endswith("]")
    with pytest.raises(ValueError):
        knowledge._vector_literal([1.0, 2.0, 3.0])  # wrong dimension fails loudly


# --- DB tests (need the vector extension) ------------------------------------------------------

@pytest.fixture
def pgvector_db(db):
    knowledge._reset_vector_cache()
    if not knowledge._has_vector_column():
        pytest.skip("pgvector column absent — the `vector` extension is not installed on this Postgres")
    yield
    knowledge._reset_vector_cache()


def _admin(username: str) -> User:
    return User.objects.create_user(username=username, password="Dev12345!",
                                    email=f"{username}@example.test")


def _chunk(title: str, text: str, vec: list[float] | None) -> KnowledgeChunk:
    doc = KnowledgeDocument.objects.create(
        title=title, filename=f"{title}.txt", media_type="text/plain", status="ready",
    )
    c = KnowledgeChunk.objects.create(document=doc, seq=0, text=text)
    KnowledgeChunk.objects.filter(id=c.id).update(search=SearchVector("text", config="simple"))
    if vec is not None:
        c.embedding = vec
        c.save(update_fields=["embedding"])
        knowledge._write_vector_column(c.id, vec)
    return c


@pytest.mark.pgvector
def test_migration_added_column_and_hnsw_index(pgvector_db):
    assert knowledge._has_vector_column() is True
    with connection.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_indexes WHERE indexname = 'assistant_knowledgechunk_embv_hnsw'")
        assert cur.fetchone() is not None


@pytest.mark.pgvector
def test_backfill_is_idempotent(pgvector_db):
    # three chunks with a JSON embedding but no vector yet (simulate pre-pgvector ingestion)
    ids = []
    for i in range(3):
        c = _chunk(f"doc{i}", "refund policy text", None)
        c.embedding = _axis(i)
        c.save(update_fields=["embedding"])
        ids.append(c.id)

    def _null_count() -> int:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM assistant_knowledgechunk "
                "WHERE id = ANY(%s) AND embedding_v IS NULL", [ids])
            return cur.fetchone()[0]

    assert _null_count() == 3
    call_command("backfill_embeddings", batch=200, sleep=0)
    assert _null_count() == 0            # first run fills them
    call_command("backfill_embeddings", batch=200, sleep=0)
    assert _null_count() == 0            # second run is a no-op — same rows, no error


@pytest.mark.pgvector
def test_vector_search_ids_uses_hnsw_index(pgvector_db, settings):
    settings.ASSISTANT_PGVECTOR = True
    _chunk("A", "refund policy", _axis(0))
    _chunk("B", "refund policy", _axis(1))
    with connection.cursor() as cur:
        cur.execute("SET LOCAL enable_seqscan = off")  # tiny table — force the planner to the index
        cur.execute(
            "EXPLAIN SELECT id FROM assistant_knowledgechunk WHERE embedding_v IS NOT NULL "
            "ORDER BY embedding_v <=> %s::vector LIMIT 20",
            [knowledge._vector_literal(_axis(1))],
        )
        plan = "\n".join(row[0] for row in cur.fetchall())
    assert "assistant_knowledgechunk_embv_hnsw" in plan


@pytest.mark.pgvector
def test_flag_on_search_scores_via_db_cosine(pgvector_db, settings, monkeypatch):
    settings.ASSISTANT_PGVECTOR = True
    # both match the FTS query; the query vector aligns with B, so the DB cosine must lift B first.
    _chunk("A", "refund policy refund policy handling steps.", _axis(0))
    _chunk("B", "refund policy summary.", _axis(1))
    monkeypatch.setattr(knowledge.client, "embed_text", lambda _q: _axis(1))
    results = knowledge.search("refund policy")
    assert results and results[0]["title"] == "B"


@pytest.mark.pgvector
def test_flag_off_ignores_vector_column(pgvector_db, settings, monkeypatch):
    # column present but flag off → the vector arm stays silent (byte-identical to pre-T3.1).
    settings.ASSISTANT_PGVECTOR = False
    _chunk("A", "refund policy summary.", _axis(0))
    monkeypatch.setattr(knowledge.client, "embed_text", lambda _q: None)
    assert knowledge.vector_search_ids(_axis(0)) == []
    results = knowledge.search("refund policy")
    assert results and results[0]["title"] == "A"
