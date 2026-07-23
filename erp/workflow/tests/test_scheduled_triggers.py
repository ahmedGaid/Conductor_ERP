"""Scheduled (non-event) workflow triggers — Task 7 of the non-technical workflow builder."""
from __future__ import annotations

import pytest

from erp.workflow.models import InstanceStatus, Workflow, WorkflowEdge, WorkflowInstance, WorkflowNode, WorkflowTrigger
from erp.workflow.tasks import run_scheduled_triggers

pytestmark = pytest.mark.django_db


def _notify_workflow():
    wf = Workflow.objects.create(name="Low stock alert")
    start = WorkflowNode.objects.create(workflow=wf, key="start", type="start")
    end = WorkflowNode.objects.create(workflow=wf, key="end", type="end")
    WorkflowEdge.objects.create(workflow=wf, source=start, target=end, ordering=0)
    return wf


def test_low_stock_schedule_starts_one_instance_per_low_item(item_below_reorder_point):
    wf = _notify_workflow()
    WorkflowTrigger.objects.create(workflow=wf, event_name="", schedule="low_stock", is_active=True)

    run_scheduled_triggers()

    instance = WorkflowInstance.objects.get(workflow=wf)
    assert instance.status == InstanceStatus.COMPLETED
    assert instance.context["item_name"] == item_below_reorder_point.name
