"""ai-reliability T3.1 — give KnowledgeChunk a pgvector `embedding_v` column + HNSW index.

Deliberately guarded and reversible. The `embedding_v` column is a `vector(768)` (Gemini
`text-embedding-004` output dim), managed here by raw SQL — it is NOT a Django model field, so
ordinary ``KnowledgeChunk`` queries never select it and behaviour is byte-identical wherever the
column is absent. If the Postgres server has no `vector` extension available (community/Windows
installs often don't), or the DB role can't ``CREATE EXTENSION``, this migration adds nothing and
``ASSISTANT_PGVECTOR`` simply can never turn on — the assistant keeps working on FTS + the existing
Python-cosine blend, exactly as before.
"""
from __future__ import annotations

from django.db import migrations, transaction

# text-embedding-004 output dimension. Asserted at write time in services/knowledge.py so a model
# swap that changes the dim fails loudly instead of writing a mismatched vector.
EMBED_DIM = 768
_INDEX = "assistant_knowledgechunk_embv_hnsw"


def _vector_available(cursor) -> bool:
    cursor.execute("SELECT 1 FROM pg_available_extensions WHERE name = 'vector'")
    return cursor.fetchone() is not None


def forwards(apps, schema_editor):
    conn = schema_editor.connection
    if conn.vendor != "postgresql":
        return
    with conn.cursor() as cur:
        if not _vector_available(cur):
            # Server binary absent — skip silently; the feature flag can never turn on here.
            return
    # CREATE EXTENSION needs privileges; run it in a savepoint so a permission error rolls back
    # only this step and leaves the migration transaction usable (we then just skip the column).
    try:
        with transaction.atomic(using=conn.alias):
            with conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    except Exception:
        return
    with conn.cursor() as cur:
        cur.execute(
            f"ALTER TABLE assistant_knowledgechunk ADD COLUMN IF NOT EXISTS embedding_v vector({EMBED_DIM})"
        )
        cur.execute(
            f"CREATE INDEX IF NOT EXISTS {_INDEX} ON assistant_knowledgechunk "
            "USING hnsw (embedding_v vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
        )


def backwards(apps, schema_editor):
    conn = schema_editor.connection
    if conn.vendor != "postgresql":
        return
    with conn.cursor() as cur:
        cur.execute(f"DROP INDEX IF EXISTS {_INDEX}")
        cur.execute("ALTER TABLE assistant_knowledgechunk DROP COLUMN IF EXISTS embedding_v")
    # Leave the `vector` extension installed — other features (T2.8 cache, later phases) may use it.


class Migration(migrations.Migration):

    dependencies = [
        ("assistant", "0009_alter_trace_feature"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
