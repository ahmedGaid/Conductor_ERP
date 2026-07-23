"""Workflow API serializers.

The graph is exchanged with edges referenced by node **key** (not DB id) so a definition
round-trips cleanly: save a graph, reload it, get an identical structure. The execution shapes
(instance + node runs + logs) feed the execution viewer.
"""
from __future__ import annotations

from rest_framework import serializers

from .models import NodeType


class NodeSerializer(serializers.Serializer):
    key = serializers.CharField(max_length=64)
    type = serializers.ChoiceField(choices=NodeType.choices)
    config = serializers.DictField(required=False, default=dict)
    position = serializers.DictField(required=False, default=dict)


class EdgeSerializer(serializers.Serializer):
    source = serializers.CharField(max_length=64)
    target = serializers.CharField(max_length=64)
    condition = serializers.JSONField(required=False, allow_null=True, default=None)
    ordering = serializers.IntegerField(default=0)


class WorkflowGraphSerializer(serializers.Serializer):
    """Read+write shape of a full workflow definition (header + nodes + edges)."""

    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(max_length=200)
    version = serializers.IntegerField(read_only=True)
    status = serializers.CharField(max_length=16, required=False, default="active")
    created_at = serializers.DateTimeField(read_only=True)
    nodes = NodeSerializer(many=True)
    edges = EdgeSerializer(many=True)

    def to_representation(self, wf) -> dict:
        nodes = list(wf.nodes.all().order_by("key"))
        edges = list(wf.edges.select_related("source", "target").order_by("source__key", "ordering"))
        return {
            "id": str(wf.id),
            "name": wf.name,
            "version": wf.version,
            "status": wf.status,
            "created_at": wf.created_at,
            "nodes": [
                {"key": n.key, "type": n.type, "config": n.config or {}, "position": n.position or {}}
                for n in nodes
            ],
            "edges": [
                {
                    "source": e.source.key,
                    "target": e.target.key,
                    "condition": e.condition,
                    "ordering": e.ordering,
                }
                for e in edges
            ],
        }


class WorkflowListItemSerializer(serializers.Serializer):
    """Lightweight row for the workflow list, with live instance counts."""

    id = serializers.UUIDField()
    name = serializers.CharField()
    version = serializers.IntegerField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField()
    node_count = serializers.IntegerField()
    instance_count = serializers.IntegerField()


class StartInstanceSerializer(serializers.Serializer):
    payload = serializers.DictField(required=False, default=dict)


class TemplateCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    params = serializers.DictField()


class DecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "reject"])
    comment = serializers.CharField(required=False, allow_blank=True, default="")


class ApprovalRequestSerializer(serializers.Serializer):
    """The pending (or most recently decided) approval attached to an instance, if any."""

    id = serializers.UUIDField()
    approver_role = serializers.CharField()
    approver_user = serializers.SerializerMethodField()
    title = serializers.CharField()
    message = serializers.CharField()
    status = serializers.CharField()
    decided_by = serializers.SerializerMethodField()
    comment = serializers.CharField()
    decided_at = serializers.DateTimeField()
    created_at = serializers.DateTimeField()

    def get_approver_user(self, obj) -> str | None:
        return obj.approver_user.username if obj.approver_user_id else None

    def get_decided_by(self, obj) -> str | None:
        return obj.decided_by.username if obj.decided_by_id else None


class ExecutionLogSerializer(serializers.Serializer):
    level = serializers.CharField()
    message = serializers.CharField()
    data = serializers.JSONField()
    correlation_id = serializers.CharField()
    created_at = serializers.DateTimeField()


class NodeExecutionSerializer(serializers.Serializer):
    node_key = serializers.SerializerMethodField()
    node_type = serializers.SerializerMethodField()
    status = serializers.CharField()
    attempt = serializers.IntegerField()
    input = serializers.JSONField()
    output = serializers.JSONField()
    error = serializers.CharField()
    started_at = serializers.DateTimeField()
    finished_at = serializers.DateTimeField()
    logs = serializers.SerializerMethodField()

    def get_node_key(self, obj) -> str:
        return obj.node.key

    def get_node_type(self, obj) -> str:
        return obj.node.type

    def get_logs(self, obj) -> list:
        return ExecutionLogSerializer(obj.logs.all().order_by("created_at"), many=True).data


class InstanceSerializer(serializers.Serializer):
    """Instance summary (list rows / start response)."""

    id = serializers.UUIDField()
    workflow_id = serializers.UUIDField(source="workflow.id")
    workflow_name = serializers.CharField(source="workflow.name")
    status = serializers.CharField()
    current_node = serializers.SerializerMethodField()
    error = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()

    def get_current_node(self, obj) -> str | None:
        return obj.current_node.key if obj.current_node_id else None


class InstanceDetailSerializer(InstanceSerializer):
    """Full execution view: header + context + node-level timeline with logs."""

    context = serializers.JSONField()
    node_runs = serializers.SerializerMethodField()
    approval = serializers.SerializerMethodField()

    def get_node_runs(self, obj) -> list:
        runs = obj.node_runs.select_related("node").order_by("started_at", "attempt")
        return NodeExecutionSerializer(runs, many=True).data

    def get_approval(self, obj) -> dict | None:
        """The most recent approval request against this instance, if it has any."""
        req = (
            obj.approval_requests.select_related("approver_user", "decided_by")
            .order_by("-created_at")
            .first()
        )
        return ApprovalRequestSerializer(req).data if req else None
