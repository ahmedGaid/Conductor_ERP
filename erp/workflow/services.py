"""Workflow application services — graph persistence and dashboard metrics.

`save_graph` is the canvas round-trip primitive: it persists a full definition (header + nodes +
edges) in one transaction. Nodes are upserted **by key** so existing node ids (and therefore any
running instances pointing at them) survive an edit; edges are fully replaced. Validation rejects
malformed graphs before any write.
"""
from __future__ import annotations

from django.db import transaction
from django.db.models import Count
from rest_framework.exceptions import ValidationError

from .models import (
    InstanceStatus,
    NodeType,
    Workflow,
    WorkflowEdge,
    WorkflowInstance,
    WorkflowNode,
)


def _validate(nodes: list[dict], edges: list[dict]) -> None:
    keys = [n["key"] for n in nodes]
    if len(keys) != len(set(keys)):
        raise ValidationError("node keys must be unique within a workflow")

    start_count = sum(1 for n in nodes if n["type"] == NodeType.START)
    if start_count != 1:
        raise ValidationError("a workflow must have exactly one start node")

    keyset = set(keys)
    seen_ordering: set[tuple[str, int]] = set()
    for e in edges:
        if e["source"] not in keyset:
            raise ValidationError(f"edge source '{e['source']}' is not a node in this workflow")
        if e["target"] not in keyset:
            raise ValidationError(f"edge target '{e['target']}' is not a node in this workflow")
        slot = (e["source"], int(e["ordering"]))
        if slot in seen_ordering:
            raise ValidationError(
                f"duplicate edge ordering {slot[1]} on source '{slot[0]}' "
                "(ordering must be unique per source for deterministic selection)"
            )
        seen_ordering.add(slot)


@transaction.atomic
def save_graph(
    *,
    name: str,
    nodes: list[dict],
    edges: list[dict],
    status: str = "active",
    workflow_id=None,
) -> Workflow:
    """Create or update a workflow definition. Returns the saved Workflow."""
    _validate(nodes, edges)

    if workflow_id is not None:
        wf = Workflow.objects.select_for_update().get(id=workflow_id)
        wf.name = name
        wf.status = status
        wf.version = wf.version + 1  # every saved edit bumps the version
        wf.save(update_fields=["name", "status", "version"])
    else:
        wf = Workflow.objects.create(name=name, status=status)

    existing = {n.key: n for n in wf.nodes.all()}
    incoming_keys = {n["key"] for n in nodes}

    # Remove nodes no longer in the graph (cascades their edges + executions).
    for key, node in existing.items():
        if key not in incoming_keys:
            node.delete()

    by_key: dict[str, WorkflowNode] = {}
    for n in nodes:
        config = n.get("config") or {}
        position = n.get("position") or {}
        if n["key"] in existing:
            node = existing[n["key"]]
            node.type = n["type"]
            node.config = config
            node.position = position
            node.save(update_fields=["type", "config", "position"])
        else:
            node = WorkflowNode.objects.create(
                workflow=wf, key=n["key"], type=n["type"], config=config, position=position
            )
        by_key[n["key"]] = node

    # Edges are not referenced by instances — safe to replace wholesale.
    wf.edges.all().delete()
    for e in edges:
        WorkflowEdge.objects.create(
            workflow=wf,
            source=by_key[e["source"]],
            target=by_key[e["target"]],
            condition=e.get("condition"),
            ordering=int(e["ordering"]),
        )

    return wf


def list_workflows() -> list[dict]:
    """Workflow rows with node + instance counts for the list screen."""
    rows = (
        Workflow.objects.annotate(
            node_count=Count("nodes", distinct=True),
            instance_count=Count("instances", distinct=True),
        )
        .order_by("-created_at")
    )
    return [
        {
            "id": wf.id,
            "name": wf.name,
            "version": wf.version,
            "status": wf.status,
            "created_at": wf.created_at,
            "node_count": wf.node_count,
            "instance_count": wf.instance_count,
        }
        for wf in rows
    ]


def dashboard_metrics() -> dict:
    """Aggregate counts for the dashboard, computed from real data."""
    by_status = {
        row["status"]: row["n"]
        for row in WorkflowInstance.objects.values("status").annotate(n=Count("id"))
    }
    instances_total = sum(by_status.values())
    return {
        "workflows_total": Workflow.objects.count(),
        "workflows_active": Workflow.objects.filter(status="active").count(),
        "instances_total": instances_total,
        "instances_by_status": {s.value: by_status.get(s.value, 0) for s in InstanceStatus},
        "instances_waiting": by_status.get(InstanceStatus.WAITING, 0),
        "instances_failed": by_status.get(InstanceStatus.FAILED, 0),
    }
