"""Audit service — the only sanctioned way to write the immutable audit trail.

Every business write should call ``record(...)``. The correlation ID is pulled from the current
execution context automatically so each audit row is traceable end-to-end.
"""
from __future__ import annotations

from typing import Any

from erp.core.correlation import get_correlation_id

from .models import AuditEntry


def record(
    *,
    module: str,
    action: str,
    entity_type: str,
    entity_id: str | int | None = None,
    actor=None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    result: str = AuditEntry.Result.SUCCESS,
) -> AuditEntry:
    """Append one immutable audit entry. Never updates/deletes existing rows."""
    return AuditEntry.objects.create(
        module=module,
        action=action,
        entity_type=entity_type,
        entity_id="" if entity_id is None else str(entity_id),
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        before=before,
        after=after,
        result=result,
        correlation_id=get_correlation_id() or "",
    )
