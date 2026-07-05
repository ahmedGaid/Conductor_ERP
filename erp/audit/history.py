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


# Identity fields every module's snapshot may carry that aren't a meaningful "change" on a timeline.
# Nested dict/list values (e.g. an order's line items) are skipped separately below by type, since a
# module may reuse the same key name for a scalar (a journal's "lines" is a plain count).
_TIMELINE_SKIP = {"number", "id", "created_at", "updated_at"}


def record_timeline(entity_type: str, entity_id: str, limit: int = 30) -> list[dict]:
    """Generic per-record activity feed: ``[{action, actor_name, at, changes}]``, newest first.

    Every audit entry stores a full point-in-time snapshot in ``after`` (never a partial diff — see
    ``order_history`` above), so a field's "old -> new" is reconstructed here by comparing an entry's
    snapshot against the one immediately before it for the same record.
    """
    entries = list(
        AuditEntry.objects.filter(entity_type=entity_type, entity_id=entity_id)
        .select_related("actor")
        .order_by("created_at")
    )
    entries = entries[-max(1, min(limit, 100)):]

    out: list[dict] = []
    prev_after: dict | None = None
    for e in entries:
        after = e.after or {}
        changes = []
        if prev_after is not None:
            for field, new in after.items():
                if field in _TIMELINE_SKIP or isinstance(new, (dict, list)):
                    continue
                old = prev_after.get(field)
                if old != new:
                    changes.append({"field": field, "old": old, "new": new})
        out.append({
            "action": e.action,
            "actor_name": _actor_name(e.actor),
            "at": e.created_at.isoformat(),
            "changes": changes,
        })
        if after:
            prev_after = after
    out.reverse()
    return out
