"""Approval node (human).

First entry returns `waiting` (engine persists and exits). On resume the engine passes the decision
through `node_input.runtime['decision']`; we write `{approved: bool}` so downstream Condition edges
can branch on `<node_key>.approved`.
"""
from __future__ import annotations

from ..engine.types import NodeInput, NodeOutput


def apply_decision(decision: str) -> dict:
    return {"approved": decision == "approve", "decision": decision}


class ApprovalExecutor:
    type = "approval"
    is_external_write = False

    def run(self, node_input: NodeInput) -> NodeOutput:
        decision = (node_input.runtime or {}).get("decision")
        if decision is None:
            return NodeOutput(status="waiting", output_payload={})
        return NodeOutput(status="success", output_payload=apply_decision(decision))
