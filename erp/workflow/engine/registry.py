"""NodeType -> executor mapping (frozen).

Adding a node type later = one executor file + one entry here; the engine never changes.
"""
from __future__ import annotations

from types import MappingProxyType

from ..executors.api_call import ApiCallExecutor
from ..executors.approval import ApprovalExecutor
from ..executors.condition import ConditionExecutor
from ..executors.end import EndExecutor
from ..executors.script import ScriptExecutor
from ..executors.start import StartExecutor
from ..models import NodeType, WorkflowNode
from .types import NodeExecutor

_REGISTRY = MappingProxyType(
    {
        NodeType.START: StartExecutor(),
        NodeType.API_CALL: ApiCallExecutor(),
        NodeType.APPROVAL: ApprovalExecutor(),
        NodeType.CONDITION: ConditionExecutor(),
        NodeType.SCRIPT: ScriptExecutor(),
        NodeType.END: EndExecutor(),
    }
)


def get_executor(node_type: str) -> NodeExecutor:
    try:
        return _REGISTRY[node_type]
    except KeyError as exc:
        raise ValueError(f"no executor for node type {node_type!r}") from exc


def is_external_write(node: WorkflowNode) -> bool:
    """An API Call with config.write == True is an external write (engine enforces idempotency)."""
    if node.type == NodeType.API_CALL:
        return bool((node.config or {}).get("write"))
    return bool(getattr(get_executor(node.type), "is_external_write", False))
