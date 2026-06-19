"""WhatsApp channel adapter — a deterministic, offline-safe stub.

A real WhatsApp Business / payment / bank gateway needs credentials + network access — out of scope
for a customer-hosted offline build. This stub simulates the contract deterministically (no network):
``send`` returns a stable provider reference derived from the message hash, so retries are idempotent
and tests are reproducible. Swapping in a real HTTP client later touches only this file.
"""
from __future__ import annotations

import hashlib

from .base import NotificationMessage, SendResult


class WhatsAppAdapter:
    channel = "whatsapp"

    def send(self, message: NotificationMessage) -> SendResult:
        digest = hashlib.sha256(
            f"{message.recipient}|{message.subject}|{message.body}".encode("utf-8")
        ).hexdigest()
        return SendResult(provider_ref=f"wamid-{digest[:20]}", ok=True)
