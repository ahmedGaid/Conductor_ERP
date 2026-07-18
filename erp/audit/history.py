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


# Identity fields worth surfacing as humanization params (e.g. "Order {number}") even though they
# never appear in ``changes`` — they're excluded there by ``_TIMELINE_SKIP`` because they don't change.
_TIMELINE_PARAM_FIELDS = {"number", "name"}

# Modules whose writes are machine-caused rather than a direct human edit — the timeline surfaces
# this so a disputed entry stays click-verifiable back to its AI trace or import batch (STRATEGY
# mechanic 4). Anything else (the owning module's own service layer) reads as a plain human action.
_AI_MODULES = {"assistant"}
_IMPORT_MODULES = {"imports"}


def _source(module: str) -> str | None:
    if module in _AI_MODULES:
        return "ai"
    if module in _IMPORT_MODULES:
        return "import"
    return None


def record_timeline_page(
    entity_type: str, entity_id: str, page: int = 1, page_size: int = 30,
) -> tuple[list[dict], int]:
    """Paginated per-record activity feed: ``([{event, actor, at, params, changes}], total)``,
    newest first. Same whitelist-diff engine as :func:`record_timeline`, but page-aware: each page
    is fetched with one extra, older row as its diff baseline so a change on the first entry of a
    page is still correctly diffed against the entry immediately before it (not silently blanked).
    """
    qs = AuditEntry.objects.filter(entity_type=entity_type, entity_id=entity_id).order_by("created_at")
    total = qs.count()
    end_idx = max(total - (page - 1) * page_size, 0)
    start_idx = max(end_idx - page_size, 0)
    fetch_start = max(start_idx - 1, 0)
    has_baseline_row = fetch_start < start_idx

    entries = list(qs.select_related("actor")[fetch_start:end_idx])

    out: list[dict] = []
    prev_after: dict | None = None
    for i, e in enumerate(entries):
        after = e.after or {}
        changes = []
        if prev_after is not None:
            for field, new in after.items():
                if field in _TIMELINE_SKIP or isinstance(new, (dict, list)):
                    continue
                old = prev_after.get(field)
                if old != new:
                    changes.append({"field": field, "old": old, "new": new})
        if not (has_baseline_row and i == 0):
            out.append({
                "event": e.action,
                "actor": _actor_name(e.actor),
                "at": e.created_at.isoformat(),
                "params": {k: after[k] for k in _TIMELINE_PARAM_FIELDS if k in after},
                "changes": changes,
                "source": _source(e.module),
            })
        if after:
            prev_after = after
    out.reverse()
    return out, total
