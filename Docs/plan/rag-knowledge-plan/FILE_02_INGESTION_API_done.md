# SESSION 2 — Ingestion Pipeline + Knowledge API
# Files: erp/assistant/services/knowledge.py, erp/assistant/api/views.py, erp/assistant/api/urls.py, erp/assistant/tests/test_knowledge.py

---

## Before You Start

1. Open `erp/assistant/api/views.py` → read the imports, `_envelope`, `ExtractDocumentView`
   (the upload-validation pattern: `MAX_UPLOAD_BYTES` ceiling BEFORE reading, `ALLOWED_TYPES`,
   `client.enabled()` gate) and `_CanBuy = HasAnyRole.require(BRANCH_MANAGER)` — note where
   `MAX_UPLOAD_BYTES` / `ALLOWED_TYPES` are defined and what roles are imported.
2. Open `erp/identity` role definitions (follow the `BRANCH_MANAGER` import) → find the
   admin-level role constant to gate knowledge management with (owner/admin — pick the one the
   codebase already uses for administration; do NOT invent a role).
3. Open `erp/assistant/services/files.py` → find how text is pulled out of txt/csv/xlsx chat
   attachments (`describe_for_model` and its helpers) — you will REUSE those helpers, not
   rewrite them. Note their exact names.
4. Open `erp/assistant/api/urls.py` → note the path style.
5. Open `erp/assistant/services/knowledge.py` (from session 01).

Do not write anything yet.

---

## Task A — Ingestion in `services/knowledge.py`

Append to `services/knowledge.py` (below `chunk_text`). Adjust the two REUSE points to the
exact helper names you found in `files.py`:

```python
def _extract_text(*, data: bytes, media_type: str, filename: str) -> str:
    """Plain text out of any allowed upload.

    txt/md/csv/xlsx: decoded/tabular-flattened locally (REUSE the files.py helpers found in
    the Before-You-Start read — do not duplicate their logic).
    pdf/images: transcribed through the existing vision path (client.complete_stream with the
    file as media and a transcription instruction) — no PDF library, same seam chat already
    uses. Join the streamed chunks into one string.
    """


def ingest_document(*, data: bytes, media_type: str, filename: str, title: str, actor):
    """Create the document row, extract → chunk → index. Synchronous and bounded.

    Any extraction failure is captured on the row (status="failed", error_text truncated to
    255) — the caller always gets the row back, never an exception (mirrors
    notifications.dispatch's posture). On success: status="ready", chunk_count set, every
    chunk's ``search`` vector populated with
    KnowledgeChunk.objects.filter(document=doc).update(search=SearchVector("text", config="simple"))
    and an audit.record(module="assistant", action="knowledge_ingest", ...) written.
    """


def delete_document(doc_id: int, actor) -> None:
    """Delete one document (chunks cascade) + audit.record(action="knowledge_delete")."""
```

Write the real bodies. Rules:
- `SearchVector` import: `from django.contrib.postgres.search import SearchVector`.
- Transcription instruction for the vision path (exact text):
  `"Transcribe the full text content of this document faithfully, in its original language. Output only the transcribed text, no commentary."`
- Wrap the extract step in `try/except Exception` → failed row; never re-raise.
- Empty extracted text is a failure: `error_text="no readable text"`.
- Audit via `from erp.audit import services as audit` (same import agent.py uses).

## Task B — API views

In `erp/assistant/api/views.py`, below `ExtractDocumentView`, add:

```python
_CanManageKnowledge = HasAnyRole.require(<ADMIN-LEVEL ROLE YOU FOUND>)


class KnowledgeView(APIView):
    """List (GET) and upload (POST) knowledge-base documents."""

    permission_classes = [IsAuthenticated, _CanManageKnowledge]

    def get(self, request: Request) -> Response:
        docs = KnowledgeDocument.objects.all()[:200]
        return _envelope([_doc_row(d) for d in docs])

    def post(self, request: Request) -> Response:
        if not client.enabled():
            raise Http404
        upload = request.FILES.get("file")
        # …exact same ceiling + type validation as ExtractDocumentView (size BEFORE read,
        # ALLOWED_TYPES + the text types: text/plain, text/markdown, text/csv, xlsx)…
        doc = knowledge.ingest_document(
            data=upload.read(), media_type=media_type, filename=upload.name,
            title=(request.data.get("title") or upload.name)[:200], actor=request.user,
        )
        return _envelope(_doc_row(doc), status=201)


class KnowledgeDetailView(APIView):
    permission_classes = [IsAuthenticated, _CanManageKnowledge]

    def delete(self, request: Request, pk: int) -> Response:
        knowledge.delete_document(pk, actor=request.user)
        return Response(status=204)
```

Write `_doc_row(d)` next to `_envelope`: `{"id", "title", "filename", "status", "error_text",
"chunk_count", "size", "updated_at"}` (ISO string for the date — copy whatever serialization the
conversations `_detail` helper uses).

Define the allowed text types as a module constant next to `ALLOWED_TYPES`:

```python
KNOWLEDGE_TEXT_TYPES = {
    "text/plain", "text/markdown", "text/csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
```

and validate uploads against `ALLOWED_TYPES | KNOWLEDGE_TEXT_TYPES`.

## Task C — URLs

In `erp/assistant/api/urls.py`, following the existing path style, add:

```python
path("knowledge", KnowledgeView.as_view(), name="assistant-knowledge"),
path("knowledge/<int:pk>", KnowledgeDetailView.as_view(), name="assistant-knowledge-detail"),
```

## Task D — Tests

Extend `tests/test_knowledge.py` (monkeypatch the vision/transcription seam exactly the way
`test_files.py` / `test_agent.py` fake their provider seams — never a live call):

- test_ingest_text_document_creates_ready_chunks — a small .txt upload → status "ready",
  chunk_count ≥ 1, every chunk has non-null `search`
- test_ingest_failure_lands_on_row — transcription seam raises → status "failed",
  error_text set, no exception
- test_ingest_empty_text_is_failed — seam returns "" → status "failed"
- test_knowledge_api_requires_role — plain user POST/GET/DELETE → 403
- test_knowledge_upload_and_delete_roundtrip — role user uploads txt → 201; DELETE → 204;
  chunks gone (cascade)
- test_upload_rejects_oversize_and_bad_type — mirrors ExtractDocumentView's two validations

---

## Smoke Test

- [ ] `pytest erp/assistant/tests/test_knowledge.py` green
- [ ] `pytest erp/assistant` green (nothing else broke)
- [ ] Dev server: POST a small .txt to `/api/assistant/knowledge` as an admin-role user →
      201, status "ready", chunk_count correct
- [ ] Same POST as a non-admin user → 403
- [ ] GET `/api/assistant/knowledge` lists the doc; DELETE removes it (204)
- [ ] Row-level failure check: upload an image with the provider key unset/seam broken →
      row exists with status "failed", API still 201 (blame-free)

---

## After This Session

```
Smoke test passed?
→ Commit, rename this file FILE_02_INGESTION_API_done.md
→ Type /compact in Claude Code
→ Open FILE_03_SEARCH_SERVICE.md and continue
```
