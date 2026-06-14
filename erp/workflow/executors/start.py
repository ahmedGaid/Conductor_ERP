"""Start node: seeds context from the instance's initial payload."""
from __future__ import annotations

from ..engine.types import NodeInput, NodeOutput


class StartExecutor:
    type = "start"
    is_external_write = False

    def run(self, node_input: NodeInput) -> NodeOutput:
        return NodeOutput(status="success", output_payload=dict(node_input.incoming_payload))
