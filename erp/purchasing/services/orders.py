"""Purchase order lifecycle — procure-to-pay, closing the GRNI loop.

draft → confirm → receive (GRN: inventory.contracts.receive → Dr Inventory / Cr GRNI) →
bill (3-way match, then Dr GRNI / Cr AP — clearing the GRNI the receipt created) →
payment (Dr AP / Cr Cash). Every transition is atomic and guarded.
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
from ..domain.models import POStatus, PurchaseOrder, PurchaseOrderLine, Supplier
from ..errors import (
    EmptyOrderError,
    InvalidTransitionError,
    OverpaymentError,
    ThreeWayMatchError,
    UnknownItemError,
)

GRNI_ACCOUNT = "2150"
AP_ACCOUNT = "2000"
CASH_ACCOUNT = "1000"


@dataclass
class POLineInput:
    item_sku: str
    quantity: Decimal
    unit_cost_minor: int
    description: str = ""


def _round_minor(amount: Decimal) -> int:
    return int(amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _next_number() -> str:
    year = timezone.now().year
    prefix = f"PO-{year}-"
    last = (
        PurchaseOrder.objects.filter(number__startswith=prefix)
        .order_by("-number")
        .values_list("number", flat=True)
        .first()
    )
    seq = (int(last.rsplit("-", 1)[1]) + 1) if last else 1
    return f"{prefix}{seq:06d}"


def _require(order: PurchaseOrder, status: str) -> None:
    if order.status != status:
        raise InvalidTransitionError(
            data={"order": order.number, "status": order.status, "expected": status}
        )


@transaction.atomic
def create_order(
    *, supplier: Supplier, warehouse_code: str, lines: list[POLineInput],
    order_date=None, currency: str = "EGP", notes: str = "", actor=None,
) -> PurchaseOrder:
    if not lines:
        raise EmptyOrderError()
    for ln in lines:
        info = inventory.find_item(ln.item_sku)
        if info is None or info.type != "stock" or not info.is_active:
            raise UnknownItemError(data={"sku": ln.item_sku})

    order = PurchaseOrder.objects.create(
        number=_next_number(), supplier=supplier, order_date=order_date or dt.date.today(),
        warehouse_code=warehouse_code, currency=currency, notes=notes, status=POStatus.DRAFT,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
    )
    subtotal = 0
    for i, ln in enumerate(lines, start=1):
        total = _round_minor(Decimal(ln.quantity) * Decimal(ln.unit_cost_minor))
        PurchaseOrderLine.objects.create(
            order=order, line_no=i, item_sku=ln.item_sku, description=ln.description,
            quantity=Decimal(ln.quantity), unit_cost_minor=ln.unit_cost_minor,
            line_total_minor=total,
        )
        subtotal += total
    order.subtotal_minor = subtotal
    order.save(update_fields=["subtotal_minor"])
    return order


@transaction.atomic
def confirm_order(order: PurchaseOrder, actor=None) -> PurchaseOrder:
    _require(order, POStatus.DRAFT)
    order.status = POStatus.CONFIRMED
    order.save(update_fields=["status", "updated_at"])
    audit.record(module="purchasing", action="confirm_order", entity_type="PurchaseOrder",
                 entity_id=order.number, actor=actor)
    bus.publish(events.PO_CONFIRMED, {"order": order.number, "supplier": order.supplier.code})
    return order


@transaction.atomic
def receive_order(order: PurchaseOrder, received: dict[int, Decimal] | None = None, actor=None) -> PurchaseOrder:
    """Goods receipt. Defaults to the full ordered quantity; pass {line_no: qty} for a partial GRN."""
    _require(order, POStatus.CONFIRMED)
    received_total = 0
    for line in order.lines.all().order_by("line_no"):
        qty = Decimal(received[line.line_no]) if received and line.line_no in received else Decimal(line.quantity)
        if qty <= 0:
            continue
        inventory.receive(
            line.item_sku, order.warehouse_code, qty, line.unit_cost_minor,
            reference=order.number, memo=f"GRN {order.number}", actor=actor,
        )
        line.received_qty = qty
        line.save(update_fields=["received_qty"])
        received_total += _round_minor(qty * Decimal(line.unit_cost_minor))
    order.received_minor = received_total
    order.status = POStatus.RECEIVED
    order.save(update_fields=["received_minor", "status", "updated_at"])
    audit.record(module="purchasing", action="receive_order", entity_type="PurchaseOrder",
                 entity_id=order.number, actor=actor, after={"received": received_total})
    bus.publish(events.PO_RECEIVED, {"order": order.number, "value": received_total})
    return order


@transaction.atomic
def bill_order(order: PurchaseOrder, actor=None) -> PurchaseOrder:
    """Vendor bill. 3-way match (ordered == received per line), then clear GRNI into AP."""
    _require(order, POStatus.RECEIVED)
    for line in order.lines.all():
        if Decimal(line.received_qty) != Decimal(line.quantity):
            raise ThreeWayMatchError(
                data={"line": line.line_no, "ordered": str(line.quantity),
                      "received": str(line.received_qty)}
            )
    entry = post_journal(
        JournalInput(
            date=dt.date.today(), source="purchasing", reference=order.number,
            memo=f"Bill {order.number} — {order.supplier.code}",
            lines=[
                LineInput(account_code=GRNI_ACCOUNT, debit=order.received_minor),
                LineInput(account_code=AP_ACCOUNT, credit=order.received_minor),
            ],
        ),
        actor=actor,
    )
    order.status = POStatus.BILLED
    order.billed_minor = order.received_minor
    order.bill_number = entry.number
    order.save(update_fields=["status", "billed_minor", "bill_number", "updated_at"])
    audit.record(module="purchasing", action="bill_order", entity_type="PurchaseOrder",
                 entity_id=order.number, actor=actor, after={"bill": entry.number})
    bus.publish(events.PO_BILLED, {"order": order.number, "bill": entry.number})
    return order


@transaction.atomic
def pay_order(order: PurchaseOrder, amount_minor: int, actor=None) -> PurchaseOrder:
    _require(order, POStatus.BILLED)
    if amount_minor <= 0 or amount_minor > order.outstanding_minor:
        raise OverpaymentError(
            data={"outstanding": order.outstanding_minor, "amount": amount_minor}
        )
    post_journal(
        JournalInput(
            date=dt.date.today(), source="purchasing", reference=order.number,
            memo=f"Payment {order.number} — {order.supplier.code}",
            lines=[
                LineInput(account_code=AP_ACCOUNT, debit=amount_minor),
                LineInput(account_code=CASH_ACCOUNT, credit=amount_minor),
            ],
        ),
        actor=actor,
    )
    order.paid_minor += amount_minor
    if order.paid_minor >= order.billed_minor:
        order.status = POStatus.PAID
    order.save(update_fields=["paid_minor", "status", "updated_at"])
    audit.record(module="purchasing", action="pay_order", entity_type="PurchaseOrder",
                 entity_id=order.number, actor=actor, after={"amount": amount_minor})
    bus.publish(events.PO_PAID, {"order": order.number, "amount": amount_minor})
    return order
