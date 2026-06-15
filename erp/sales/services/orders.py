"""Sales order lifecycle — the cross-module orchestration.

draft → confirm (credit check) → deliver (issue stock via inventory contract → COGS posts) →
invoice (Dr AR / Cr Revenue via accounting contract) → payment (Dr Cash / Cr AR). Every transition
is atomic and guarded; the GL stays balanced and the Inventory account keeps matching stock value.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.utils import timezone

from erp.accounting.contracts import JournalInput, LineInput, post_journal
from erp.audit import services as audit
from erp.core.events import bus
from erp.inventory import contracts as inventory

from .. import events
from ..domain.models import Customer, OrderStatus, SalesOrder, SalesOrderLine
from ..errors import (
    CreditLimitExceededError,
    EmptyOrderError,
    InvalidTransitionError,
    OverpaymentError,
    UnknownItemError,
)
from ..repositories import customers as customer_repo

AR_ACCOUNT = "1100"
REVENUE_ACCOUNT = "4000"
CASH_ACCOUNT = "1000"


@dataclass
class OrderLineInput:
    item_sku: str
    quantity: Decimal
    unit_price_minor: int
    description: str = ""


def _round_minor(amount: Decimal) -> int:
    return int(amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _next_number() -> str:
    year = timezone.now().year
    prefix = f"SO-{year}-"
    last = (
        SalesOrder.objects.filter(number__startswith=prefix)
        .order_by("-number")
        .values_list("number", flat=True)
        .first()
    )
    seq = (int(last.rsplit("-", 1)[1]) + 1) if last else 1
    return f"{prefix}{seq:06d}"


def _require(order: SalesOrder, status: str) -> None:
    if order.status != status:
        raise InvalidTransitionError(
            data={"order": order.number, "status": order.status, "expected": status}
        )


@transaction.atomic
def create_order(
    *, customer: Customer, warehouse_code: str, lines: list[OrderLineInput],
    order_date=None, currency: str = "EGP", notes: str = "", actor=None,
) -> SalesOrder:
    if not lines:
        raise EmptyOrderError()
    for ln in lines:
        info = inventory.find_item(ln.item_sku)
        if info is None or info.type != "stock" or not info.is_active:
            raise UnknownItemError(data={"sku": ln.item_sku})

    order = SalesOrder.objects.create(
        number=_next_number(), customer=customer, order_date=order_date or dt.date.today(),
        warehouse_code=warehouse_code, currency=currency, notes=notes, status=OrderStatus.DRAFT,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
    )
    subtotal = 0
    for i, ln in enumerate(lines, start=1):
        total = _round_minor(Decimal(ln.quantity) * Decimal(ln.unit_price_minor))
        SalesOrderLine.objects.create(
            order=order, line_no=i, item_sku=ln.item_sku, description=ln.description,
            quantity=Decimal(ln.quantity), unit_price_minor=ln.unit_price_minor,
            line_total_minor=total,
        )
        subtotal += total
    order.subtotal_minor = subtotal
    order.save(update_fields=["subtotal_minor"])
    return order


@transaction.atomic
def confirm_order(order: SalesOrder, actor=None) -> SalesOrder:
    _require(order, OrderStatus.DRAFT)
    limit = order.customer.credit_limit_minor
    if limit > 0:
        projected = customer_repo.outstanding_minor(order.customer) + order.subtotal_minor
        if projected > limit:
            raise CreditLimitExceededError(
                data={"customer": order.customer.code, "limit": limit, "projected": projected}
            )
    order.status = OrderStatus.CONFIRMED
    order.save(update_fields=["status", "updated_at"])
    audit.record(module="sales", action="confirm_order", entity_type="SalesOrder",
                 entity_id=order.number, actor=actor)
    bus.publish(events.ORDER_CONFIRMED, {"order": order.number, "customer": order.customer.code})
    return order


@transaction.atomic
def deliver_order(order: SalesOrder, actor=None) -> SalesOrder:
    _require(order, OrderStatus.CONFIRMED)
    for line in order.lines.all().order_by("line_no"):
        # Issues stock + posts Dr COGS / Cr Inventory at weighted-average cost.
        inventory.issue(
            line.item_sku, order.warehouse_code, line.quantity,
            reference=order.number, memo=f"Delivery {order.number}", actor=actor,
        )
    order.status = OrderStatus.DELIVERED
    order.save(update_fields=["status", "updated_at"])
    audit.record(module="sales", action="deliver_order", entity_type="SalesOrder",
                 entity_id=order.number, actor=actor)
    bus.publish(events.ORDER_DELIVERED, {"order": order.number})
    return order


@transaction.atomic
def invoice_order(order: SalesOrder, actor=None) -> SalesOrder:
    _require(order, OrderStatus.DELIVERED)
    entry = post_journal(
        JournalInput(
            date=dt.date.today(), source="sales", reference=order.number,
            memo=f"Invoice {order.number} — {order.customer.code}",
            lines=[
                LineInput(account_code=AR_ACCOUNT, debit=order.subtotal_minor),
                LineInput(account_code=REVENUE_ACCOUNT, credit=order.subtotal_minor),
            ],
        ),
        actor=actor,
    )
    order.status = OrderStatus.INVOICED
    order.invoiced_minor = order.subtotal_minor
    order.invoice_number = entry.number
    order.save(update_fields=["status", "invoiced_minor", "invoice_number", "updated_at"])
    audit.record(module="sales", action="invoice_order", entity_type="SalesOrder",
                 entity_id=order.number, actor=actor, after={"invoice": entry.number})
    bus.publish(events.ORDER_INVOICED, {"order": order.number, "invoice": entry.number})
    return order


@transaction.atomic
def receive_payment(order: SalesOrder, amount_minor: int, actor=None) -> SalesOrder:
    if order.status not in (OrderStatus.INVOICED,):
        raise InvalidTransitionError(
            data={"order": order.number, "status": order.status, "expected": "invoiced"}
        )
    if amount_minor <= 0:
        raise OverpaymentError("payment must be positive")
    if amount_minor > order.outstanding_minor:
        raise OverpaymentError(
            data={"outstanding": order.outstanding_minor, "amount": amount_minor}
        )
    post_journal(
        JournalInput(
            date=dt.date.today(), source="sales", reference=order.number,
            memo=f"Payment {order.number} — {order.customer.code}",
            lines=[
                LineInput(account_code=CASH_ACCOUNT, debit=amount_minor),
                LineInput(account_code=AR_ACCOUNT, credit=amount_minor),
            ],
        ),
        actor=actor,
    )
    order.paid_minor += amount_minor
    if order.paid_minor >= order.invoiced_minor:
        order.status = OrderStatus.PAID
    order.save(update_fields=["paid_minor", "status", "updated_at"])
    audit.record(module="sales", action="receive_payment", entity_type="SalesOrder",
                 entity_id=order.number, actor=actor, after={"amount": amount_minor})
    bus.publish(events.PAYMENT_RECEIVED, {"order": order.number, "amount": amount_minor})
    return order
