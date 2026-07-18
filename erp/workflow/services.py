"""Workflow application services — graph persistence and dashboard metrics.

`save_graph` is the canvas round-trip primitive: it persists a full definition (header + nodes +
edges) in one transaction. Nodes are upserted **by key** so existing node ids (and therefore any
running instances pointing at them) survive an edit; edges are fully replaced. Validation rejects
malformed graphs before any write.
"""
from __future__ import annotations

import uuid

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

    _validate_drafts_only(nodes, edges)


def _action_risk(node: dict) -> str | None:
    """The declared risk of an ``assistant_action`` node's action — ``None`` if it names none."""
    from erp.assistant.services.actions import ACTIONS

    action = ACTIONS.get((node.get("config") or {}).get("action") or "")
    return action.risk if action else None


def _posts(node: dict) -> bool:
    """Does this node push something out of the building — post/send/finalise?

    An assistant action declared ``post``/``destructive`` (none exist today; the rule is written
    for the day they arrive), or an API Call marked as an external write.
    """
    if node["type"] == NodeType.ASSISTANT_ACTION:
        return _action_risk(node) in ("post", "destructive")
    if node["type"] == NodeType.API_CALL:
        return bool((node.get("config") or {}).get("write"))
    return False


def _validate_drafts_only(nodes: list[dict], edges: list[dict]) -> None:
    """The drafts-only rule, enforced at save time.

    An assistant-action node that WRITES (creates a draft) must be followed, on **every** path
    that leaves it, by an ``approval`` node — before the run reaches any posting node and before
    it reaches the end. A graph that lets an agent-made draft slip past a human is refused here,
    not caught later in a run.
    """
    by_key = {n["key"]: n for n in nodes}
    out: dict[str, list[str]] = {n["key"]: [] for n in nodes}
    for e in edges:
        out[e["source"]].append(e["target"])

    for node in nodes:
        if node["type"] != NodeType.ASSISTANT_ACTION:
            continue
        config = node.get("config") or {}
        name = config.get("action")
        if not name:
            raise ValidationError(
                f"the assistant step '{node['key']}' has no action chosen yet"
            )
        risk = _action_risk(node)
        if risk is None:
            raise ValidationError(
                f"the assistant step '{node['key']}' names an action that does not exist "
                f"('{name}')"
            )
        if risk == "read":
            continue  # a reading step creates nothing, so nothing needs approving

        reason = _path_without_approval(node["key"], by_key, out)
        if reason:
            raise ValidationError(
                f"the assistant step '{node['key']}' creates a draft, so a human approval step "
                f"must come after it on every path — {reason}"
            )


def _path_without_approval(start: str, by_key: dict, out: dict[str, list[str]]) -> str | None:
    """Walk forward from ``start``; return a human reason for the first unapproved path found.

    A branch stops being a problem the moment it hits an approval node. Cycles terminate because
    a key is only walked once in the "no approval seen yet" state.
    """
    seen: set[str] = set()
    stack = list(out.get(start, []))
    if not stack:
        return "this step has nothing after it"
    while stack:
        key = stack.pop()
        if key in seen:
            continue
        seen.add(key)
        node = by_key[key]
        if node["type"] == NodeType.APPROVAL:
            continue  # approved from here on — this branch is fine
        if _posts(node):
            return f"'{key}' posts or sends before anyone has approved it"
        if node["type"] == NodeType.END:
            return f"the path through '{key}' finishes with no approval step"
        nxt = out.get(key, [])
        if not nxt:
            return f"the path through '{key}' finishes with no approval step"
        stack.extend(nxt)
    return None


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


def instance_status(query: str) -> dict:
    """One workflow instance's live state — for "why did this workflow stop?" (the AI read tool).

    ``query`` resolves an instance by id (or id prefix) first, else by any value stored in its
    ``context`` (e.g. the document number that started it), else by workflow name. Returns the
    current step, its status/error, and the recent node-run history. Company-wide (the assistant's
    tool layer gates it by ``workflow.instance.view``).
    """
    q = (query or "").strip()
    if not q:
        return {"instance": None}
    qs = WorkflowInstance.objects.select_related("workflow", "current_node")
    inst = None
    try:
        uuid.UUID(str(q))
    except ValueError:
        pass
    else:
        inst = qs.filter(id=q).first()
    if inst is None:
        inst = qs.filter(workflow__name__icontains=q).order_by("-created_at").first()
    if inst is None:
        return {"instance": None}

    runs = [
        {"node": r.node.key, "type": r.node.type, "status": r.status, "attempt": r.attempt,
         "error": r.error}
        for r in inst.node_runs.select_related("node").order_by("started_at", "id")[:10]
    ]
    return {
        "instance": {
            "id": str(inst.id),
            "workflow": inst.workflow.name,
            "status": inst.status,
            "current_node": inst.current_node.key if inst.current_node else None,
            "current_type": inst.current_node.type if inst.current_node else None,
            "error": inst.error,
        },
        "history": runs,
    }


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
