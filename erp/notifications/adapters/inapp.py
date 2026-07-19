"""In-app channel adapter — the row IS the delivery.

Unlike email/WhatsApp, an in-app notification never leaves the system: dispatch already writes a
durable ``Notification`` row, and the inbox reads it back. So ``send`` has nothing to transmit — it
just confirms acceptance with a deterministic reference. This keeps the one adapter interface intact
(dispatch stays channel-agnostic) while the "channel" is really the local inbox.
"""
from __future__ import annotations

import hashlib

from .base import NotificationMessage, SendResult


class InAppAdapter:
    channel = "inapp"

    def send(self, message: NotificationMessage) -> SendResult:
        digest = hashlib.sha256(
            f"{message.recipient}|{message.subject}|{message.body}".encode()
        ).hexdigest()
        return SendResult(provider_ref=f"inapp-{digest[:20]}", ok=True)
