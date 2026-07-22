"""Workflow data model (re-expressed from the PHASE specs on Django ORM).

Tables: Workflow, WorkflowNode, WorkflowEdge, WorkflowInstance, NodeExecution, ExecutionLog,
IdempotencyRecord. The IdempotencyRecord is the durable dedupe ledger the engine's idempotency
contract requires.
"""
from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class InstanceStatus(models.TextChoices):
    PENDING = "pending"
    RUNNING = "running"
    WAITING = "waiting"
    FAILED = "failed"
    COMPLETED = "completed"


class NodeRunStatus(models.TextChoices):
    PENDING = "pending"
    RUNNING = "running"
    WAITING = "waiting"
    FAILED = "failed"
    COMPLETED = "completed"


class NodeType(models.TextChoices):
    START = "start"
    API_CALL = "api_call"
    APPROVAL = "approval"
    ASSISTANT_ACTION = "assistant_action"
    CONDITION = "condition"
    SCRIPT = "script"
    NOTIFICATION = "notification"
    END = "end"


class LogLevel(models.TextChoices):
    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


class ApprovalStatus(models.TextChoices):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Workflow(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    version = models.IntegerField(default=1)
    status = models.CharField(max_length=16, default="active")  # active | archived
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workflow"

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.name} v{self.version}"


class WorkflowTrigger(models.Model):
    """Subscribes a workflow to a domain event, reusing the same event-name catalog Webhooks use.

    An optional JSON-logic ``condition`` gates the start (same shape/engine as edge conditions —
    see ``erp.workflow.lib.jsonlogic``). No condition = fires on every occurrence of the event.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name="triggers")
    event_name = models.CharField(max_length=64)
    condition = models.JSONField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workflow_trigger"
        indexes = [models.Index(fields=["event_name", "is_active"])]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.workflow.name} on {self.event_name}"


class WorkflowNode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name="nodes")
    # Stable per-workflow key used in definitions/seeds (e.g. "check_budget").
    key = models.CharField(max_length=64)
    # 32, not 16: "assistant_action" is exactly 16 characters — no headroom for the next node type.
    type = models.CharField(max_length=32, choices=NodeType.choices)
    config = models.JSONField(default=dict)
    position = models.JSONField(default=dict)  # { x, y }

    class Meta:
        db_table = "workflow_node"
        unique_together = [("workflow", "key")]


class WorkflowEdge(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name="edges")
    source = models.ForeignKey(WorkflowNode, on_delete=models.CASCADE, related_name="out_edges")
    target = models.ForeignKey(WorkflowNode, on_delete=models.CASCADE, related_name="in_edges")
    condition = models.JSONField(null=True, blank=True)  # JSON-logic; null for unconditional
    ordering = models.IntegerField(default=0)  # STABLE deterministic edge order

    class Meta:
        db_table = "workflow_edge"
        indexes = [models.Index(fields=["workflow", "source", "ordering"])]
        unique_together = [("source", "ordering")]


class WorkflowInstance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow = models.ForeignKey(Workflow, on_delete=models.PROTECT, related_name="instances")
    status = models.CharField(
        max_length=16, choices=InstanceStatus.choices, default=InstanceStatus.PENDING
    )
    current_node = models.ForeignKey(
        WorkflowNode, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    context = models.JSONField(default=dict)
    started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    error = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workflow_instance"
        indexes = [models.Index(fields=["status"])]


class NodeExecution(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    instance = models.ForeignKey(
        WorkflowInstance, on_delete=models.CASCADE, related_name="node_runs"
    )
    node = models.ForeignKey(WorkflowNode, on_delete=models.CASCADE, related_name="+")
    status = models.CharField(
        max_length=16, choices=NodeRunStatus.choices, default=NodeRunStatus.PENDING
    )
    attempt = models.IntegerField(default=1)
    input = models.JSONField(null=True, blank=True)
    output = models.JSONField(null=True, blank=True)
    error = models.TextField(blank=True, default="")
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "workflow_node_execution"
        indexes = [models.Index(fields=["instance"])]
        # Makes a transition write idempotent (one row per instance+node+attempt).
        unique_together = [("instance", "node", "attempt")]


class ExecutionLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    instance = models.ForeignKey(WorkflowInstance, on_delete=models.CASCADE, related_name="logs")
    node_execution = models.ForeignKey(
        NodeExecution, null=True, blank=True, on_delete=models.CASCADE, related_name="logs"
    )
    level = models.CharField(max_length=8, choices=LogLevel.choices, default=LogLevel.INFO)
    message = models.CharField(max_length=500)
    data = models.JSONField(null=True, blank=True)
    correlation_id = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workflow_execution_log"
        indexes = [models.Index(fields=["instance"])]


class ApprovalRequest(models.Model):
    """One human decision needed at an ``approval`` node — created when a run halts there.

    ``approver_user``/``approver_role`` are the node's config, copied at creation time (an edit to
    the workflow definition after the request was raised must not retroactively change who could
    decide it). Both blank means "any authenticated user" — the pre-FILE_09 behavior, kept as the
    default so a graph author who hasn't set an approver yet doesn't lock everyone out.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    instance = models.ForeignKey(
        WorkflowInstance, on_delete=models.CASCADE, related_name="approval_requests"
    )
    node = models.ForeignKey(WorkflowNode, on_delete=models.CASCADE, related_name="+")
    approver_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    approver_role = models.CharField(max_length=64, blank=True, default="")
    title = models.CharField(max_length=200, blank=True, default="")
    message = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=16, choices=ApprovalStatus.choices, default=ApprovalStatus.PENDING
    )
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    comment = models.TextField(blank=True, default="")
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workflow_approval_request"
        indexes = [models.Index(fields=["instance", "status"])]


class IdempotencyRecord(models.Model):
    key = models.CharField(primary_key=True, max_length=64)  # sha256 hex
    instance_id = models.UUIDField()
    node_id = models.UUIDField()
    response = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workflow_idempotency_record"
