# SESSION 1 — Conversation Persistence (Backend)
# Files: erp/assistant/models.py (new), erp/assistant/migrations/*, erp/assistant/api/views.py, erp/assistant/api/urls.py, erp/assistant/services/ask.py, erp/assistant/tests/test_conversations.py (new)

---

## Before You Start

1. Open `erp/assistant/api/urls.py` → confirm the three existing routes (`status`, `extract-document`, `ask`).
2. Open `erp/assistant/api/views.py` → read `AskView` — note how it authenticates, parses the body, and calls `services/ask.py`.
3. Open `erp/assistant/services/ask.py` → read the full ask pipeline (router prompt → tool → answer) and the shape it returns (`answer`, `citations`, `used_tool`).
4. Open one existing models file for house style, e.g. `erp/audit/models.py` — match field naming and Meta conventions.
5. Open `erp/settings.py` (or wherever `INSTALLED_APPS` lives) → confirm `erp.assistant` is registered and whether it currently has models.

"Do not write anything yet."

---

## Task A — Models

Create `erp/assistant/models.py`:

```python
"""Conversation storage for the AI workspace.

A Conversation belongs to one user (single-tenant, but conversations are private to their owner).
Messages are append-only; edits create new messages so the transcript stays honest.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models


class Conversation(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="ai_conversations")
    title = models.CharField(max_length=200, blank=True, default="")
    pinned = models.BooleanField(default=False)
    archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-pinned", "-updated_at"]


class Message(models.Model):
    class Role(models.TextChoices):
        USER = "user"
        ASSISTANT = "assistant"

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=12, choices=Role.choices)
    content = models.TextField(blank=True, default="")
    # citations / tool steps / action proposals ride along as structured JSON (session 09/10 fill these)
    meta = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
```

Run `python manage.py makemigrations assistant`.

## Task B — Conversation API

In `erp/assistant/api/views.py`, add (mirroring the auth/permission style of `AskView` exactly):

- `ConversationsView` — `GET` lists the caller's conversations (id, title, pinned, archived,
  updated_at, first-line preview), supports `?q=` (icontains on title + message content) and
  `?archived=1`; `POST` creates one (empty title allowed).
- `ConversationDetailView` — `GET` returns the conversation + all messages (role, content, meta,
  created_at); `PATCH` accepts any of `title` / `pinned` / `archived`; `DELETE` deletes it.
  Every view filters by `request.user` — never expose another user's thread (404, not 403).

In `erp/assistant/api/urls.py`, find the `urlpatterns` list and add below the `ask` path:

```python
    path("conversations", ConversationsView.as_view(), name="assistant-conversations"),
    path("conversations/<int:pk>", ConversationDetailView.as_view(), name="assistant-conversation"),
```

## Task C — Persist the ask flow

In `erp/assistant/services/ask.py`, add an optional `conversation` parameter to the top-level ask
function. When given: append the user Message before calling the model, append the assistant
Message (content + `meta={"citations": ..., "used_tool": ...}`) after, and set the conversation
title from the first user message (first 60 chars) if the title is empty. Touch `updated_at` by
saving the conversation. `AskView` accepts an optional `conversation_id` in the body, resolves it
(owned by `request.user`, else 404), and passes it through. **No `conversation_id` ⇒ behaviour
identical to today** — the existing page keeps working.

## Task D — Tests

Create `erp/assistant/tests/test_conversations.py` (copy the setup style of
`erp/assistant/tests/test_ask.py` — same client/auth fixtures):

- create → list → rename → pin → archive → delete round-trip
- search by `?q=` matches message content
- user B cannot see / patch / delete user A's conversation (404)
- ask with `conversation_id` appends two messages and auto-titles

---

## Smoke Test

- [ ] `python manage.py migrate` runs clean
- [ ] `pytest erp/assistant` — all green (old ask/extraction tests untouched and passing)
- [ ] `POST /api/assistant/conversations` returns an id; `GET` lists it
- [ ] `POST /api/assistant/ask` with that `conversation_id` → `GET /conversations/<id>` shows 2 messages
- [ ] `PATCH` with `{"pinned": true}` moves it to the top of the list
- [ ] Second user's token gets 404 on that conversation
- [ ] `POST /api/assistant/ask` **without** `conversation_id` still returns the same shape as before

---

## After This Session

```
Smoke test passed?
→ Rename this file: append _done (e.g. FILE_01_CONVERSATIONS_BACKEND_done.md). A _done file is finished forever - never reopen it.
→ Type /compact in Claude Code
→ Open FILE_02_STREAMING_BACKEND.md and continue
```
