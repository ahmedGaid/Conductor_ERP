"""Condition node: passes through; the engine then runs edges.select_edge (exactly-one-winner)."""
from __future__ import annotations

from ..engine.types import NodeInput, NodeOutput


class ConditionExecutor:
    type = "condition"
    is_external_write = False

    def run(self, node_input: NodeInput) -> NodeOutput:
        return NodeOutput(status="success", output_payload=dict(node_input.incoming_payload))
