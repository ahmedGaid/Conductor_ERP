"""Forms builder models."""
from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class FormDefinition(models.Model):
    """A form's field schema. `schema` is a list of field descriptors:
    [{ "key": "amount", "label": "Amount", "type": "number", "required": true }, ...]
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    schema = models.JSONField(default=list)
    # Optional workflow to start when a submission is created.
    trigger_workflow = models.ForeignKey(
        "workflow.Workflow", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "forms_definition"

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class FormSubmission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    form = models.ForeignKey(FormDefinition, on_delete=models.CASCADE, related_name="submissions")
    data = models.JSONField(default=dict)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    instance = models.ForeignKey(
        "workflow.WorkflowInstance", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "forms_submission"
