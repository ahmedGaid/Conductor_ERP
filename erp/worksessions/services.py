"""WorkSession service — draft bookkeeping only. NEVER writes a business model.

Every function is owner-scoped: a caller can only see or mutate its own drafts. Completion flips a
status; the real business write happens in the owning module's service contract, untouched.
"""
from __future__ import annotations

from dataclasses import dataclass

from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import WorkSession


@dataclass(frozen=True)
class UpsertResult:
    session: WorkSession
    conflict: bool


def get_active(owner, workflow_key: str, related_entity_id: str = "") -> WorkSession | None:
    return WorkSession.objects.filter(
        owner=owner, workflow_key=workflow_key, related_entity_id=related_entity_id,
        status=WorkSession.Status.ACTIVE,
    ).first()


def list_active(owner) -> list[WorkSession]:
    return list(
        WorkSession.objects.filter(owner=owner, status=WorkSession.Status.ACTIVE)
        .order_by("-last_active_at")
    )


@transaction.atomic
def upsert_draft(
    owner, *, workflow_key: str, payload: dict, entity_type: str = "",
    related_entity_id: str = "", schema_version: int = 1, client_version: int = 0,
    expected_version: int | None = None, import_batch=None,
) -> UpsertResult:
    """Create or update the single ACTIVE draft for (owner, workflow_key, related_entity_id).

    Conflict: if ``expected_version`` is given and is < the stored ``client_version``, another writer
    moved ahead since this client last read — return ``conflict=True`` WITHOUT clobbering. The client
    decides whether to overwrite (last-write-wins) after warning the user.
    """
    existing = (
        WorkSession.objects.select_for_update()
        .filter(owner=owner, workflow_key=workflow_key, related_entity_id=related_entity_id,
                status=WorkSession.Status.ACTIVE)
        .first()
    )
    if existing is None:
        try:
            with transaction.atomic():
                session = WorkSession.objects.create(
                    owner=owner, workflow_key=workflow_key, entity_type=entity_type,
                    related_entity_id=related_entity_id, payload=payload,
                    schema_version=schema_version, client_version=max(client_version, 1),
                    last_active_at=timezone.now(), import_batch=import_batch,
                )
            return UpsertResult(session=session, conflict=False)
        except IntegrityError:
            # A concurrent create won the unique-active slot — fall through to update it.
            existing = (
                WorkSession.objects.select_for_update()
                .filter(owner=owner, workflow_key=workflow_key,
                        related_entity_id=related_entity_id, status=WorkSession.Status.ACTIVE)
                .first()
            )

    if expected_version is not None and expected_version < existing.client_version:
        return UpsertResult(session=existing, conflict=True)

    existing.payload = payload
    existing.entity_type = entity_type or existing.entity_type
    existing.schema_version = schema_version
    existing.client_version = existing.client_version + 1
    existing.last_active_at = timezone.now()
    if import_batch is not None:
        existing.import_batch = import_batch
    existing.save(update_fields=[
        "payload", "entity_type", "schema_version", "client_version",
        "last_active_at", "import_batch", "updated_at",
    ])
    return UpsertResult(session=existing, conflict=False)


def complete(owner, session_id, *, related_entity_id: str = "") -> None:
    session = WorkSession.objects.filter(owner=owner, id=session_id).first()
    if session is None:
        return  # not found or not owned — no-op
    session.status = WorkSession.Status.COMPLETED
    if related_entity_id:
        session.related_entity_id = related_entity_id
    session.save(update_fields=["status", "related_entity_id", "updated_at"])


def discard(owner, session_id) -> None:
    WorkSession.objects.filter(owner=owner, id=session_id).update(
        status=WorkSession.Status.DISCARDED
    )
