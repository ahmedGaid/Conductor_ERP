import pytest

from erp.core.events import bus
from erp.purchasing.events import PR_SUBMITTED
from erp.workflow import triggers
from erp.workflow.models import InstanceStatus, Workflow, WorkflowInstance, WorkflowNode, WorkflowTrigger

pytestmark = pytest.mark.django_db


def _simple_workflow():
    wf = Workflow.objects.create(name="Notify on submit")
    start = WorkflowNode.objects.create(workflow=wf, key="start", type="start")
    end = WorkflowNode.objects.create(workflow=wf, key="end", type="end")
    from erp.workflow.models import WorkflowEdge

    WorkflowEdge.objects.create(workflow=wf, source=start, target=end, ordering=0)
    return wf


def test_trigger_starts_instance_on_matching_event():
    wf = _simple_workflow()
    triggers.create_trigger(workflow_id=wf.id, event_name=PR_SUBMITTED)

    bus.publish(PR_SUBMITTED, {"amount_minor": 10000})

    instance = WorkflowInstance.objects.get(workflow=wf)
    assert instance.status == InstanceStatus.COMPLETED
    assert instance.context["amount_minor"] == 10000


def test_trigger_condition_blocks_non_matching_event():
    wf = _simple_workflow()
    triggers.create_trigger(
        workflow_id=wf.id, event_name=PR_SUBMITTED,
        condition={">": [{"var": "amount_minor"}, 500000]},
    )

    bus.publish(PR_SUBMITTED, {"amount_minor": 10000})

    assert not WorkflowInstance.objects.filter(workflow=wf).exists()


def test_inactive_trigger_does_not_fire():
    wf = _simple_workflow()
    trigger = triggers.create_trigger(workflow_id=wf.id, event_name=PR_SUBMITTED)
    trigger.is_active = False
    trigger.save(update_fields=["is_active"])

    bus.publish(PR_SUBMITTED, {"amount_minor": 10000})

    assert not WorkflowInstance.objects.filter(workflow=wf).exists()
