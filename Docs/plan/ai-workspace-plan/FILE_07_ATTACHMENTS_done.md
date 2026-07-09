# SESSION 7 — Attachments: Drag, Drop, Paste, Understand
# Files: erp/assistant/services/files.py (new), erp/assistant/api/views.py, erp/assistant/models.py + migration, apps/web/src/assistant/Composer.tsx, apps/web/src/api/assistant.ts, apps/web/src/assistant/assistant-panel.css, apps/web/src/i18n/locales/ar.json, apps/web/src/i18n/locales/en.json, erp/assistant/tests/test_files.py (new)

---

## Before You Start

1. Open `erp/assistant/services/extraction.py` → how files are already received, size/type-checked,
   and sent to the vision-capable provider (Groq Llama-4 vision / Gemini). Reuse every helper you
   can — this session generalizes that path, it does not duplicate it.
2. Open `erp/assistant/api/views.py` → `ExtractDocumentView`'s upload handling (multipart parsing,
   limits, error mapping).
3. Open `apps/web/src/api/client.ts` → `apiUpload`.
4. Check what's already in the Python environment for spreadsheets (`pip list` / `pyproject.toml` —
   look for `openpyxl`). If absent: CSV ships now (stdlib), XLSX support is a **stop-and-ask**
   (no new dependencies without asking).

"Do not write anything yet."

---

## Task A — Attachment model + upload endpoint

Add to `erp/assistant/models.py`:

```python
class Attachment(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="attachments",
                                null=True, blank=True)  # null until the send that claims it
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    file = models.FileField(upload_to="assistant/%Y/%m/")
    name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    size = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
```

`POST /api/assistant/attachments` (multipart, same auth as extract-document): validates type
(png/jpg/webp, pdf, csv, xlsx, json, xml, txt) and size (reuse extraction's limit; if none exists,
10 MB), stores, returns `{id, name, content_type, size}`. Register in `api/urls.py`.

## Task B — File understanding

Create `erp/assistant/services/files.py`:

```python
def describe_for_model(attachment) -> dict:
    """Turn an attachment into model-ready content.

    Images/PDF → the provider's vision path (same as extraction).
    CSV/XLSX  → header row + dtypes + first 20 rows as a compact text table + row count.
    JSON/XML/TXT → first ~8KB verbatim, marked as truncated when cut.
    """
```

Wire into the chat pipeline: `ChatView` body gains `attachment_ids: number[]`; the service claims
them (sets `message` FK — only the uploader's own unclaimed attachments, else 404), and their
`describe_for_model` output joins the user message content sent to the provider. The attachment
list rides in the user Message's `meta` so history re-renders chips.

Structured **import** of file contents (create records from a customer list, etc.) is session 12 —
this session is understanding and Q&A only ("what's in this file?", "summarize this price list").

## Task C — Composer upload UX

In `Composer.tsx` (the `startSlot` from session 6):

- paperclip button → hidden `<input type="file" multiple>`
- drag-over on the whole panel shows a designed drop veil (`assistant.dropHint`, dashed border via
  tokens); drop uploads
- paste: `onPaste` with `clipboardData.files` (screenshots paste straight in)
- each file uploads immediately (`uploadAttachment` wrapper via `apiUpload`), rendering a chip with
  name, size, spinner→check, and a remove ×; send includes the claimed `attachment_ids`
- upload failure: chip flips to a quiet error state with retry — blame-free copy, no toast spam
- message bubbles render attachment chips above the text (image chips get a small thumbnail)

## Task D — i18n + tests

Both locales: `assistant.attach`, `assistant.dropHint`, `assistant.uploadFailed`,
`assistant.remove`, `assistant.fileTooLarge`, `assistant.fileType`.

`erp/assistant/tests/test_files.py`: CSV describe (headers + row cap + count), oversize rejected
with the human error, claiming another user's attachment 404s, chat with attachment persists the
link.

---

## Smoke Test

- [ ] Drop a CSV of customers → ask "how many rows and what columns?" → correct answer
- [ ] Paste a screenshot → ask "what is this?" → vision answer
- [ ] PDF invoice → "what's the total?" → correct (extraction path reused, not duplicated)
- [ ] Two files on one message; chips persist after reload (history re-render)
- [ ] 15 MB file rejected client-side with the designed message; unsupported type likewise
- [ ] `pytest erp/assistant` + i18n parity + tsc + gate03 green

---

## After This Session

```
Smoke test passed?  End of Phase 2 — commit, merge checkpoint.
→ Rename this file: append _done (e.g. FILE_01_CONVERSATIONS_BACKEND_done.md). A _done file is finished forever - never reopen it.
→ Type /compact in Claude Code
→ Open FILE_08_TOOL_CATALOG.md and continue
```
