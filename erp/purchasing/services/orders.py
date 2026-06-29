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

from erp.accounting.contracts import (
    JournalInput,
    LineInput,
    compute_tax,
    find_tax_code,
    post_journal,
)
from erp.audit import services as audit
from erp.core.events import bus
from erp.identity import access
from erp.inventory import contracts as inventory

from .. import events
from ..domain.models import POStatus, PurchaseOrder, PurchaseOrderLine, Supplier
from ..errors import (
    ApprovalLimitExceededError,
    ApprovalRequiredError,
    EmptyOrderError,
    ExcessiveReceiptError,
    ExcessiveReturnError,
    InvalidTransitionError,
    NothingToReturnError,
    OverpaymentError,
    ThreeWayMatchError,
    UnknownItemError,
    UnknownTaxCodeError,
)

GRNI_ACCOUNT = "2150"
AP_ACCOUNT = "2000"
CASH_ACCOUNT = "1000"

# Orders above this value need manager approval before they can be confirmed.
APPROVAL_THRESHOLD_MINOR = 1_000_000  # 10,000.00 EGP


def requires_approval(subtotal_minor: int) -> bool:
    return subtotal_minor > APPROVAL_THRESHOLD_MINOR


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


def _snapshot(order: PurchaseOrder) -> dict:
    """Point-in-time view of the PO, stored on the audit trail (``after``) at every transition so each
    workflow stage can be replayed exactly as it was when the actor reached it."""
    return {
        "number": order.number,
        "status": order.status,
        "supplier_code": order.supplier.code,
        "supplier_name": order.supplier.name,
        "warehouse_code": order.warehouse_code,
        "currency": order.currency,
        "order_date": order.order_date.isoformat(),
        "subtotal_minor": order.subtotal_minor,
        "tax_code": order.tax_code,
        "tax_minor": order.tax_minor,
        "received_minor": order.received_minor,
        "billed_minor": order.billed_minor,
        "paid_minor": order.paid_minor,
        "returned_minor": order.returned_minor,
        "outstanding_minor": order.billed_minor - order.paid_minor,
        "bill_number": order.bill_number,
        "debit_note_number": order.debit_note_number,
        "lines": [
            {
                "line_no": ln.line_no,
                "item_sku": ln.item_sku,
                "description": ln.description,
                "quantity": str(ln.quantity),
                "received_qty": str(ln.received_qty),
                "returned_qty": str(ln.returned_qty),
                "unit_cost_minor": ln.unit_cost_minor,
                "line_total_minor": ln.line_total_minor,
            }
            for ln in order.lines.all().order_by("line_no")
        ],
    }


@transaction.atomic
def create_order(
    *, supplier: Supplier, warehouse_code: str, lines: list[POLineInput],
    order_date=None, currency: str = "EGP", notes: str = "", tax_code: str = "", actor=None,
) -> PurchaseOrder:
    if not lines:
        raise EmptyOrderError()
    for ln in lines:
        info = inventory.find_item(ln.item_sku)
        if info is None or info.type != "stock" or not info.is_active:
            raise UnknownItemError(data={"sku": ln.item_sku})
    if tax_code and find_tax_code(tax_code) is None:
        raise UnknownTaxCodeError(data={"tax_code": tax_code})

    order = PurchaseOrder.objects.create(
        number=_next_number(), supplier=supplier, order_date=order_date or dt.date.today(),
        warehouse_code=warehouse_code, currency=currency, notes=notes, tax_code=tax_code,
        status=POStatus.DRAFT,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
        branch=actor.branch if getattr(actor, "is_authenticated", False) else None,
        department=actor.department if getattr(actor, "is_authenticated", False) else None,
        team=actor.team if getattr(actor, "is_authenticated", False) else None,
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
    audit.record(module="purchasing", action="create_order", entity_type="PurchaseOrder",
                 entity_id=order.number, actor=actor, after=_snapshot(order))
    return order


@transaction.atomic
def approve_order(order: PurchaseOrder, actor=None) -> PurchaseOrder:
    """Manager sign-off for an above-threshold order (required before confirm).

    An interactive approver may only sign off up to their role's approval limit for purchase orders
    (Increment 6). A system/no-actor call (actor=None) and superuser/System Admin are unrestricted.
    """
    _require(order, POStatus.DRAFT)
    if getattr(actor, "is_authenticated", False) and not access.can_approve(
        actor, "purchase_order", order.subtotal_minor
    ):
        raise ApprovalLimitExceededError(
            data={"document": order.number, "amount": order.subtotal_minor,
                  "limit": access.approval_limit(actor, "purchase_order")}
        )
    order.approved = True
    order.approved_at = timezone.now()
    order.approved_by = actor if getattr(actor, "is_authenticated", False) else None
    order.save(update_fields=["approved", "approved_at", "approved_by", "updated_at"])
    audit.record(module="purchasing", action="approve_order", entity_type="PurchaseOrder",
                 entity_id=order.number, actor=actor, after=_snapshot(order))
    bus.publish(events.PO_APPROVED, {"order": order.number})
    return order


@transaction.atomic
def confirm_order(order: PurchaseOrder, actor=None) -> PurchaseOrder:
    _require(order, POStatus.DRAFT)
    if requires_approval(order.subtotal_minor) and not order.approved:
        raise ApprovalRequiredError(
            data={"order": order.number, "total": order.subtotal_minor,
                  "threshold": APPROVAL_THRESHOLD_MINOR}
        )
    order.status = POStatus.CONFIRMED
    order.save(update_fields=["status", "updated_at"])
    audit.record(module="purchasing", action="confirm_order", entity_type="PurchaseOrder",
                 entity_id=order.number, actor=actor, after=_snapshot(order))
    bus.publish(events.PO_CONFIRMED, {"order": order.number, "supplier": order.supplier.code})
    return order


@transaction.atomic
def cancel_order(order: PurchaseOrder, actor=None) -> PurchaseOrder:
    """Cancel a purchase order that has not yet received stock or posted to the GL.

    Allowed only for the states the org's cancellation policy permits (draft/confirmed); past
    receipt, cancellation is never offered — use a return / debit note instead. A pure status flip,
    so there is nothing to reverse."""
    if not access.order_cancellable(order.status):
        raise InvalidTransitionError(
            data={"order": order.number, "status": order.status, "expected": "draft|confirmed"}
        )
    order.status = POStatus.CANCELLED
    order.save(update_fields=["status", "updated_at"])
    audit.record(module="purchasing", action="cancel_order", entity_type="PurchaseOrder",
                 entity_id=order.number, actor=actor, after=_snapshot(order))
    return order


@transaction.atomic
def receive_order(order: PurchaseOrder, received: dict[int, Decimal] | None = None, actor=None) -> PurchaseOrder:
    """Goods receipt (GRN). Full by default; pass ``{line_no: qty}`` for a partial receipt.

    Supports multiple receipts: callable while CONFIRMED or PARTIALLY_RECEIVED, accumulating each
    line's ``received_qty`` until every line is fully received (then the order becomes RECEIVED — the
    state the 3-way match requires before billing). A partial receipt leaves it PARTIALLY_RECEIVED.
    """
    if order.status not in (POStatus.CONFIRMED, POStatus.PARTIALLY_RECEIVED):
        raise InvalidTransitionError(
            data={"order": order.number, "status": order.status,
                  "expected": "confirmed|partially_received"}
        )
    moved = False
    for line in order.lines.all().order_by("line_no"):
        remaining = Decimal(line.quantity) - Decimal(line.received_qty)
        qty = Decimal(received[line.line_no]) if received and line.line_no in received else remaining
        if qty <= 0:
            continue
        if qty > remaining:
            raise ExcessiveReceiptError(
                data={"line": line.line_no, "remaining": str(remaining), "requested": str(qty)}
            )
        inventory.receive(
            line.item_sku, order.warehouse_code, qty, line.unit_cost_minor,
            reference=order.number, memo=f"GRN {order.number}", actor=actor,
        )
        line.received_qty = Decimal(line.received_qty) + qty
        line.save(update_fields=["received_qty"])
        moved = True
    if not moved:
        raise ExcessiveReceiptError(data={"order": order.number, "reason": "nothing to receive"})

    lines = list(order.lines.all())
    received_total = sum(_round_minor(Decimal(l.received_qty) * Decimal(l.unit_cost_minor)) for l in lines)
    fully = all(Decimal(l.received_qty) >= Decimal(l.quantity) for l in lines)
    order.received_minor = received_total
    order.status = POStatus.RECEIVED if fully else POStatus.PARTIALLY_RECEIVED
    order.save(update_fields=["received_minor", "status", "updated_at"])
    audit.record(module="purchasing", action="receive_order", entity_type="PurchaseOrder",
                 entity_id=order.number, actor=actor, after=_snapshot(order))
    bus.publish(events.PO_RECEIVED, {"order": order.number, "value": received_total,
                                     "status": order.status})
    return order


@transaction.atomic
def bill_order(order: PurchaseOrder, actor=None) -> PurchaseOrder:
    """Vendor bill. 3-way match (ordered == received per line), then clear GRNI into AP."""
    if order.status not in (POStatus.RECEIVED, POStatus.PARTIALLY_RECEIVED):
        raise InvalidTransitionError(
            data={"order": order.number, "status": order.status,
                  "expected": "received|partially_received"}
        )
    for line in order.lines.all():
        if Decimal(line.received_qty) != Decimal(line.quantity):
            raise ThreeWayMatchError(
                data={"line": line.line_no, "ordered": str(line.quantity),
                      "received": str(line.received_qty)}
            )
    net = order.received_minor
    vat = compute_tax(net, order.tax_code) if order.tax_code else 0
    gross = net + vat
    # Admin-configured ceiling (opt-in): blocked only if the actor's role has an 'invoice' limit
    # below this bill; uncapped roles are unrestricted.
    if getattr(actor, "is_authenticated", False) and not access.within_limit(actor, "invoice", gross):
        raise ApprovalLimitExceededError(
            data={"document": order.number, "amount": gross,
                  "limit": access.approval_limit(actor, "invoice")}
        )
    # Clear GRNI into AP, booking recoverable input VAT: Dr GRNI (net) [/ Dr VAT Input (vat)] / Cr AP (gross).
    lines = [LineInput(account_code=GRNI_ACCOUNT, debit=net)]
    if vat > 0:
        info = find_tax_code(order.tax_code)
        lines.append(LineInput(account_code=info.input_account_code, debit=vat))
    lines.append(LineInput(account_code=AP_ACCOUNT, credit=gross))
    entry = post_journal(
        JournalInput(
            date=dt.date.today(), source="purchasing", reference=order.number,
            party_type="supplier", party_code=order.supplier.code,
            memo=f"Bill {order.number} — {order.supplier.code}",
            lines=lines,
        ),
        actor=actor,
    )
    order.status = POStatus.BILLED
    order.tax_minor = vat
    order.billed_minor = gross
    order.bill_number = entry.number
    order.save(update_fields=["status", "tax_minor", "billed_minor", "bill_number", "updated_at"])
    audit.record(module="purchasing", action="bill_order", entity_type="PurchaseOrder",
                 entity_id=order.number, actor=actor, after=_snapshot(order))
    bus.publish(events.PO_BILLED, {"order": order.number, "bill": entry.number})
    return order


@transaction.atomic
def pay_order(order: PurchaseOrder, amount_minor: int, actor=None) -> PurchaseOrder:
    _require(order, POStatus.BILLED)
    if amount_minor <= 0 or amount_minor > order.outstanding_minor:
        raise OverpaymentError(
            data={"outstanding": order.outstanding_minor, "amount": amount_minor}
        )
    if getattr(actor, "is_authenticated", False) and not access.within_limit(actor, "payment", amount_minor):
        raise ApprovalLimitExceededError(
            data={"document": order.number, "amount": amount_minor,
                  "limit": access.approval_limit(actor, "payment")}
        )
    post_journal(
        JournalInput(
            date=dt.date.today(), source="purchasing", reference=order.number,
            party_type="supplier", party_code=order.supplier.code,
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
                 entity_id=order.number, actor=actor, after=_snapshot(order))
    bus.publish(events.PO_PAID, {"order": order.number, "amount": amount_minor})
    return order


@transaction.atomic
def return_order(order: PurchaseOrder, returned: dict[int, Decimal] | None = None, actor=None) -> PurchaseOrder:
    """Supplier return / debit note on a billed (or paid) order.

    Ships stock back out via the inventory contract (Dr GRNI / Cr Inventory) and posts the financial
    leg Dr AP / Cr GRNI for the cost value — so GRNI nets to zero and the payable is reduced (net of
    the original receipt+bill+return is nil). Returns default to the full received-not-returned qty.
    """
    if order.status not in (POStatus.BILLED, POStatus.PAID):
        raise InvalidTransitionError(
            data={"order": order.number, "status": order.status, "expected": "billed|paid"}
        )
    cost_value = 0
    for line in order.lines.all().order_by("line_no"):
        returnable = Decimal(line.received_qty) - Decimal(line.returned_qty)
        qty = Decimal(returned[line.line_no]) if returned and line.line_no in returned else returnable
        if qty <= 0:
            continue
        if qty > returnable:
            raise ExcessiveReturnError(
                data={"line": line.line_no, "returnable": str(returnable), "requested": str(qty)}
            )
        movement = inventory.return_out(
            line.item_sku, order.warehouse_code, qty,
            reference=order.number, memo=f"Return {order.number}", actor=actor,
        )
        line.returned_qty = Decimal(line.returned_qty) + qty
        line.save(update_fields=["returned_qty"])
        cost_value += movement.value_minor

    if cost_value <= 0:
        raise NothingToReturnError(data={"order": order.number})

    # Reverse recoverable input VAT proportionally to the returned net cost, if the order was taxed.
    vat_value = compute_tax(cost_value, order.tax_code) if order.tax_code else 0
    # Dr AP (net + vat) / Cr GRNI (net) [/ Cr VAT Input (vat)].
    lines = [
        LineInput(account_code=AP_ACCOUNT, debit=cost_value + vat_value),
        LineInput(account_code=GRNI_ACCOUNT, credit=cost_value),
    ]
    if vat_value > 0:
        info = find_tax_code(order.tax_code)
        lines.append(LineInput(account_code=info.input_account_code, credit=vat_value))
    entry = post_journal(
        JournalInput(
            date=dt.date.today(), source="purchasing", reference=order.number,
            party_type="supplier", party_code=order.supplier.code,
            memo=f"Debit note {order.number} — {order.supplier.code}",
            lines=lines,
        ),
        actor=actor,
    )
    order.returned_minor += cost_value
    order.billed_minor -= cost_value + vat_value
    order.debit_note_number = entry.number
    if all(Decimal(l.returned_qty) >= Decimal(l.received_qty) for l in order.lines.all()):
        order.status = POStatus.RETURNED
    order.save(update_fields=["returned_minor", "billed_minor", "debit_note_number",
                              "status", "updated_at"])
    audit.record(module="purchasing", action="return_order", entity_type="PurchaseOrder",
                 entity_id=order.number, actor=actor, after=_snapshot(order))
    bus.publish(events.PO_RETURNED, {"order": order.number, "debit_note": entry.number})
    return order
