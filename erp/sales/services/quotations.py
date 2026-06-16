"""Sales quotation lifecycle — pre-order document with an approval gate.

draft → submit → (auto-approve at/below threshold, else awaits) approve/reject → convert → SalesOrder.

Conversion reuses the existing order service (`create_order`) so no order logic is duplicated; the
quotation only carries the resulting order number. Money is integer minor units; quantities Decimal.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.utils import timezone

from erp.audit import services as audit
from erp.core.events import bus

from .. import events
from ..domain.models import Customer, Quotation, QuotationLine, QuotationStatus
from ..errors import (
    EmptyQuotationError,
    QuotationAlreadyConvertedError,
    QuotationInvalidTransitionError,
)
from .orders import OrderLineInput, create_order

# Quotations at or below this value auto-approve on submit; above it, they need explicit approval.
APPROVAL_THRESHOLD_MINOR = 1_000_000  # 10,000.00 EGP


@dataclass
class QuoteLineInput:
    item_sku: str
    quantity: Decimal
    unit_price_minor: int
    description: str = ""


def _round_minor(amount: Decimal) -> int:
    return int(amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _next_number() -> str:
    year = timezone.now().year
    prefix = f"QUO-{year}-"
    last = (
        Quotation.objects.filter(number__startswith=prefix)
        .order_by("-number")
        .values_list("number", flat=True)
        .first()
    )
    seq = (int(last.rsplit("-", 1)[1]) + 1) if last else 1
    return f"{prefix}{seq:06d}"


def _require(quote: Quotation, status: str) -> None:
    if quote.status != status:
        raise QuotationInvalidTransitionError(
            data={"quotation": quote.number, "status": quote.status, "expected": status}
        )


def requires_approval(subtotal_minor: int) -> bool:
    return subtotal_minor > APPROVAL_THRESHOLD_MINOR


@transaction.atomic
def create_quotation(
    *, customer: Customer, warehouse_code: str, lines: list[QuoteLineInput],
    quote_date=None, currency: str = "EGP", notes: str = "", actor=None,
) -> Quotation:
    if not lines:
        raise EmptyQuotationError()

    quote = Quotation.objects.create(
        number=_next_number(), customer=customer, quote_date=quote_date or dt.date.today(),
        warehouse_code=warehouse_code, currency=currency, notes=notes,
        status=QuotationStatus.DRAFT,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
    )
    subtotal = 0
    for i, ln in enumerate(lines, start=1):
        total = _round_minor(Decimal(ln.quantity) * Decimal(ln.unit_price_minor))
        QuotationLine.objects.create(
            quotation=quote, line_no=i, item_sku=ln.item_sku, description=ln.description,
            quantity=Decimal(ln.quantity), unit_price_minor=ln.unit_price_minor,
            line_total_minor=total,
        )
        subtotal += total
    quote.subtotal_minor = subtotal
    quote.save(update_fields=["subtotal_minor"])
    return quote


@transaction.atomic
def submit_quotation(quote: Quotation, actor=None) -> Quotation:
    """Submit for approval. At/below the threshold this auto-approves; above it, it awaits a manager."""
    _require(quote, QuotationStatus.DRAFT)
    if requires_approval(quote.subtotal_minor):
        quote.status = QuotationStatus.SUBMITTED
        quote.save(update_fields=["status", "updated_at"])
        bus.publish(events.QUOTATION_SUBMITTED, {"quotation": quote.number})
    else:
        quote.status = QuotationStatus.APPROVED
        quote.approved_at = timezone.now()
        quote.save(update_fields=["status", "approved_at", "updated_at"])
        bus.publish(events.QUOTATION_APPROVED, {"quotation": quote.number, "auto": True})
    audit.record(module="sales", action="submit_quotation", entity_type="Quotation",
                 entity_id=quote.number, actor=actor, after={"status": quote.status})
    return quote


@transaction.atomic
def approve_quotation(quote: Quotation, actor=None) -> Quotation:
    _require(quote, QuotationStatus.SUBMITTED)
    quote.status = QuotationStatus.APPROVED
    quote.approved_at = timezone.now()
    quote.approved_by = actor if getattr(actor, "is_authenticated", False) else None
    quote.save(update_fields=["status", "approved_at", "approved_by", "updated_at"])
    audit.record(module="sales", action="approve_quotation", entity_type="Quotation",
                 entity_id=quote.number, actor=actor)
    bus.publish(events.QUOTATION_APPROVED, {"quotation": quote.number, "auto": False})
    return quote


@transaction.atomic
def reject_quotation(quote: Quotation, reason: str = "", actor=None) -> Quotation:
    if quote.status not in (QuotationStatus.SUBMITTED, QuotationStatus.APPROVED):
        raise QuotationInvalidTransitionError(
            data={"quotation": quote.number, "status": quote.status, "expected": "submitted|approved"}
        )
    quote.status = QuotationStatus.REJECTED
    quote.rejected_reason = reason
    quote.save(update_fields=["status", "rejected_reason", "updated_at"])
    audit.record(module="sales", action="reject_quotation", entity_type="Quotation",
                 entity_id=quote.number, actor=actor, after={"reason": reason})
    bus.publish(events.QUOTATION_REJECTED, {"quotation": quote.number})
    return quote


@transaction.atomic
def convert_quotation(quote: Quotation, actor=None):
    """Turn an approved quotation into a sales order via the existing order service."""
    if quote.converted_order_number:
        raise QuotationAlreadyConvertedError(data={"quotation": quote.number})
    _require(quote, QuotationStatus.APPROVED)
    order = create_order(
        customer=quote.customer, warehouse_code=quote.warehouse_code, currency=quote.currency,
        notes=f"From quotation {quote.number}",
        lines=[
            OrderLineInput(item_sku=l.item_sku, quantity=l.quantity,
                           unit_price_minor=l.unit_price_minor, description=l.description)
            for l in quote.lines.all().order_by("line_no")
        ],
        actor=actor,
    )
    quote.status = QuotationStatus.CONVERTED
    quote.converted_order_number = order.number
    quote.save(update_fields=["status", "converted_order_number", "updated_at"])
    audit.record(module="sales", action="convert_quotation", entity_type="Quotation",
                 entity_id=quote.number, actor=actor, after={"order": order.number})
    bus.publish(events.QUOTATION_CONVERTED, {"quotation": quote.number, "order": order.number})
    return order
