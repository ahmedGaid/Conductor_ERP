"""Determinism: same definition + inputs => same path + same final context.

Also proves edge `ordering` (not DB insertion order) governs evaluation.
"""
from __future__ import annotations

import pytest

from erp.workflow.engine import engine
from erp.workflow.models import NodeExecution, NodeType, WorkflowEdge

from .factories import make_workflow

pytestmark = pytest.mark.django_db


def _branching_wf():
    return make_workflow(
        "branch",
        nodes=[
            ("start", NodeType.START, {}),
            ("calc", NodeType.SCRIPT, {"logic": {">": [{"var": "amount"}, 50]}, "output_key": "big"}),
            ("gate", NodeType.CONDITION, {}),
            ("end_big", NodeType.END, {}),
            ("end_small", NodeType.END, {}),
        ],
        edges=[
            ("start", "calc", None, 0),
            ("calc", "gate", None, 0),
            ("gate", "end_big", {"==": [{"var": "calc.big"}, True]}, 0),
            ("gate", "end_small", None, 1),  # unconditional fallback
        ],
    )


def _visit_keys(instance):
    return [r.node.key for r in NodeExecution.objects.filter(instance=instance).order_by("started_at")]


def test_same_inputs_same_path_and_context():
    wf = _branching_wf()
    a = engine.start_instance(wf, {"amount": 100})
    b = engine.start_instance(wf, {"amount": 100})
    assert _visit_keys(a) == _visit_keys(b) == ["start", "calc", "gate", "end_big"]
    assert a.context == b.context


def test_ordering_governs_not_insertion_order():
    wf = _branching_wf()
    # Re-insert the gate's edges in reverse DB order but keep their `ordering` values.
    gate = wf.nodes.get(key="gate")
    existing = list(gate.out_edges.order_by("ordering").values("target_id", "condition", "ordering"))
    gate.out_edges.all().delete()
    for spec in reversed(existing):
        WorkflowEdge.objects.create(
            workflow=wf, source=gate, target_id=spec["target_id"],
            condition=spec["condition"], ordering=spec["ordering"],
        )
    inst = engine.start_instance(wf, {"amount": 10})  # small -> fallback edge
    assert _visit_keys(inst) == ["start", "calc", "gate", "end_small"]
