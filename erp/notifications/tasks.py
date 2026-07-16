"""Celery tasks for outbound webhook delivery.

Called directly (no worker required in dev, matching ``accounting.tasks``); a beat schedule sweeps
due retries when a worker is running. See ``services.webhooks`` for the actual HTTP + signing logic.
"""
from __future__ import annotations

from celery import shared_task


@shared_task(name="notifications.deliver_webhook")
def deliver_webhook(delivery_id: str) -> None:
    from .services.webhooks import attempt_delivery

    attempt_delivery(delivery_id)


@shared_task(name="notifications.retry_due_webhooks")
def retry_due_webhooks() -> int:
    """Beat-scheduled sweep: re-attempt every delivery whose backoff window has elapsed."""
    from .services.webhooks import attempt_delivery, due_retries

    due = list(due_retries().values_list("id", flat=True))
    for delivery_id in due:
        attempt_delivery(delivery_id)
    return len(due)
