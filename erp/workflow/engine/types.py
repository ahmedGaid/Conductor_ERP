"""Node I/O contract types and the NodeExecutor interface.

Every executor is a pure function of its inputs plus at most ONE explicitly-declared side effect
(an adapter call). No hidden global state.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

RunStatus = Literal["success", "failed", "waiting"]


@dataclass
class NodeInput:
    instance_context: dict[str, Any]
    node_config: dict[str, Any]
    incoming_payload: dict[str, Any] = field(default_factory=dict)
    # Extra runtime hints (e.g. an approval decision) the engine passes through on resume.
    runtime: dict[str, Any] = field(default_factory=dict)


@dataclass
class NodeOutput:
    status: RunStatus
    output_payload: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@runtime_checkable
class NodeExecutor(Protocol):
    type: str
    is_external_write: bool

    def run(self, node_input: NodeInput) -> NodeOutput:  # pragma: no cover - protocol
        ...


class EdgeSelectionError(Exception):
    """Raised when a node does not have exactly one winning out-edge."""
