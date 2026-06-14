"""In-process domain event bus with subscriber isolation.

Modules publish domain events (e.g. ``InvoiceCreated``, ``InventoryUpdated``,
``WorkflowStarted``); other modules subscribe. A subscriber that raises must NEVER break the
publisher — exceptions are caught, logged structurally, and the publish call still succeeds.
This is the only sanctioned cross-module communication channel besides public service
interfaces and contracts.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable

from .correlation import get_correlation_id

logger = logging.getLogger("erp.core.events")

Handler = Callable[["DomainEvent"], None]


@dataclass(frozen=True)
class DomainEvent:
    name: str
    payload: dict = field(default_factory=dict)
    correlation_id: str | None = None


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[Handler]] = defaultdict(list)

    def subscribe(self, event_name: str, handler: Handler) -> None:
        self._subscribers[event_name].append(handler)

    def publish(self, name: str, payload: dict | None = None) -> DomainEvent:
        event = DomainEvent(
            name=name, payload=payload or {}, correlation_id=get_correlation_id()
        )
        for handler in list(self._subscribers.get(name, [])):
            try:
                handler(event)
            except Exception:  # noqa: BLE001 - isolation is the whole point
                logger.error(
                    "Event subscriber failed",
                    exc_info=True,
                    extra={"data": {"event": name, "handler": getattr(handler, "__name__", str(handler))}},
                )
        return event


# Process-wide singleton bus.
bus = EventBus()
