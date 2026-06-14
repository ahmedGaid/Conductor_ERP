"""Crash-resume: state lives in the DB; a fresh engine resumes with no lost/duplicated steps."""
from __future__ import annotations

import pytest

from erp.workflow.engine import engine
from erp.workflow.models import InstanceStatus, NodeExecution, NodeRunStatus, NodeType

from .factories import make_workflow

pytestmark = pytest.mark.django_db


def _linear_wf():
    return make_workflow(
        "linear",
        nodes=[
            ("start", NodeType.START, {}),
            ("s1", NodeType.SCRIPT, {"logic": {"+": [1, 1]}, "output_key": "v"}),
            ("s2", NodeType.SCRIPT, {"logic": {"+": [2, 2]}, "output_key": "v"}),
            ("end", NodeType.END, {}),
        ],
        edges=[
            ("start", "s1", None, 0),
            ("s1", "s2", None, 0),
            ("s2", "end", None, 0),
        ],
    )


def test_crash_then_resume_completes_once_each():
    wf = _linear_wf()
    from erp.workflow.models import WorkflowInstance

    # Run only part-way (bounded steps) to simulate a crash mid-flow, persisting each transition.
    partial = WorkflowInstance.objects.create(
        workflow=wf, status=InstanceStatus.PENDING,
        current_node=wf.nodes.get(key="start"), context={"seed": 1},
    )
    engine.run(partial.id, max_steps=2)
    partial.refresh_from_db()
    assert partial.status not in (InstanceStatus.COMPLETED, InstanceStatus.FAILED)

    # Fresh resume (no in-memory state carried) finishes the flow.
    final = engine.resume(partial.id)
    assert final.status == InstanceStatus.COMPLETED

    # Each node executed exactly once, in order.
    runs = list(
        NodeExecution.objects.filter(instance=partial).order_by("started_at")
    )
    keys = [r.node.key for r in runs]
    assert keys == ["start", "s1", "s2", "end"]
    assert all(r.status == NodeRunStatus.COMPLETED for r in runs)
    assert len(keys) == len(set(keys))  # no duplicates


def test_full_run_completes():
    wf = _linear_wf()
    instance = engine.start_instance(wf, {"seed": 1})
    assert instance.status == InstanceStatus.COMPLETED
    assert instance.context["s1"] == {"v": 2}
    assert instance.context["s2"] == {"v": 4}
