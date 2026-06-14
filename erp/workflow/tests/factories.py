"""Test helpers to build workflows concisely."""
from __future__ import annotations

from ..models import Workflow, WorkflowEdge, WorkflowNode


def make_workflow(name, nodes, edges) -> Workflow:
    """nodes: [(key, type, config)]; edges: [(src_key, tgt_key, condition, ordering)]."""
    wf = Workflow.objects.create(name=name)
    by_key = {}
    for key, ntype, config in nodes:
        by_key[key] = WorkflowNode.objects.create(
            workflow=wf, key=key, type=ntype, config=config or {}
        )
    for src, tgt, cond, ordering in edges:
        WorkflowEdge.objects.create(
            workflow=wf,
            source=by_key[src],
            target=by_key[tgt],
            condition=cond,
            ordering=ordering,
        )
    return wf
