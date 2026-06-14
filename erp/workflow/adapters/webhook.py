"""Webhook adapter — outbound POST of the payload as JSON.

Config: { url, headers? }. Same Idempotency-Key behavior as the REST adapter.
"""
from __future__ import annotations

from .rest import RestAdapter
from .types import AdapterCall, AdapterResult


class WebhookAdapter:
    kind = "webhook"

    def call(self, call: AdapterCall) -> AdapterResult:
        cfg = call.config
        rest_call = AdapterCall(
            config={
                "method": "POST",
                "url": cfg["url"],
                "headers": cfg.get("headers") or {},
                "body": call.payload,
            },
            payload=call.payload,
            idempotency_key=call.idempotency_key,
        )
        return RestAdapter().call(rest_call)
