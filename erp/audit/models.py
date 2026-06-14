"""Immutable audit entry.

Records user, timestamp, action, entity, before/after, result, and correlation_id for every
business write. Append-only: rows are never updated or deleted (enforced in the service layer
and DB permissions during hardening).
"""
from __future__ import annotations

from django.conf import settings
from django.db import models


class AuditEntry(models.Model):
    class Result(models.TextChoices):
        SUCCESS = "success", "Success"
        FAILURE = "failure", "Failure"

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_entries",
    )
    module = models.CharField(max_length=64)
    action = models.CharField(max_length=128)
    entity_type = models.CharField(max_length=128)
    entity_id = models.CharField(max_length=64, blank=True)
    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)
    result = models.CharField(max_length=16, choices=Result.choices, default=Result.SUCCESS)
    correlation_id = models.CharField(max_length=64, blank=True, db_index=True)

    class Meta:
        db_table = "audit_entry"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["module", "action"])]

    def save(self, *args, **kwargs):
        # Append-only: allow the initial insert, forbid any later update.
        if not self._state.adding:
            raise ValueError("AuditEntry is immutable and cannot be updated")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("AuditEntry is immutable and cannot be deleted")
