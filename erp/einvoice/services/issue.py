"""E-invoice lifecycle services.

record_invoice (idempotent, from a posted sales invoice) → submit (prepare, assigns a reference) →
poll (ask for the outcome). Every transition is atomic. The submission itself goes through the ETA
adapter, so the only side effect is the (currently simulated) external call + the persisted status.

While ``eta_adapter.SIMULATED`` is True nothing reaches the Tax Authority, so ``poll_invoice``
cannot reach ``valid`` — a prepared invoice rests at ``submitted``.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from erp.audit import services as audit
from erp.core.events import bus

from .. import events
from ..domain.models import ETAInvoice, ETAStatus
from ..errors import InvalidEInvoiceTransitionError
from . import eta_adapter


@dataclass
class EInvoiceInput:
    invoice_number: str
    issue_date: dt.date
    order_number: str = ""
    customer_code: str = ""
    customer_name: str = ""
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
    result = eta_adapter.submit(_document(eta))
    if not result.accepted:
        eta.status = ETAStatus.REJECTED
        eta.error_text = result.error
        eta.save(update_fields=["status", "error_text", "updated_at"])
        bus.publish(events.EINVOICE_REJECTED, {"invoice": eta.invoice_number})
        return eta
    eta.uuid = result.uuid
    eta.status = ETAStatus.SUBMITTED
    eta.submitted_at = eta.submitted_at or timezone.now()
    eta.error_text = ""
    eta.save(update_fields=["uuid", "status", "submitted_at", "error_text", "updated_at"])
    audit.record(module="einvoice", action="submit_invoice", entity_type="ETAInvoice",
                 entity_id=eta.invoice_number, actor=actor, after={"uuid": eta.uuid})
    bus.publish(events.EINVOICE_SUBMITTED, {"invoice": eta.invoice_number, "uuid": eta.uuid})
    return eta


@transaction.atomic
def poll_invoice(eta: ETAInvoice, actor=None) -> ETAInvoice:
    """Poll ETA for a submitted e-invoice's validation result."""
    if eta.status not in (ETAStatus.SUBMITTED, ETAStatus.VALID):
        raise InvalidEInvoiceTransitionError(
            data={"invoice": eta.invoice_number, "status": eta.status, "expected": "submitted"}
        )
    outcome = eta_adapter.query(eta.uuid)
    if outcome == "pending":
        # The adapter has no Tax-Authority verdict to report (it is simulated). Leave the record
        # where it is rather than inventing a "valid" that no authority granted — see
        # eta_adapter.SIMULATED and the claims-discipline decision (2026-07-20).
        audit.record(module="einvoice", action="poll_invoice", entity_type="ETAInvoice",
                     entity_id=eta.invoice_number, actor=actor, after={"status": eta.status})
        return eta
    if outcome == "valid":
        eta.status = ETAStatus.VALID
        eta.validated_at = eta.validated_at or timezone.now()
        eta.save(update_fields=["status", "validated_at", "updated_at"])
        bus.publish(events.EINVOICE_VALIDATED, {"invoice": eta.invoice_number, "uuid": eta.uuid})
    else:
        eta.status = ETAStatus.REJECTED
        eta.error_text = f"ETA returned {outcome}"
        eta.save(update_fields=["status", "error_text", "updated_at"])
        bus.publish(events.EINVOICE_REJECTED, {"invoice": eta.invoice_number})
    audit.record(module="einvoice", action="poll_invoice", entity_type="ETAInvoice",
                 entity_id=eta.invoice_number, actor=actor, after={"status": eta.status})
    return eta
