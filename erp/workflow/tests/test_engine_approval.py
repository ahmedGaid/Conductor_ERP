"""Approval pauses the instance (waiting) and resumes on approve/reject."""
from __future__ import annotations

import pytest

from erp.workflow.engine import engine
from erp.workflow.models import InstanceStatus, NodeType

from .factories import make_workflow

pytestmark = pytest.mark.django_db


def _approval_wf():
    return make_workflow(
        "approval",
        nodes=[
            ("start", NodeType.START, {}),
            ("approve", NodeType.APPROVAL, {}),
            ("gate", NodeType.CONDITION, {}),
            ("end_ok", NodeType.END, {}),
            ("end_no", NodeType.END, {}),
        ],
        edges=[
            ("start", "approve", None, 0),
            ("approve", "gate", None, 0),
            ("gate", "end_ok", {"==": [{"var": "approve.approved"}, True]}, 0),
            ("gate", "end_no", None, 1),
        ],
    )


def test_waiting_then_approve():
    wf = _approval_wf()
    inst = engine.start_instance(wf, {})
    assert inst.status == InstanceStatus.WAITING
    assert inst.current_node.key == "approve"

    final = engine.resume(inst.id, decision="approve")
    assert final.status == InstanceStatus.COMPLETED
    assert final.context["approve"]["approved"] is True


def test_waiting_then_reject():
    wf = _approval_wf()
    inst = engine.start_instance(wf, {})
    final = engine.resume(inst.id, decision="reject")
    assert final.status == InstanceStatus.COMPLETED
    assert final.context["approve"]["approved"] is False
