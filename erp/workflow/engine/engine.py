"""The workflow execution engine — a persisted, crash-resumable state machine.

Contract (architecture/workflows.md):
- one DB transaction per node transition (NodeExecution + instance state + log commit together);
- resume strictly from the DB (no authoritative in-memory state);
- idempotency on external writes (sha256 key + durable ledger);
- exactly-one-winner edge selection;
- determinism (edges read in ordering ASC, id ASC; no wall-clock/random in control flow).
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from erp.core.correlation import get_correlation_id

from ..models import (
    ExecutionLog,
    InstanceStatus,
    LogLevel,
    NodeExecution,
    NodeRunStatus,
    NodeType,
    WorkflowInstance,
)
from .edges import select_edge
from .idempotency import key_for
from .registry import get_executor, is_external_write
from .types import EdgeSelectionError, NodeInput

DEFAULT_MAX_ATTEMPTS = 3
TERMINAL = {InstanceStatus.COMPLETED, InstanceStatus.FAILED}


def _log(instance, node_execution, level, message, data=None):
    ExecutionLog.objects.create(
        instance=instance,
        node_execution=node_execution,
        level=level,
        message=message,
        data=data,
        correlation_id=get_correlation_id() or "",
    )


def start_instance(workflow, initial_payload: dict, user=None) -> WorkflowInstance:
    """Create an instance positioned at the workflow's start node, then run it."""
    start_node = workflow.nodes.filter(type=NodeType.START).first()
    if start_node is None:
        raise ValueError("workflow has no start node")
    instance = WorkflowInstance.objects.create(
        workflow=workflow,
        status=InstanceStatus.PENDING,
        current_node=start_node,
        context=dict(initial_payload or {}),
        started_by=user if getattr(user, "is_authenticated", False) else None,
    )
    return run(instance.id)


def _incoming_payload(instance: WorkflowInstance) -> dict:
    last = (
        instance.node_runs.filter(status=NodeRunStatus.COMPLETED)
        .order_by("-finished_at", "-attempt")
        .first()
    )
    if last and last.output is not None:
        return dict(last.output)
    return dict(instance.context)  # start node sees the initial payload


def _next_attempt(instance, node) -> int:
    return instance.node_runs.filter(node=node).count() + 1


@transaction.atomic
def _step(instance_id, runtime: dict) -> bool:
    """Execute exactly one node transition atomically. Returns True to continue, False to stop."""
    # Lock only the instance row (current_node is a nullable FK; an outer join can't take FOR UPDATE).
    instance = WorkflowInstance.objects.select_for_update().get(id=instance_id)
    node = instance.current_node
    if node is None:
        instance.status = InstanceStatus.FAILED
        instance.error = "no current node"
        instance.save(update_fields=["status", "error", "updated_at"])
        return False

    attempt = _next_attempt(instance, node)
    incoming = _incoming_payload(instance)
    node_exec = NodeExecution.objects.create(
        instance=instance,
        node=node,
        status=NodeRunStatus.RUNNING,
        attempt=attempt,
        input=incoming,
        started_at=timezone.now(),
    )

    external = is_external_write(node)
    effective_runtime = dict(runtime or {})
    cached = None
    idem_key = None
    if external:
        idem_key = key_for(instance.id, node.id, attempt)
        from ..models import IdempotencyRecord

        record = IdempotencyRecord.objects.filter(key=idem_key).first()
        if record is not None:
            cached = record.response
        else:
            effective_runtime["idempotency_key"] = idem_key

    executor = get_executor(node.type)
    node_input = NodeInput(
        instance_context=dict(instance.context),
        node_config=dict(node.config or {}),
        incoming_payload=incoming,
        runtime=effective_runtime,
    )

    if cached is not None:
        from .types import NodeOutput

        output = NodeOutput(status="success", output_payload=cached)
    else:
        output = executor.run(node_input)

    # --- waiting ---
    if output.status == "waiting":
        node_exec.status = NodeRunStatus.WAITING
        node_exec.finished_at = timezone.now()
        node_exec.save(update_fields=["status", "finished_at"])
        instance.status = InstanceStatus.WAITING
        instance.save(update_fields=["status", "updated_at"])
        _log(instance, node_exec, LogLevel.INFO, f"node '{node.key}' waiting")
        return False

    # --- failed (with retry policy) ---
    if output.status == "failed":
        node_exec.status = NodeRunStatus.FAILED
        node_exec.error = output.error or "node failed"
        node_exec.finished_at = timezone.now()
        node_exec.save(update_fields=["status", "error", "finished_at"])
        max_attempts = int((node.config or {}).get("maxAttempts", DEFAULT_MAX_ATTEMPTS))
        # External writes are idempotent (key + ledger + DB UNIQUE), so retry is safe.
        if attempt < max_attempts:
            _log(instance, node_exec, LogLevel.WARN,
                 f"node '{node.key}' failed (attempt {attempt}/{max_attempts}); retrying",
                 {"error": output.error})
            return True  # same current_node; next _step uses attempt+1
        instance.status = InstanceStatus.FAILED
        instance.error = output.error or "node failed"
        instance.save(update_fields=["status", "error", "updated_at"])
        _log(instance, node_exec, LogLevel.ERROR, f"node '{node.key}' failed permanently",
             {"error": output.error})
        return False

    # --- success ---
    node_exec.status = NodeRunStatus.COMPLETED
    node_exec.output = output.output_payload
    node_exec.finished_at = timezone.now()
    node_exec.save(update_fields=["status", "output", "finished_at"])

    if external and cached is None:
        from ..models import IdempotencyRecord

        IdempotencyRecord.objects.get_or_create(
            key=idem_key,
            defaults={
                "instance_id": instance.id,
                "node_id": node.id,
                "response": output.output_payload,
            },
        )

    # Accumulate output into context under the node key.
    context = dict(instance.context)
    context[node.key] = output.output_payload

    if node.type == NodeType.END:
        instance.context = context
        instance.status = InstanceStatus.COMPLETED
        instance.current_node = None
        instance.save(update_fields=["context", "status", "current_node", "updated_at"])
        _log(instance, node_exec, LogLevel.INFO, "instance completed")
        return False

    try:
        edge = select_edge(node, context)
    except EdgeSelectionError as exc:
        instance.context = context
        instance.status = InstanceStatus.FAILED
        instance.error = str(exc)
        instance.save(update_fields=["context", "status", "error", "updated_at"])
        _log(instance, node_exec, LogLevel.ERROR, "edge selection failed", {"error": str(exc)})
        return False

    instance.context = context
    instance.current_node_id = edge.target_id
    instance.status = InstanceStatus.RUNNING
    instance.save(update_fields=["context", "current_node", "status", "updated_at"])
    _log(instance, node_exec, LogLevel.INFO, f"advanced '{node.key}' -> '{edge.target.key}'")
    return True


def run(instance_id, _runtime: dict | None = None, max_steps: int | None = None) -> WorkflowInstance:
    """Drive the instance until it reaches waiting or a terminal state (or max_steps)."""
    first = True
    steps = 0
    while True:
        if max_steps is not None and steps >= max_steps:
            break
        instance = WorkflowInstance.objects.get(id=instance_id)
        if instance.status in TERMINAL:
            break
        if instance.status == InstanceStatus.WAITING and not (first and _runtime):
            break
        runtime = _runtime if first else {}
        cont = _step(instance_id, runtime or {})
        first = False
        steps += 1
        if not cont:
            break
    return WorkflowInstance.objects.get(id=instance_id)


def resume(instance_id, decision: str | None = None) -> WorkflowInstance:
    """Resume a waiting instance (e.g. an approval) or continue after a crash."""
    runtime = {"decision": decision} if decision is not None else None
    return run(instance_id, _runtime=runtime)
