"""Notification node: send a message through the existing notifications dispatch service.

Config: channel, recipient, subject, body (all template strings rendered against instance
context — see erp.workflow.lib.template), optional reference. No new adapter — reuses
erp.notifications.services.dispatch exactly like other in-process module calls in this engine.
"""
from __future__ import annotations

from ..engine.types import NodeInput, NodeOutput
from ..lib.template import render_value


class NotificationExecutor:
    type = "notification"
    is_external_write = False

    def run(self, node_input: NodeInput) -> NodeOutput:
        from erp.notifications.domain.models import NotificationChannel
        from erp.notifications.services import dispatch

        cfg = node_input.node_config or {}
        try:
            recipient = render_value(cfg.get("recipient", ""), {"ctx": node_input.instance_context})
            subject = render_value(cfg.get("subject", ""), {"ctx": node_input.instance_context})
            body = render_value(cfg.get("body", ""), {"ctx": node_input.instance_context})
            reference = render_value(cfg.get("reference", ""), {"ctx": node_input.instance_context})
        except KeyError as exc:
            return NodeOutput(status="failed", output_payload={}, error=str(exc))

        if not recipient:
            return NodeOutput(status="failed", output_payload={},
                               error="This step has no recipient set.")

        channel = cfg.get("channel", NotificationChannel.INAPP)
        dispatch(
            channel=channel,
            recipient=recipient,
            subject=subject,
            body=body,
            reference=reference,
            event_name="workflow.notification",
        )
        return NodeOutput(status="success", output_payload={"sent_to": recipient})
