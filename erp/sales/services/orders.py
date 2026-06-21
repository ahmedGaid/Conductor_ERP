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
from ..domain.models import Customer, OrderStatus, SalesOrder, SalesOrderLine
from ..errors import (
    ApprovalLimitExceededError,
    ApprovalRequiredError,
    CreditLimitExceededError,
    EmptyOrderError,
    ExcessiveDeliveryError,
    ExcessiveReturnError,
    InvalidDiscountError,
    InvalidTransitionError,
    NothingToReturnError,
    OverpaymentError,
    UnknownItemError,
    UnknownTaxCodeError,
)
from ..repositories import customers as customer_repo

AR_ACCOUNT = "1100"
REVENUE_ACCOUNT = "4000"
CASH_ACCOUNT = "1000"
SALES_RETURNS_ACCOUNT = "4090"

# Orders above this net value need manager approval before they can be confirmed.
APPROVAL_THRESHOLD_MINOR = 1_000_000  # 10,000.00 EGP


def requires_approval(subtotal_minor: int) -> bool:
    return subtotal_minor > APPROVAL_THRESHOLD_MINOR


@dataclass
class OrderLineInput:
    item_sku: str
    quantity: Decimal
    unit_price_minor: int
    description: str = ""
    discount_minor: int = 0


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
    order_date=None, currency: str = "EGP", notes: str = "", tax_code: str = "", actor=None,
) -> SalesOrder:
    if not lines:
        raise EmptyOrderError()
    for ln in lines:
        info = inventory.find_item(ln.item_sku)
        if info is None or info.type != "stock" or not info.is_active:
            raise UnknownItemError(data={"sku": ln.item_sku})
    if tax_code and find_tax_code(tax_code) is None:
        raise UnknownTaxCodeError(data={"tax_code": tax_code})

    order = SalesOrder.objects.create(
        number=_next_number(), customer=customer, order_date=order_date or dt.date.today(),
        warehouse_code=warehouse_code, currency=currency, notes=notes, tax_code=tax_code,
        status=OrderStatus.DRAFT,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
        branch=actor.branch if getattr(actor, "is_authenticated", False) else None,
        department=actor.department if getattr(actor, "is_authenticated", False) else None,
        team=actor.team if getattr(actor, "is_authenticated", False) else None,
    )
    subtotal = 0
    for i, ln in enumerate(lines, start=1):
        gross = _round_minor(Decimal(ln.quantity) * Decimal(ln.unit_price_minor))
        discount = int(ln.discount_minor or 0)
        if discount < 0 or discount > gross:
            raise InvalidDiscountError(data={"line": i, "gross": gross, "discount": discount})
        total = gross - discount
        SalesOrderLine.objects.create(
            order=order, line_no=i, item_sku=ln.item_sku, description=ln.description,
            quantity=Decimal(ln.quantity), unit_price_minor=ln.unit_price_minor,
            discount_minor=discount, line_total_minor=total,
        )
        subtotal += total
    order.subtotal_minor = subtotal
    order.save(update_fields=["subtotal_minor"])
    return order


@transaction.atomic
def approve_order(order: SalesOrder, actor=None) -> SalesOrder:
    """Manager sign-off for an above-threshold order (required before confirm).

    An interactive approver may only sign off up to their role's approval limit for sales orders
    (Increment 6). A system/no-actor call (actor=None) and superuser/System Admin are unrestricted.
    """
    _require(order, OrderStatus.DRAFT)
    if getattr(actor, "is_authenticated", False) and not access.can_approve(
        actor, "sales_order", order.subtotal_minor
    ):
        raise ApprovalLimitExceededError(
            data={"document": order.number, "amount": order.subtotal_minor,
                  "limit": access.approval_limit(actor, "sales_order")}
        )
    order.approved = True
    order.approved_at = timezone.now()
    order.approved_by = actor if getattr(actor, "is_authenticated", False) else None
    order.save(update_fields=["approved", "approved_at", "approved_by", "updated_at"])
    audit.record(module="sales", action="approve_order", entity_type="SalesOrder",
                 entity_id=order.number, actor=actor)
    bus.publish(events.ORDER_APPROVED, {"order": order.number})
    return order


@transaction.atomic
def confirm_order(order: SalesOrder, actor=None) -> SalesOrder:
    _require(order, OrderStatus.DRAFT)
    if requires_approval(order.subtotal_minor) and not order.approved:
        raise ApprovalRequiredError(
            data={"order": order.number, "total": order.subtotal_minor,
                  "threshold": APPROVAL_THRESHOLD_MINOR}
        )
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
def deliver_order(order: SalesOrder, delivered: dict[int, Decimal] | None = None, actor=None) -> SalesOrder:
    """Deliver (issue) stock. Full by default; pass ``{line_no: qty}`` for a partial shipment.

    Supports multiple shipments: callable while CONFIRMED or PARTIALLY_DELIVERED, accumulating each
    line's ``delivered_qty`` until every line is fully delivered (then the order becomes DELIVERED).
    """
    if order.status not in (OrderStatus.CONFIRMED, OrderStatus.PARTIALLY_DELIVERED):
        raise InvalidTransitionError(
            data={"order": order.number, "status": order.status,
                  "expected": "confirmed|partially_delivered"}
        )
    moved = False
    for line in order.lines.all().order_by("line_no"):
        remaining = Decimal(line.quantity) - Decimal(line.delivered_qty)
        qty = Decimal(delivered[line.line_no]) if delivered and line.line_no in delivered else remaining
        if qty <= 0:
            continue
        if qty > remaining:
            raise ExcessiveDeliveryError(
                data={"line": line.line_no, "remaining": str(remaining), "requested": str(qty)}
            )
        # Issues stock + posts Dr COGS / Cr Inventory at weighted-average cost.
        inventory.issue(
            line.item_sku, order.warehouse_code, qty,
            reference=order.number, memo=f"Delivery {order.number}", actor=actor,
        )
        line.delivered_qty = Decimal(line.delivered_qty) + qty
        line.save(update_fields=["delivered_qty"])
        moved = True
    if not moved:
        raise ExcessiveDeliveryError(data={"order": order.number, "reason": "nothing to deliver"})

    fully = all(Decimal(l.delivered_qty) >= Decimal(l.quantity) for l in order.lines.all())
    order.status = OrderStatus.DELIVERED if fully else OrderStatus.PARTIALLY_DELIVERED
    order.save(update_fields=["status", "updated_at"])
    audit.record(module="sales", action="deliver_order", entity_type="SalesOrder",
                 entity_id=order.number, actor=actor, after={"status": order.status})
    bus.publish(events.ORDER_DELIVERED, {"order": order.number, "status": order.status})
    return order


@transaction.atomic
def return_order(order: SalesOrder, returned: dict[int, Decimal] | None = None, actor=None) -> SalesOrder:
    """Customer return / credit note on an invoiced (or paid) order.

    Brings stock back via the inventory contract (Dr Inventory / Cr COGS) and posts the financial
    leg Dr Sales Returns / Cr AR for the selling value of the returned lines — reducing the
    receivable. Returns default to the full outstanding delivered quantity per line.
    """
    if order.status not in (OrderStatus.INVOICED, OrderStatus.PAID):
        raise InvalidTransitionError(
            data={"order": order.number, "status": order.status, "expected": "invoiced|paid"}
        )
    sell_value = 0
    for line in order.lines.all().order_by("line_no"):
        returnable = Decimal(line.delivered_qty) - Decimal(line.returned_qty)
        qty = Decimal(returned[line.line_no]) if returned and line.line_no in returned else returnable
        if qty <= 0:
            continue
        if qty > returnable:
            raise ExcessiveReturnError(
                data={"line": line.line_no, "returnable": str(returnable), "requested": str(qty)}
            )
        inventory.return_in(
            line.item_sku, order.warehouse_code, qty,
            reference=order.number, memo=f"Return {order.number}", actor=actor,
        )
        line.returned_qty = Decimal(line.returned_qty) + qty
        line.save(update_fields=["returned_qty"])
        # Credit the net (post-discount) line value, prorated by the returned quantity.
        sell_value += _round_minor(Decimal(line.line_total_minor) * qty / Decimal(line.quantity))

    if sell_value <= 0:
        raise NothingToReturnError(data={"order": order.number})

    # Reverse VAT proportionally to the returned net value, if the order was taxed.
    vat_value = compute_tax(sell_value, order.tax_code) if order.tax_code else 0
    # Dr Sales Returns (net) [/ Dr VAT Payable (vat)] / Cr AR (net + vat).
    lines = [LineInput(account_code=SALES_RETURNS_ACCOUNT, debit=sell_value)]
    if vat_value > 0:
        info = find_tax_code(order.tax_code)
        lines.append(LineInput(account_code=info.output_account_code, debit=vat_value))
    lines.append(LineInput(account_code=AR_ACCOUNT, credit=sell_value + vat_value))
    entry = post_journal(
        JournalInput(
            date=dt.date.today(), source="sales", reference=order.number,
            memo=f"Credit note {order.number} — {order.customer.code}",
            lines=lines,
        ),
        actor=actor,
    )
    order.returned_minor += sell_value
    order.invoiced_minor -= sell_value + vat_value
    order.credit_note_number = entry.number
    if all(Decimal(l.returned_qty) >= Decimal(l.delivered_qty) for l in order.lines.all()):
        order.status = OrderStatus.RETURNED
    order.save(update_fields=["returned_minor", "invoiced_minor", "credit_note_number",
                              "status", "updated_at"])
    audit.record(module="sales", action="return_order", entity_type="SalesOrder",
                 entity_id=order.number, actor=actor, after={"credit_note": entry.number,
                                                             "value": sell_value})
    bus.publish(events.ORDER_RETURNED, {"order": order.number, "credit_note": entry.number})
    return order


@transaction.atomic
def invoice_order(order: SalesOrder, actor=None) -> SalesOrder:
    _require(order, OrderStatus.DELIVERED)
    net = order.subtotal_minor
    vat = compute_tax(net, order.tax_code) if order.tax_code else 0
    gross = net + vat
    # Admin-configured ceiling (opt-in): blocked only if the actor's role has an 'invoice' limit
    # below this amount; uncapped roles are unrestricted.
    if getattr(actor, "is_authenticated", False) and not access.within_limit(actor, "invoice", gross):
        raise ApprovalLimitExceededError(
            data={"document": order.number, "amount": gross,
                  "limit": access.approval_limit(actor, "invoice")}
        )
    # Dr AR (gross) / Cr Revenue (net) [/ Cr VAT Payable (vat)].
    lines = [
        LineInput(account_code=AR_ACCOUNT, debit=gross),
        LineInput(account_code=REVENUE_ACCOUNT, credit=net),
    ]
    if vat > 0:
        info = find_tax_code(order.tax_code)
        lines.append(LineInput(account_code=info.output_account_code, credit=vat))
    entry = post_journal(
        JournalInput(
            date=dt.date.today(), source="sales", reference=order.number,
            memo=f"Invoice {order.number} — {order.customer.code}",
            lines=lines,
        ),
        actor=actor,
    )
    order.status = OrderStatus.INVOICED
    order.tax_minor = vat
    order.invoiced_minor = gross
    order.invoice_number = entry.number
    order.save(update_fields=["status", "tax_minor", "invoiced_minor", "invoice_number", "updated_at"])
    audit.record(module="sales", action="invoice_order", entity_type="SalesOrder",
                 entity_id=order.number, actor=actor, after={"invoice": entry.number, "vat": vat})
    # Enriched payload so subscribers (e-invoicing) can build a record without reaching into sales.
    bus.publish(events.ORDER_INVOICED, {
        "order": order.number, "invoice": entry.number,
        "customer_code": order.customer.code, "customer_name": order.customer.name,
        "date": dt.date.today().isoformat(), "currency": order.currency,
        "tax_code": order.tax_code, "net_minor": net, "tax_minor": vat, "total_minor": gross,
    })
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
    if getattr(actor, "is_authenticated", False) and not access.within_limit(actor, "payment", amount_minor):
        raise ApprovalLimitExceededError(
            data={"document": order.number, "amount": amount_minor,
                  "limit": access.approval_limit(actor, "payment")}
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
