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
