"""Read side of the audit trail: assemble a record's lifecycle history for the UI.

Each business transition stores a point-in-time snapshot in ``AuditEntry.after`` (see the sales /
purchasing order services). This turns that immutable trail into an ordered, display-ready list and
tags each entry with the workflow stage it belongs to, so the frontend tracker can attach the right
snapshot to each node.
"""
from __future__ import annotations

from .models import AuditEntry


def _actor_name(actor) -> str | None:
    if actor is None:
        return None
    full = actor.get_full_name() if hasattr(actor, "get_full_name") else ""
    return full or actor.get_username()


def order_history(entity_type: str, entity_id: str, stage_map: dict[str, str]) -> list[dict]:
    """Ordered lifecycle of one record: ``[{action, stage, actor_name, at, snapshot}]`` (oldest
    first). ``stage`` maps an audit action onto the workflow tracker's stage key (or ``None`` when
    the action has no forward stage)."""
    entries = (
        AuditEntry.objects.filter(entity_type=entity_type, entity_id=entity_id)
        .select_related("actor")
        .order_by("created_at")
    )
    return [
        {
            "action": e.action,
            "stage": stage_map.get(e.action),
            "actor_name": _actor_name(e.actor),
            "at": e.created_at.isoformat(),
            "snapshot": e.after,
        }
        for e in entries
    ]
