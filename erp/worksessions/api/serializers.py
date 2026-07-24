"""Read shape for a WorkSession sent to the client. Hand-written (like other envelope views)."""
from __future__ import annotations

from ..models import WorkSession


def serialize_session(s: WorkSession) -> dict:
    return {
        "id": str(s.id),
        "workflow_key": s.workflow_key,
        "entity_type": s.entity_type,
        "related_entity_id": s.related_entity_id,
        "status": s.status,
        "payload": s.payload,
        "schema_version": s.schema_version,
        "client_version": s.client_version,
        "last_active_at": s.last_active_at.isoformat(),
    }
