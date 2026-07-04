"""Conversation storage for the AI workspace.

A Conversation belongs to one user (single-tenant, but conversations are private to their owner).
Messages are append-only; edits create new messages so the transcript stays honest.
"""
from __future__ import annotations

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
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


class Attachment(models.Model):
    """A file the user attached to a chat turn (image/PDF/CSV/XLSX/JSON/XML/TXT).

    Uploaded on its own first (so the composer shows a chip while the file transfers), then *claimed*
    by the send that references it — ``message`` stays null until then. Private to its uploader; a
    claim only ever links the uploader's own still-unclaimed attachments.
    """

    message = models.ForeignKey(
        Message, on_delete=models.CASCADE, related_name="attachments", null=True, blank=True,
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    file = models.FileField(upload_to="assistant/%Y/%m/")
    name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    size = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


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
