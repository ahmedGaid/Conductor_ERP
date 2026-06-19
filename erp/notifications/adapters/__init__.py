"""Notification channel adapters — registered behind the single adapter interface."""
from __future__ import annotations

from .base import (  # noqa: F401
    NotificationAdapter,
    NotificationMessage,
    SendResult,
    UnknownChannelError,
    get_adapter,
    register_adapter,
    registered_channels,
)
from .email import EmailAdapter
from .whatsapp import WhatsAppAdapter

# Register the built-in channels. Additional gateways (SMS, payment, bank import) drop in here.
register_adapter(EmailAdapter())
register_adapter(WhatsAppAdapter())

__all__ = [
    "NotificationAdapter",
    "NotificationMessage",
    "SendResult",
    "UnknownChannelError",
    "get_adapter",
    "register_adapter",
    "registered_channels",
    "EmailAdapter",
    "WhatsAppAdapter",
]
