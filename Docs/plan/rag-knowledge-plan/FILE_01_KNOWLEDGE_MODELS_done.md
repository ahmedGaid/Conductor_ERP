# SESSION 1 — Knowledge Models + Chunker
# Files: erp/assistant/models.py, erp/assistant/migrations/0003_knowledge.py, erp/assistant/services/knowledge.py, erp/assistant/tests/test_knowledge.py

---

## Before You Start

1. Open `erp/assistant/models.py` → read the whole file → note the style of `Conversation`,
   `Message`, `Attachment` (field naming, `Meta` ordering, `__str__`, timestamp fields).
2. Open `erp/assistant/migrations/0002_attachment.py` → note how migrations are written here.
3. Open `erp/assistant/services/files.py` → note the module docstring style and how services
   are structured in this app.
4. Run `python manage.py showmigrations assistant` → confirm 0001 and 0002 are applied.

Do not write anything yet.

---

## Task A — Two models in `models.py`

At the END of `erp/assistant/models.py`, add (match the existing models' style — if field/Meta
conventions you read differ from below, follow the file, not this snippet):

```python
class KnowledgeDocument(models.Model):
    """One uploaded company document (SOP, policy, catalog, manual) in the knowledge base.

    Ingestion is synchronous and bounded; a failure lands on the row (status=failed +
    error_text) blame-free, never as an exception to the uploader.
    """

    STATUS_CHOICES = [("processing", "processing"), ("ready", "ready"), ("failed", "failed")]

    title = models.CharField(max_length=200)
    filename = models.CharField(max_length=255)
    media_type = models.CharField(max_length=100)
    size = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="processing")
    error_text = models.CharField(max_length=255, blank=True, default="")
    chunk_count = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="knowledge_documents",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return self.title


class KnowledgeChunk(models.Model):
    """One searchable slice of a document. ``search`` is a maintained tsvector (config
    "simple" — language-neutral, works for Arabic + English); ``embedding`` is filled only
    when ASSISTANT_RAG_EMBEDDINGS is on (session 03)."""

    document = models.ForeignKey(KnowledgeDocument, on_delete=models.CASCADE, related_name="chunks")
    seq = models.PositiveIntegerField()
    text = models.TextField()
    search = SearchVectorField(null=True)
    embedding = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ["document_id", "seq"]
        indexes = [GinIndex(fields=["search"])]
        constraints = [
            models.UniqueConstraint(fields=["document", "seq"], name="uniq_chunk_per_doc_seq"),
        ]

    def __str__(self) -> str:
        return f"{self.document_id}#{self.seq}"
```

Add the needed imports at the top of `models.py`, next to the existing imports:

```python
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
```

(`settings` — check whether the file already imports `django.conf.settings` for
`Attachment.created_by`/similar; reuse whatever user-FK pattern the existing models use.)

## Task B — Migration

```
python manage.py makemigrations assistant -n knowledge
```

Open the generated file → confirm it contains both models, the GIN index, and the unique
constraint. Rename is not needed; Django will number it 0003.

```
python manage.py migrate assistant
```

## Task C — The chunker in a new `services/knowledge.py`

Create `erp/assistant/services/knowledge.py`:

```python
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
```

## Task D — Tests

Create `erp/assistant/tests/test_knowledge.py` (match the style of an existing test module —
open `tests/test_files.py` for fixtures/DB markers used in this app):

```python
"""Knowledge base: models + chunker (plan session 01)."""

- test_chunk_text_packs_paragraphs_under_budget — 3 short paragraphs → 1 chunk containing all 3
- test_chunk_text_splits_long_paragraph_with_overlap — one 3000-char paragraph → ≥2 chunks;
  chunk[1] starts with the last CHUNK_OVERLAP chars of chunk[0]
- test_chunk_text_empty_input_returns_empty_list
- test_knowledge_document_defaults — create a KnowledgeDocument → status == "processing",
  chunk_count == 0
- test_chunk_unique_per_doc_seq — creating two chunks with the same (document, seq) raises
  IntegrityError
```

Write the five tests as real code following the file's conventions.

---

## Smoke Test

- [ ] `python manage.py migrate assistant` applies 0003 cleanly
- [ ] `pytest erp/assistant/tests/test_knowledge.py` — all green
- [ ] `pytest erp/assistant` — everything else still green
- [ ] In `python manage.py shell`: create a KnowledgeDocument + one KnowledgeChunk → no errors
- [ ] `chunk_text("a\n\nb")` returns `["a\n\nb"]` (packed, not split)

---

## After This Session

```
Smoke test passed?
→ Commit, rename this file FILE_01_KNOWLEDGE_MODELS_done.md
→ Type /compact in Claude Code
→ Open FILE_02_INGESTION_API.md and continue
```
