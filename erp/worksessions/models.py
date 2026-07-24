"""Persistent work-in-progress (draft) sessions — a module-agnostic platform capability.

A WorkSession preserves the *unsaved* state of a form or wizard so the user can leave and return to
exactly where they were. It is deliberately NOT a business record: this module never writes a
customer/order/journal — completion just flips a status, and the real write goes through the owning
module's own service contract. See docs/superpowers/specs/2026-07-24-draft-recovery-design.md.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

from erp.core.models import TimeStampedModel


class WorkSession(TimeStampedModel):
    """One user's in-progress draft for a single form/wizard (uuid pk + created/updated from base)."""

    class Status(models.TextChoices):
        ACTIVE = "active", "active"
        COMPLETED = "completed", "completed"
        DISCARDED = "discarded", "discarded"
        SUPERSEDED = "superseded", "superseded"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="work_sessions",
    )
    workflow_key = models.CharField(max_length=64)  # e.g. "sales.customer.create"
    entity_type = models.CharField(max_length=64, blank=True, default="")
    related_entity_id = models.CharField(max_length=64, blank=True, default="")  # "" for a create draft
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    payload = models.JSONField(default=dict)  # the form draft: field values + current step
    schema_version = models.PositiveIntegerField(default=1)  # bump when a form's payload shape changes
    client_version = models.PositiveIntegerField(default=0)  # monotonic; drives conflict detection
    last_active_at = models.DateTimeField(default=timezone.now)  # touched on each content save
    import_batch = models.ForeignKey(
        "imports.ImportBatch", null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
    )

    class Meta:
        db_table = "worksessions_session"
        ordering = ["-last_active_at"]
        indexes = [
            models.Index(fields=["owner", "workflow_key", "status"]),
            models.Index(fields=["owner", "status", "last_active_at"]),
        ]
        constraints = [
            # At most one ACTIVE draft per form per user → no duplicate drafts.
            models.UniqueConstraint(
                fields=["owner", "workflow_key", "related_entity_id"],
                condition=models.Q(status="active"),
                name="uniq_active_worksession_per_form",
            ),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.workflow_key} draft for owner={self.owner_id} ({self.status})"
