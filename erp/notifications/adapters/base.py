"""The single notification-adapter interface + a channel registry.

Every channel (email, WhatsApp, SMS, a payment/bank gateway later) is a swappable adapter that
implements the same tiny contract: ``send(NotificationMessage) -> SendResult``. The dispatch service
talks ONLY to this interface — it never knows whether the channel is SMTP, an HTTP API, or a stub —
so adding or replacing a channel touches one file and registers it here. This mirrors the ETA
adapter pattern: offline-safe by default, real clients drop in behind the same surface.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class NotificationMessage:
    recipient: str
    subject: str = ""
    body: str = ""


@dataclass(frozen=True)
class SendResult:
    provider_ref: str = ""   # the channel's message id (or a deterministic stub id)
    ok: bool = True
    error: str = ""


@runtime_checkable
class NotificationAdapter(Protocol):
    """The one interface every channel implements."""

    channel: str

    def send(self, message: NotificationMessage) -> SendResult:  # pragma: no cover - protocol
        ...


# Channel registry — populated at import time in adapters/__init__.py.
_ADAPTERS: dict[str, NotificationAdapter] = {}


def register_adapter(adapter: NotificationAdapter) -> None:
    _ADAPTERS[adapter.channel] = adapter


def get_adapter(channel: str) -> NotificationAdapter:
    try:
        return _ADAPTERS[channel]
    except KeyError as exc:
        raise UnknownChannelError(channel) from exc


def registered_channels() -> list[str]:
    return sorted(_ADAPTERS)


class UnknownChannelError(Exception):
    """No adapter is registered for the requested channel."""

    def __init__(self, channel: str) -> None:
        super().__init__(f"no notification adapter registered for channel '{channel}'")
        self.channel = channel
