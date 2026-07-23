"""Workflow triggers: subscribe a workflow to a domain event, mirroring how Webhooks fan out
the same event catalog (`erp.notifications.services.webhooks.on_domain_event`). A trigger with
a condition only starts the workflow when the event payload matches — same JSON-logic engine
edges already use, so there's exactly one condition dialect in this codebase, not two.
"""
from __future__ import annotations

from erp.core.errors import NotFoundError, ValidationError
from erp.notifications.webhook_catalog import WEBHOOK_EVENT_CATALOG

from .engine import engine
from .lib.jsonlogic import jsonlogic
from .models import Workflow, WorkflowTrigger


def create_trigger(
    *, workflow_id, event_name: str = "", condition: dict | None = None, schedule: str = "",
) -> WorkflowTrigger:
    if event_name and event_name not in WEBHOOK_EVENT_CATALOG:
        raise ValidationError(f"unknown event: {event_name}")
    if not event_name and not schedule:
        raise ValidationError("a trigger needs either an event_name or a schedule")
    try:
        workflow = Workflow.objects.get(id=workflow_id)
    except Workflow.DoesNotExist as exc:
        raise NotFoundError("workflow not found") from exc
    return WorkflowTrigger.objects.create(
        workflow=workflow, event_name=event_name, condition=condition, schedule=schedule,
    )


def on_domain_event(event) -> None:
    """Core-event listener: start every active, matching trigger's workflow."""
    triggers = WorkflowTrigger.objects.filter(
        is_active=True, event_name=event.name,
    ).select_related("workflow")
    for trigger in triggers:
        if trigger.condition and not jsonlogic(trigger.condition, event.payload):
            continue
        engine.start_instance(trigger.workflow, event.payload)
