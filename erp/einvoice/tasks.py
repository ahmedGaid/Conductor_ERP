"""Celery tasks for the ETA e-invoice lifecycle.

Called directly in dev (no worker required, matching ``accounting.tasks``); a beat schedule sweeps
due polls when a worker is running. See ``services.issue.due_polls``/``poll_invoice`` for the actual
backoff/cap logic.
"""
from __future__ import annotations

from celery import shared_task


@shared_task(name="einvoice.reconcile_submitted")
def reconcile_submitted() -> int:
    """Beat-scheduled sweep: poll every submitted e-invoice whose backoff window has elapsed."""
    from .services import due_polls, poll_invoice
    from .domain.models import ETAInvoice

    due_ids = list(due_polls().values_list("id", flat=True))
    for eta_id in due_ids:
        poll_invoice(ETAInvoice.objects.get(id=eta_id))
    return len(due_ids)
