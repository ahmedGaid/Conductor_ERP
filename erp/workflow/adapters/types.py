"""Shared adapter interface. Engine/executors never branch on adapter kind."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class AdapterCall:
    config: dict[str, Any]  # adapter-specific; validated inside the adapter
    payload: dict[str, Any] = field(default_factory=dict)
    idempotency_key: str | None = None  # present => adapter MUST dedupe the write


@dataclass
class AdapterResult:
    ok: bool
    data: Any = None
    error: str | None = None
    status: int | None = None


@runtime_checkable
class Adapter(Protocol):
    kind: str

    def call(self, call: AdapterCall) -> AdapterResult:  # pragma: no cover - protocol
        ...
