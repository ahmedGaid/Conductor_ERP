"""API Call node.

Config (validated): { method, url_template, headers_template?, body_template?, write?, adapter? }.
Resolves templates against { ctx, in } via lib.template, then delegates to an adapter (default REST;
'sql'/'webhook' selectable). Reports is_external_write = config.write so the engine wraps it in
idempotency. Never calls the network directly — always through the adapter interface.
"""
from __future__ import annotations

from ..adapters import get_adapter
from ..adapters.types import AdapterCall
from ..engine.types import NodeInput, NodeOutput
from ..lib import template


class ApiCallExecutor:
    type = "api_call"

    # The engine reads this per-node via is_external_write_for(config); see registry note.
    is_external_write = False

    def run(self, node_input: NodeInput) -> NodeOutput:
        cfg = node_input.node_config or {}
        scope = {
            "ctx": node_input.instance_context,
            "in": node_input.incoming_payload,
            "idem": node_input.runtime.get("idempotency_key"),
        }

        kind = cfg.get("adapter", "rest")
        try:
            adapter_config = self._build_config(cfg, scope)
        except KeyError as exc:
            return NodeOutput(status="failed", output_payload={}, error=str(exc))

        adapter = get_adapter(kind)
        call = AdapterCall(
            config=adapter_config,
            payload=adapter_config.get("body", {}) or {},
            idempotency_key=node_input.runtime.get("idempotency_key"),
        )
        result = adapter.call(call)
        if not result.ok:
            return NodeOutput(
                status="failed", output_payload={}, error=result.error or "adapter call failed"
            )
        return NodeOutput(status="success", output_payload=_as_dict(result.data))

    @staticmethod
    def _build_config(cfg: dict, scope: dict) -> dict:
        kind = cfg.get("adapter", "rest")
        if kind == "sql":
            return {
                "statement": cfg["statement"],
                "params": template.render_value(cfg.get("params", []), scope),
            }
        out = {
            "method": cfg.get("method", "GET"),
            "url": template.render(cfg["url_template"], scope),
        }
        if cfg.get("headers_template"):
            out["headers"] = template.render_value(cfg["headers_template"], scope)
        if cfg.get("body_template") is not None:
            out["body"] = template.render_value(cfg["body_template"], scope)
        return out


def _as_dict(data) -> dict:
    if isinstance(data, dict):
        return data
    return {"data": data}
