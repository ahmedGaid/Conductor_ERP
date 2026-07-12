"""Smart Import Engine — working tables.

Three records carry a migration from raw spreadsheet to imported records:

* ``ImportProfile`` — a saved, reusable header→field mapping for one entity (spec step 5). Lets a
  user re-run "customers.xlsx from our old system" every month without remapping.
* ``ImportBatch`` — one upload's lifecycle: analyzing → mapping → previewing → ready → running →
  done (or paused/failed/rolled_back). Holds the chosen strategy, the resolved mapping, and rolling
  stats/counts.
* ``ImportRow`` — one source row, the working table the engine grinds on: raw values, normalized
  values, validation ``issues``, the user's ``decision`` (merge target / edits / skip), and, once
  written, a ``result_ref`` anchor used for rollback-as-reversal.

The engine core never imports business-module models — only the adapters in ``adapters/`` do (see
``registry``). These tables are module-agnostic on purpose (spec step 27).
"""
from __future__ import annotations

from django.db import models

from erp.core.models import AuditedModel, TimeStampedModel


class ImportProfile(AuditedModel):
    """A saved header→field mapping for one entity, re-runnable across uploads (spec step 5)."""

    name = models.CharField(max_length=200)
    entity = models.CharField(max_length=64)  # adapter entity key, e.g. "customers"
    # {source_header: field_name} plus any per-field options the wizard captured.
    mapping = models.JSONField(default=dict)
    options = models.JSONField(default=dict)

    class Meta:
        db_table = "imports_profile"
        ordering = ["entity", "name"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.entity}:{self.name}"


class ImportBatch(AuditedModel):
    """One upload's import lifecycle — status machine + chosen strategy + rolling stats."""

    class Status(models.TextChoices):
        ANALYZING = "analyzing", "analyzing"
        MAPPING = "mapping", "mapping"
        PREVIEWING = "previewing", "previewing"
        READY = "ready", "ready"
        RUNNING = "running", "running"
        PAUSED = "paused", "paused"
        DONE = "done", "done"
        FAILED = "failed", "failed"
        ROLLED_BACK = "rolled_back", "rolled_back"

    class Strategy(models.TextChoices):
        CREATE_ONLY = "create_only", "create_only"
        UPDATE_ONLY = "update_only", "update_only"
        UPSERT = "upsert", "upsert"
        SKIP_EXISTING = "skip_existing", "skip_existing"

    entity = models.CharField(max_length=64)
    # The uploaded file lives in the assistant Attachment store (string ref → no core import).
    source_file = models.ForeignKey(
        "assistant.Attachment",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    profile = models.ForeignKey(
        ImportProfile,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="batches",
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.ANALYZING,
    )
    strategy = models.CharField(
        max_length=16, choices=Strategy.choices, default=Strategy.CREATE_ONLY,
    )
    mapping = models.JSONField(default=dict)
    # Free-form counts / timings / stage detail the engine writes as it progresses.
    stats = models.JSONField(default=dict)
    row_count = models.PositiveIntegerField(default=0)
    processed_count = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "imports_batch"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["entity", "status"])]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.entity} batch {self.pk} ({self.status})"


class ImportRow(TimeStampedModel):
    """One source row — the per-row working table the engine validates, fixes, and writes."""

    class Status(models.TextChoices):
        PENDING = "pending", "pending"
        VALID = "valid", "valid"
        ERROR = "error", "error"
        DUPLICATE = "duplicate", "duplicate"
        SKIPPED = "skipped", "skipped"
        IMPORTED = "imported", "imported"
        REVERTED = "reverted", "reverted"

    batch = models.ForeignKey(ImportBatch, on_delete=models.CASCADE, related_name="rows")
    row_number = models.PositiveIntegerField()  # 1-based source row (header excluded)
    raw = models.JSONField(default=dict)  # values exactly as read from the file
    normalized = models.JSONField(default=dict)  # after cleaning/mapping
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING,
    )
    issues = models.JSONField(default=list)  # [{field, code, message}]
    decision = models.JSONField(default=dict)  # {merge_target, edits, skip}
    result_ref = models.JSONField(default=dict)  # {model, pk} — rollback anchor

    class Meta:
        db_table = "imports_row"
        ordering = ["batch", "row_number"]
        indexes = [models.Index(fields=["batch", "status"])]
        constraints = [
            models.UniqueConstraint(
                fields=["batch", "row_number"], name="uniq_batch_rownumber",
            ),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"row {self.row_number} of batch {self.batch_id} ({self.status})"
