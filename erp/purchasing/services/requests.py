"""Purchase request (requisition) lifecycle — pre-order document with an approval gate.

draft → submit → (auto-approve at/below threshold, else awaits) approve/reject → convert → PO.

Conversion reuses the existing PO service (`create_order`) so no purchase order logic is duplicated;
the request only carries the resulting order number. Money is integer minor units; quantities Decimal.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.utils import timezone

from erp.audit import services as audit
from erp.core.events import bus
from erp.identity import access

from .. import events
from ..domain.models import PRStatus, PurchaseRequest, PurchaseRequestLine, Supplier
from ..errors import (
    ApprovalLimitExceededError,
    EmptyRequestError,
    RequestAlreadyConvertedError,
    RequestInvalidTransitionError,
)
from .orders import POLineInput, create_order

# Requests at or below this value auto-approve on submit; above it, they need explicit approval.
APPROVAL_THRESHOLD_MINOR = 1_000_000  # 10,000.00 EGP


@dataclass
class RequestLineInput:
    item_sku: str
    quantity: Decimal
    unit_cost_minor: int
    description: str = ""


def _round_minor(amount: Decimal) -> int:
    return int(amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _next_number() -> str:
    year = timezone.now().year
    prefix = f"PR-{year}-"
    last = (
        PurchaseRequest.objects.filter(number__startswith=prefix)
        .order_by("-number")
        .values_list("number", flat=True)
        .first()
    )
    seq = (int(last.rsplit("-", 1)[1]) + 1) if last else 1
    return f"{prefix}{seq:06d}"


def _require(req: PurchaseRequest, status: str) -> None:
    if req.status != status:
        raise RequestInvalidTransitionError(
            data={"request": req.number, "status": req.status, "expected": status}
        )


def requires_approval(subtotal_minor: int) -> bool:
    return subtotal_minor > APPROVAL_THRESHOLD_MINOR


@transaction.atomic
def create_request(
    *, supplier: Supplier, warehouse_code: str, lines: list[RequestLineInput],
    request_date=None, currency: str = "EGP", notes: str = "", actor=None,
) -> PurchaseRequest:
    if not lines:
        raise EmptyRequestError()

    req = PurchaseRequest.objects.create(
        number=_next_number(), supplier=supplier, request_date=request_date or dt.date.today(),
        warehouse_code=warehouse_code, currency=currency, notes=notes, status=PRStatus.DRAFT,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
        branch=actor.branch if getattr(actor, "is_authenticated", False) else None,
    )
    subtotal = 0
    for i, ln in enumerate(lines, start=1):
        total = _round_minor(Decimal(ln.quantity) * Decimal(ln.unit_cost_minor))
        PurchaseRequestLine.objects.create(
            request=req, line_no=i, item_sku=ln.item_sku, description=ln.description,
            quantity=Decimal(ln.quantity), unit_cost_minor=ln.unit_cost_minor,
            line_total_minor=total,
        )
        subtotal += total
    req.subtotal_minor = subtotal
    req.save(update_fields=["subtotal_minor"])
    return req


@transaction.atomic
def submit_request(req: PurchaseRequest, actor=None) -> PurchaseRequest:
    """Submit for approval. At/below the threshold this auto-approves; above it, it awaits a manager."""
    _require(req, PRStatus.DRAFT)
    if requires_approval(req.subtotal_minor):
        req.status = PRStatus.SUBMITTED
        req.save(update_fields=["status", "updated_at"])
        bus.publish(events.PR_SUBMITTED, {"request": req.number})
    else:
        req.status = PRStatus.APPROVED
        req.approved_at = timezone.now()
        req.save(update_fields=["status", "approved_at", "updated_at"])
        bus.publish(events.PR_APPROVED, {"request": req.number, "auto": True})
    audit.record(module="purchasing", action="submit_request", entity_type="PurchaseRequest",
                 entity_id=req.number, actor=actor, after={"status": req.status})
    return req


@transaction.atomic
def approve_request(req: PurchaseRequest, actor=None) -> PurchaseRequest:
    _require(req, PRStatus.SUBMITTED)
    if getattr(actor, "is_authenticated", False) and not access.can_approve(
        actor, "purchase_request", req.subtotal_minor
    ):
        raise ApprovalLimitExceededError(
            data={"document": req.number, "amount": req.subtotal_minor,
                  "limit": access.approval_limit(actor, "purchase_request")}
        )
    req.status = PRStatus.APPROVED
    req.approved_at = timezone.now()
    req.approved_by = actor if getattr(actor, "is_authenticated", False) else None
    req.save(update_fields=["status", "approved_at", "approved_by", "updated_at"])
    audit.record(module="purchasing", action="approve_request", entity_type="PurchaseRequest",
                 entity_id=req.number, actor=actor)
    bus.publish(events.PR_APPROVED, {"request": req.number, "auto": False})
    return req


@transaction.atomic
def reject_request(req: PurchaseRequest, reason: str = "", actor=None) -> PurchaseRequest:
    if req.status not in (PRStatus.SUBMITTED, PRStatus.APPROVED):
        raise RequestInvalidTransitionError(
            data={"request": req.number, "status": req.status, "expected": "submitted|approved"}
        )
    req.status = PRStatus.REJECTED
    req.rejected_reason = reason
    req.save(update_fields=["status", "rejected_reason", "updated_at"])
    audit.record(module="purchasing", action="reject_request", entity_type="PurchaseRequest",
                 entity_id=req.number, actor=actor, after={"reason": reason})
    bus.publish(events.PR_REJECTED, {"request": req.number})
    return req


@transaction.atomic
def convert_request(req: PurchaseRequest, actor=None):
    """Turn an approved request into a purchase order via the existing PO service."""
    if req.converted_order_number:
        raise RequestAlreadyConvertedError(data={"request": req.number})
    _require(req, PRStatus.APPROVED)
    order = create_order(
        supplier=req.supplier, warehouse_code=req.warehouse_code, currency=req.currency,
        notes=f"From request {req.number}",
        lines=[
            POLineInput(item_sku=l.item_sku, quantity=l.quantity,
                        unit_cost_minor=l.unit_cost_minor, description=l.description)
            for l in req.lines.all().order_by("line_no")
        ],
        actor=actor,
    )
    req.status = PRStatus.CONVERTED
    req.converted_order_number = order.number
    req.save(update_fields=["status", "converted_order_number", "updated_at"])
    audit.record(module="purchasing", action="convert_request", entity_type="PurchaseRequest",
                 entity_id=req.number, actor=actor, after={"order": order.number})
    bus.publish(events.PR_CONVERTED, {"request": req.number, "order": order.number})
    return order
