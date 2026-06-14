"""Integration adapters behind one interface: REST, SQL/PL-SQL, Webhook."""
from __future__ import annotations

from .rest import RestAdapter
from .sql import SqlAdapter
from .types import Adapter, AdapterCall, AdapterResult
from .webhook import WebhookAdapter

_REGISTRY: dict[str, type[Adapter]] = {
    "rest": RestAdapter,
    "sql": SqlAdapter,
    "webhook": WebhookAdapter,
}


def get_adapter(kind: str) -> Adapter:
    try:
        return _REGISTRY[kind]()
    except KeyError as exc:
        raise ValueError(f"unknown adapter kind: {kind!r}") from exc


__all__ = ["Adapter", "AdapterCall", "AdapterResult", "get_adapter"]
