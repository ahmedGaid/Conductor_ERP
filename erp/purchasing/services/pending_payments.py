"""Draftable supplier payments — mirrors erp.sales.services.pending_payments exactly. See that
module's docstring."""
from __future__ import annotations

import datetime as dt

from django.db import transaction
from django.utils import timezone

from ..domain.models import PendingPayment, PendingPaymentStatus, PurchaseOrder
from ..errors import PendingPaymentStateError
from .orders import pay_order


def create_pending_payment(
    *, order: PurchaseOrder | None, party_code: str, amount_minor: int, date: dt.date,
    method: str = "", source: str = "import", batch_ref: str = "", actor=None,
) -> PendingPayment:
    return PendingPayment.objects.create(
        order=order, party_code=party_code, amount_minor=amount_minor, date=date,
        method=method, source=source, batch_ref=batch_ref,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
        branch=actor.branch if getattr(actor, "is_authenticated", False) else None,
        department=actor.department if getattr(actor, "is_authenticated", False) else None,
        team=actor.team if getattr(actor, "is_authenticated", False) else None,
    )


@transaction.atomic
def apply_pending_payment(pending: PendingPayment, actor=None) -> PendingPayment:
    if pending.status != PendingPaymentStatus.PENDING:
        raise PendingPaymentStateError(f"pending payment is {pending.status!r}, not pending")
    if pending.order_id is None:
        raise PendingPaymentStateError("pending payment has no matched order — match it first")
    pay_order(pending.order, pending.amount_minor, actor=actor)
    pending.status = PendingPaymentStatus.APPLIED
    pending.applied_by = actor if getattr(actor, "is_authenticated", False) else None
    pending.applied_at = timezone.now()
    pending.save(update_fields=["status", "applied_by", "applied_at", "updated_at"])
    return pending


def discard_pending_payment(pending: PendingPayment, actor=None) -> PendingPayment:
    if pending.status != PendingPaymentStatus.PENDING:
        raise PendingPaymentStateError(f"pending payment is {pending.status!r}, not pending")
    pending.status = PendingPaymentStatus.DISCARDED
    pending.save(update_fields=["status", "updated_at"])
    return pending


def match_pending_payment(pending: PendingPayment, order: PurchaseOrder, actor=None) -> PendingPayment:
    if pending.status != PendingPaymentStatus.PENDING:
        raise PendingPaymentStateError(f"pending payment is {pending.status!r}, not pending")
    pending.order = order
    pending.save(update_fields=["order", "updated_at"])
    return pending
