"""At-most-once execution for replay-sensitive API writes.

A retried request (double-click, network replay, client retry-on-timeout) must not repeat its
side-effect. Views pass the client's ``Idempotency-Key`` header here; the first call runs the
create and records the resulting object id, replays return that id without running the create
again. The key row and the side-effect commit in one transaction, so a crash mid-create never
burns the key.
"""
from __future__ import annotations

from collections.abc import Callable

from django.db import transaction

from .models import IdempotencyKey


def run_once(*, key: str, endpoint: str, create: Callable) -> tuple[str, bool]:
    """Run ``create()`` at most once per (endpoint, key). Returns ``(object_id, created)``.

    ``create`` must return the created model instance. An empty key means the client opted out —
    the create always runs. A concurrent replay blocks on the key row's unique index until the
    first request commits, then sees its result.
    """
    if not key:
        return str(create().id), True
    with transaction.atomic():
        record, fresh = IdempotencyKey.objects.select_for_update().get_or_create(
            endpoint=endpoint, key=key
        )
        if not fresh:
            return record.object_id, False
        obj = create()
        record.object_id = str(obj.id)
        record.save(update_fields=["object_id", "updated_at"])
        return record.object_id, True
