"""Assistant-action node — the agent as a workflow STEP.

Config: ``{ action, inputs?: {arg: template}, output_key? }``.

``action`` is a name from the EXISTING assistant catalog (``erp.assistant.services.actions``);
this node builds no new AI capability. ``inputs`` values are rendered against ``{ctx, in}`` with
the same template lib the API-Call node uses, so a mapping reads
``{"customer": "{{ ctx.po.customer }}"}``. The action's result lands in the run context under
``output_key`` (default: the node key's own slot, i.e. the raw result).

Safety, by construction:
- **Actor** — the action runs as the run's *triggering* actor (``instance.started_by``), never a
  system superuser. A run started by someone without the role gets the catalog's own calm refusal,
  turned into a failed node with that message.
- **Drafts only** — the catalog contains draft actions exclusively (posting stays on the module
  screens), and ``services._validate`` refuses to save a graph where a writing action isn't
  followed by an approval node. Both boundaries hold independently.
- **Traced** — the call is wrapped in the assistant's tracing seam, so the run step carries a
  trace id and the usage/cost numbers are click-verifiable from the existing AI surfaces.
- **AI off** — no assistant configured means an actionable blocker on the node, not a crash; a
  workflow with no assistant-action node is unaffected.
"""
from __future__ import annotations

from ..engine.types import NodeInput, NodeOutput
from ..lib import template

AI_OFF_BLOCKER = (
    "The assistant is switched off, so this step cannot run. Turn the assistant on in settings "
    "(or remove this step from the workflow) and start the run again."
)


def _render_inputs(inputs: dict, scope: dict) -> dict:
    """Render each mapped value against the run scope; non-strings pass through untouched."""
    return {key: template.render_value(value, scope) for key, value in (inputs or {}).items()}


class AssistantActionExecutor:
    type = "assistant_action"
    # The draft write happens inside the module contract, which has its own uniqueness rules; the
    # engine's idempotency ledger is for *external* systems. Kept False deliberately.
    is_external_write = False

    def run(self, node_input: NodeInput) -> NodeOutput:
        # Imported here, not at module scope: the workflow app must import cleanly with the
        # assistant app absent or disabled (the registry loads every executor at startup).
        from erp.assistant import client
        from erp.assistant.services import actions, tracing

        cfg = node_input.node_config or {}
        name = cfg.get("action")
        if not name:
            return NodeOutput(status="failed", output_payload={},
                              error="This step has no action chosen yet.")
        if name not in actions.ACTIONS:
            return NodeOutput(status="failed", output_payload={},
                              error=f"There is no action named '{name}'.")
        if not client.enabled():
            return NodeOutput(status="failed", output_payload={}, error=AI_OFF_BLOCKER)

        actor = (node_input.runtime or {}).get("actor")
        if actor is None or not getattr(actor, "is_authenticated", False):
            return NodeOutput(
                status="failed", output_payload={},
                error="This step needs the person who started the run, and this run has none. "
                      "Start it from the workflow screen while signed in.",
            )

        scope = {"ctx": node_input.instance_context, "in": node_input.incoming_payload}
        try:
            decision = _render_inputs(cfg.get("inputs") or {}, scope)
        except KeyError as exc:
            return NodeOutput(status="failed", output_payload={},
                              error=f"An input mapping points at missing data: {exc}")

        # The Trace row is written when the context manager exits, so the id is read after the
        # block — inside it, `handle.trace_id` is still empty.
        with tracing.trace_call("workflow", actor=actor) as handle:
            handle.meta["action"] = name
            proposal = actions.build(actor, name, decision)
            if "error" in proposal:
                handle.fail("action_refused")
                refusal = proposal["error"]
            elif "blocker" in proposal:
                handle.fail("action_blocked")
                refusal = _blocker_text(proposal["blocker"])
            else:
                refusal = None
                result = actions.execute(actor, name, proposal["payload"])
                handle.step(kind="action", name=name, ok=True)
        if refusal is not None:
            return NodeOutput(status="failed", output_payload={}, error=refusal)

        trace_id = str(getattr(handle, "trace_id", "") or "")
        payload = {
            "action": name,
            "summary": result.get("summary") or proposal.get("summary", ""),
            "links": result.get("links", []),
            "records": proposal.get("records", []),
            "risks": proposal.get("risks", []),
            "trace_id": trace_id,
        }
        output_key = cfg.get("output_key")
        return NodeOutput(status="success",
                          output_payload={output_key: payload} if output_key else payload)


def _blocker_text(blocker) -> str:
    """A build blocker (missing customer, ambiguous item…) read back as one human line."""
    if isinstance(blocker, dict):
        return blocker.get("message") or blocker.get("text") or "That could not be prepared."
    return str(blocker)
