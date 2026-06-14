"""End node: terminal. Engine marks the instance completed."""
from __future__ import annotations

from ..engine.types import NodeInput, NodeOutput


class EndExecutor:
    type = "end"
    is_external_write = False

    def run(self, node_input: NodeInput) -> NodeOutput:
        outcome = (node_input.node_config or {}).get("outcome", "completed")
        return NodeOutput(status="success", output_payload={"outcome": outcome})
