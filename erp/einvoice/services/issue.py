"""E-invoice lifecycle services.

record_invoice (idempotent, from a posted sales invoice) → submit (prepare, assigns a reference) →
poll (ask for the outcome). Every transition is atomic. The submission itself goes through the ETA
adapter, so the only side effect is the (currently simulated) external call + the persisted status.

While ETA is not live (``eta_adapter.is_live()`` is False) nothing reaches the Tax Authority, so
``poll_invoice`` cannot reach ``valid`` — a prepared invoice rests at ``submitted``.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from erp.audit import services as audit
from erp.core.events import bus

from .. import events
from ..domain.models import ETAInvoice, ETAStatus
from ..errors import InvalidEInvoiceTransitionError
from . import eta_adapter

# FILE_04 — backoff schedule for the automatic reconciliation sweep, seconds: 5m / 15m / 1h / 6h / 24h,
# then repeat the last step. Mirrors notifications.services.webhooks' RETRY_SCHEDULE shape.
POLL_BACKOFF_SCHEDULE = [300, 900, 3600, 21600, 86400]
# After this many attempts with still no verdict, stop auto-polling and flag for an operator to look
# (a stuck invoice must raise a visible alert, not hang silently) — a manual poll can still retry it.
MAX_POLL_ATTEMPTS = 10


@dataclass
class EInvoiceInput:
    invoice_number: str
    issue_date: dt.date
    order_number: str = ""
    customer_code: str = ""
    customer_name: str = ""
    customer_tax_registration_number: str = ""
    customer_national_id: str = ""
    currency: str = "EGP"
    tax_code: str = ""
    net_minor: int = 0
    tax_minor: int = 0
    total_minor: int = 0
    # Branch code of the source order (business key) — stamps the e-invoice's data scope.
    branch_code: str = ""


def _document(eta: ETAInvoice) -> dict:
    return {
        "invoice": eta.invoice_number,
        "customer": eta.customer_code,
        "customer_name": eta.customer_name,
        "customer_tax_registration_number": eta.customer_tax_registration_number,
        "customer_national_id": eta.customer_national_id,
        "date": str(eta.issue_date),
        "currency": eta.currency,
        "tax_code": eta.tax_code,
        "net": eta.net_minor,
        "tax": eta.tax_minor,
        "total": eta.total_minor,
    }


@transaction.atomic
def record_invoice(data: EInvoiceInput, actor=None) -> ETAInvoice:
    """Record (or return the existing) ETA e-invoice for a posted sales invoice. Idempotent."""
    existing = ETAInvoice.objects.filter(invoice_number=data.invoice_number).first()
    if existing is not None:
        return existing
    branch = None
    if data.branch_code:
        from erp.core.models import Branch

        branch = Branch.objects.filter(code=data.branch_code).first()
    eta = ETAInvoice.objects.create(
        invoice_number=data.invoice_number, order_number=data.order_number,
        customer_code=data.customer_code, customer_name=data.customer_name,
        customer_tax_registration_number=data.customer_tax_registration_number,
        customer_national_id=data.customer_national_id,
        issue_date=data.issue_date, currency=data.currency, tax_code=data.tax_code,
        net_minor=data.net_minor, tax_minor=data.tax_minor, total_minor=data.total_minor,
        status=ETAStatus.DRAFT, branch=branch,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
    )
    eta.document_hash = eta_adapter.document_hash(_document(eta))
    eta.save(update_fields=["document_hash"])
    audit.record(module="einvoice", action="record_invoice", entity_type="ETAInvoice",
                 entity_id=eta.invoice_number, actor=actor)
    bus.publish(events.EINVOICE_RECORDED, {"invoice": eta.invoice_number})
    return eta


@transaction.atomic
def submit_invoice(eta: ETAInvoice, actor=None) -> ETAInvoice:
    """Prepare a draft (or re-prepare a prepared) e-invoice for ETA. Idempotent on the reference."""
    from erp.assistant.services.simulation import in_sim_mode, record_skip

    if in_sim_mode():
        # L2 dry run (os-foundations FILE_04): no ETA submission, no persisted status change.
        record_skip("einvoice_submit")
        return eta
    if eta.status not in (ETAStatus.DRAFT, ETAStatus.SUBMITTED):
        raise InvalidEInvoiceTransitionError(
            data={"invoice": eta.invoice_number, "status": eta.status, "expected": "draft|submitted"}
        )
    # Idempotency: an invoice already submitted with a reference is never re-sent — that avoids a
    # duplicate document at ETA (which would 422) and keeps the assigned UUID stable.
    if eta.status == ETAStatus.SUBMITTED and eta.uuid:
        return eta

    result = eta_adapter.submit(_document(eta))
    if not result.accepted:
        if result.retryable:
            # Transient (network/5xx/unreadable response): leave the invoice submittable and record
            # the reason, rather than marking it rejected on something that may succeed on retry.
            eta.error_text = result.error
            eta.save(update_fields=["error_text", "updated_at"])
            return eta
        eta.status = ETAStatus.REJECTED
        eta.error_text = result.error
        eta.submission_uuid = result.submission_uuid or eta.submission_uuid
        eta.save(update_fields=["status", "error_text", "submission_uuid", "updated_at"])
        audit.record(module="einvoice", action="submit_invoice", entity_type="ETAInvoice",
                     entity_id=eta.invoice_number, actor=actor, after={"status": eta.status})
        bus.publish(events.EINVOICE_REJECTED, {"invoice": eta.invoice_number})
        return eta
    eta.uuid = result.uuid
    eta.long_id = result.long_id or eta.long_id
    eta.submission_uuid = result.submission_uuid or eta.submission_uuid
    eta.status = ETAStatus.SUBMITTED
    eta.submitted_at = eta.submitted_at or timezone.now()
    eta.error_text = ""
    eta.save(update_fields=["uuid", "long_id", "submission_uuid", "status", "submitted_at",
                            "error_text", "updated_at"])
    audit.record(module="einvoice", action="submit_invoice", entity_type="ETAInvoice",
                 entity_id=eta.invoice_number, actor=actor, after={"uuid": eta.uuid})
    bus.publish(events.EINVOICE_SUBMITTED, {"invoice": eta.invoice_number, "uuid": eta.uuid})
    return eta


@transaction.atomic
def poll_invoice(eta: ETAInvoice, actor=None) -> ETAInvoice:
    """Poll ETA for a submitted e-invoice's validation result.

    Called both from the UI's manual "poll" action (immediate, ignores backoff) and from the beat
    sweep (:func:`due_polls` already filtered to eligible rows). Idempotent — polling an already-
    settled (``valid``/``rejected``) invoice raises rather than re-asking."""
    if eta.status not in (ETAStatus.SUBMITTED, ETAStatus.VALID):
        raise InvalidEInvoiceTransitionError(
            data={"invoice": eta.invoice_number, "status": eta.status, "expected": "submitted"}
        )
    outcome = eta_adapter.query(eta.uuid)
    if outcome == "pending":
        # No Tax-Authority verdict yet — either still processing at ETA, or a transient read
        # failure (the adapter can't tell the two apart; see eta_adapter.query's docstring). Either
        # way: don't invent a verdict, just track the attempt and back off the next automatic try.
        eta.poll_attempts += 1
        if eta.poll_attempts >= MAX_POLL_ATTEMPTS:
            eta.poll_stalled = True
            eta.next_poll_at = None
        else:
            delay = POLL_BACKOFF_SCHEDULE[min(eta.poll_attempts - 1, len(POLL_BACKOFF_SCHEDULE) - 1)]
            eta.next_poll_at = timezone.now() + dt.timedelta(seconds=delay)
        eta.save(update_fields=["poll_attempts", "poll_stalled", "next_poll_at", "updated_at"])
        audit.record(module="einvoice", action="poll_invoice", entity_type="ETAInvoice",
                     entity_id=eta.invoice_number, actor=actor, after={"status": eta.status})
        return eta
    if outcome == "valid":
        eta.status = ETAStatus.VALID
        eta.validated_at = eta.validated_at or timezone.now()
        eta.poll_attempts = 0
        eta.poll_stalled = False
        eta.next_poll_at = None
        eta.save(update_fields=["status", "validated_at", "poll_attempts", "poll_stalled",
                                "next_poll_at", "updated_at"])
        bus.publish(events.EINVOICE_VALIDATED, {"invoice": eta.invoice_number, "uuid": eta.uuid})
    else:
        eta.status = ETAStatus.REJECTED
        eta.error_text = f"ETA returned {outcome}"
        eta.poll_attempts = 0
        eta.poll_stalled = False
        eta.next_poll_at = None
        eta.save(update_fields=["status", "error_text", "poll_attempts", "poll_stalled",
                                "next_poll_at", "updated_at"])
        bus.publish(events.EINVOICE_REJECTED, {"invoice": eta.invoice_number})
    audit.record(module="einvoice", action="poll_invoice", entity_type="ETAInvoice",
                 entity_id=eta.invoice_number, actor=actor, after={"status": eta.status})
    return eta


def due_polls():
    """Submitted e-invoices the beat sweep should (re-)poll now: backoff elapsed, not stalled."""
    return ETAInvoice.objects.filter(status=ETAStatus.SUBMITTED, poll_stalled=False).filter(
        Q(next_poll_at__isnull=True) | Q(next_poll_at__lte=timezone.now())
    )
