"""Script node — NOT arbitrary code.

Config: { logic: <json-logic>, output_key?: str }. Evaluated with the safe jsonlogic evaluator
against the instance context only. Hard ban on eval/exec/Function/import at runtime (gate02 greps).
"""
from __future__ import annotations

from ..engine.types import NodeInput, NodeOutput
from ..lib.jsonlogic import jsonlogic


class ScriptExecutor:
    type = "script"
    is_external_write = False

    def run(self, node_input: NodeInput) -> NodeOutput:
        cfg = node_input.node_config or {}
        logic = cfg.get("logic")
        output_key = cfg.get("output_key", "result")
        scope = {**node_input.instance_context, **node_input.incoming_payload}
        try:
            value = jsonlogic(logic, scope)
        except Exception as exc:  # noqa: BLE001
            return NodeOutput(status="failed", output_payload={}, error=f"script error: {exc}")
        return NodeOutput(status="success", output_payload={output_key: value})
