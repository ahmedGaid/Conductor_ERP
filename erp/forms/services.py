"""Forms services: validation against the schema + optional workflow trigger."""
from __future__ import annotations

from erp.core.errors import ValidationError
from erp.workflow.engine import engine

from .models import FormDefinition, FormSubmission


def validate_submission(form: FormDefinition, data: dict) -> None:
    """Check required fields and basic types declared in the form schema."""
    for field in form.schema or []:
        key = field.get("key")
        if field.get("required") and (key not in data or data[key] in (None, "")):
            raise ValidationError(f"missing required field: {key}")
        if key in data and field.get("type") == "number":
            try:
                float(data[key])
            except (TypeError, ValueError):
                raise ValidationError(f"field '{key}' must be a number")


def submit(form: FormDefinition, data: dict, user=None) -> FormSubmission:
    """Validate, persist, and (if configured) start the trigger workflow with the form data."""
    validate_submission(form, data)
    submission = FormSubmission.objects.create(form=form, data=data, submitted_by=user)
    if form.trigger_workflow_id:
        instance = engine.start_instance(form.trigger_workflow, data, user=user)
        submission.instance = instance
        submission.save(update_fields=["instance"])
    return submission
