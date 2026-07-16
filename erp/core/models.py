"""Core foundational models.

`Branch` is the org-scoping primitive every business module references (multi-branch is a hard
requirement). The abstract bases give business modules the shared-convention fields
(timestamps, actor stamps, branch scope, soft-delete) without each redefining them.
"""
from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class Branch(models.Model):
    """A company branch. Data is scoped per branch across the ERP."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "core_branch"
        ordering = ["code"]
        verbose_name_plural = "branches"

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.code} — {self.name}"


class TimeStampedModel(models.Model):
    """Abstract: uuid pk + created/updated timestamps."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AuditedModel(TimeStampedModel):
    """Abstract base for business records: actor stamps + branch scope + soft-delete.

    Business modules (Stage 5) inherit this so every record carries the shared conventions.
    """

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    branch = models.ForeignKey(
        "core.Branch",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    # Finer org placement, stamped from the creating actor — drives Department/Team data scopes
    # (a Department/Team belongs to one Branch, so these narrow within the record's branch).
    department = models.ForeignKey(
        "identity.Department",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    team = models.ForeignKey(
        "identity.Team",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True


class IdempotencyKey(TimeStampedModel):
    """At-most-once guard for replay-sensitive API writes.

    A client that may retry (double-click, network replay) sends an ``Idempotency-Key`` header;
    the first request records the created object's id here and replays get that object back
    instead of a second side-effect. See ``erp.core.idempotency.run_once``.
    """

    endpoint = models.CharField(max_length=64)
    key = models.CharField(max_length=128)
    object_id = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        db_table = "core_idempotency_key"
        unique_together = [("endpoint", "key")]


class AppliedUpgradeStep(models.Model):
    """A release upgrade step (see `erp.core.upgrades`) that has already run — `manage.py
    upgrade`'s at-most-once guard so a re-run skips completed steps and resumes at a failed one.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    version = models.CharField(max_length=32)
    name = models.CharField(max_length=128)
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "core_applied_upgrade_step"
        unique_together = [("version", "name")]
        ordering = ["applied_at"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.version}:{self.name}"
