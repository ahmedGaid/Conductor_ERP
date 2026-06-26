"""Opportunity (pipeline) lifecycle — the CRM ↔ Sales bridge.

qualifying → proposal → negotiation → won | lost. Winning an opportunity can hand it off to Sales:
through the **sales public contract** (`erp.sales.contracts.place_order`, by customer *code* + line
inputs — no sales ORM crosses the boundary) it creates a draft sales order and records its number.
Every transition is atomic and guarded.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.utils import timezone

from erp.audit import services as audit
from erp.core.events import bus
from erp.sales import contracts as sales

from .. import events
from ..domain.models import (
    OPEN_STAGES,
    Lead,
    OppStage,
    Opportunity,
    OpportunityLine,
)
from ..errors import (
    EmptyOpportunityError,
    InvalidTransitionError,
    UnknownCustomerError,
)


@dataclass
class OppLineInput:
    item_sku: str
    quantity: Decimal
    unit_price_minor: int
    description: str = ""


def _round_minor(amount: Decimal) -> int:
    return int(amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _next_number() -> str:
    year = timezone.now().year
    prefix = f"OPP-{year}-"
    last = (
        Opportunity.objects.filter(number__startswith=prefix)
        .order_by("-number")
        .values_list("number", flat=True)
        .first()
    )
    seq = (int(last.rsplit("-", 1)[1]) + 1) if last else 1
    return f"{prefix}{seq:06d}"


@transaction.atomic
def create_opportunity(
    *, name: str, lines: list[OppLineInput] | None = None, lead: Lead | None = None,
    customer_code: str = "", warehouse_code: str = "", currency: str = "EGP",
    probability: int = 10, expected_close=None, notes: str = "", campaign_code: str = "", actor=None,
) -> Opportunity:
    opp = Opportunity.objects.create(
        number=_next_number(), name=name, lead=lead, customer_code=customer_code,
        warehouse_code=warehouse_code, campaign_code=campaign_code, currency=currency,
        probability=probability, expected_close=expected_close, notes=notes, stage=OppStage.QUALIFYING,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
        branch=actor.branch if getattr(actor, "is_authenticated", False) else None,
        department=actor.department if getattr(actor, "is_authenticated", False) else None,
        team=actor.team if getattr(actor, "is_authenticated", False) else None,
    )
    subtotal = 0
    for i, ln in enumerate(lines or [], start=1):
        total = _round_minor(Decimal(ln.quantity) * Decimal(ln.unit_price_minor))
        OpportunityLine.objects.create(
            opportunity=opp, line_no=i, item_sku=ln.item_sku, description=ln.description,
            quantity=Decimal(ln.quantity), unit_price_minor=ln.unit_price_minor,
            line_total_minor=total,
        )
        subtotal += total
    opp.amount_minor = subtotal
    opp.save(update_fields=["amount_minor"])
    audit.record(module="crm", action="create_opportunity", entity_type="Opportunity",
                 entity_id=opp.number, actor=actor)
    return opp


@transaction.atomic
def update_opportunity(opp: Opportunity, *, name: str | None = None, notes: str | None = None,
                       actor=None) -> Opportunity:
    """Edit an opportunity's free-text metadata (its title / notes). Stage-agnostic — these are
    labels, not lifecycle, so they stay editable whatever the stage. Only the fields passed are
    touched; everything else is left as-is."""
    changed: dict[str, str] = {}
    if name is not None and name != opp.name:
        opp.name = name
        changed["name"] = name
    if notes is not None and notes != opp.notes:
        opp.notes = notes
        changed["notes"] = notes
    if changed:
        opp.save(update_fields=[*changed.keys(), "updated_at"])
        audit.record(module="crm", action="update_opportunity", entity_type="Opportunity",
                     entity_id=opp.number, actor=actor, after=changed)
    return opp


@transaction.atomic
def advance_stage(opp: Opportunity, stage: str, actor=None) -> Opportunity:
    """Move an open opportunity to another **open** stage (won/lost go through their own services)."""
    if opp.stage not in OPEN_STAGES:
        raise InvalidTransitionError(data={"opportunity": opp.number, "stage": opp.stage})
    if stage not in OPEN_STAGES:
        raise InvalidTransitionError(data={"opportunity": opp.number, "to": stage})
    opp.stage = stage
    opp.save(update_fields=["stage", "updated_at"])
    audit.record(module="crm", action="advance_stage", entity_type="Opportunity",
                 entity_id=opp.number, actor=actor, after={"stage": stage})
    return opp


@transaction.atomic
def win_opportunity(opp: Opportunity, *, create_sales_order: bool = True, actor=None) -> Opportunity:
    """Mark an opportunity won; optionally hand it to Sales as a draft order via the contract."""
    if opp.stage not in OPEN_STAGES:
        raise InvalidTransitionError(data={"opportunity": opp.number, "stage": opp.stage})

    if create_sales_order:
        lines = list(opp.lines.all().order_by("line_no"))
        if not lines:
            raise EmptyOpportunityError(data={"opportunity": opp.number})
        if sales.find_customer(opp.customer_code) is None:
            raise UnknownCustomerError(data={"opportunity": opp.number, "customer": opp.customer_code})
        order = sales.place_order(
            customer_code=opp.customer_code,
            warehouse_code=opp.warehouse_code or "MAIN",
            lines=[
                sales.OrderLineInput(
                    item_sku=ln.item_sku, quantity=Decimal(ln.quantity),
                    unit_price_minor=ln.unit_price_minor, description=ln.description,
                )
                for ln in lines
            ],
            currency=opp.currency,
            notes=f"From opportunity {opp.number}",
            actor=actor,
        )
        opp.sales_order_number = order.number

    opp.stage = OppStage.WON
    opp.probability = 100
    opp.closed_at = timezone.now()
    opp.save(update_fields=["stage", "probability", "closed_at", "sales_order_number", "updated_at"])
    audit.record(module="crm", action="win_opportunity", entity_type="Opportunity",
                 entity_id=opp.number, actor=actor,
                 after={"sales_order": opp.sales_order_number or None})
    bus.publish(events.OPPORTUNITY_WON,
                {"opportunity": opp.number, "amount": opp.amount_minor,
                 "sales_order": opp.sales_order_number or None})
    return opp


@transaction.atomic
def lose_opportunity(opp: Opportunity, *, reason: str = "", actor=None) -> Opportunity:
    if opp.stage not in OPEN_STAGES:
        raise InvalidTransitionError(data={"opportunity": opp.number, "stage": opp.stage})
    opp.stage = OppStage.LOST
    opp.probability = 0
    opp.closed_at = timezone.now()
    if reason:
        opp.notes = (opp.notes + f"\nLost: {reason}").strip()
    opp.save(update_fields=["stage", "probability", "closed_at", "notes", "updated_at"])
    audit.record(module="crm", action="lose_opportunity", entity_type="Opportunity",
                 entity_id=opp.number, actor=actor, after={"reason": reason})
    bus.publish(events.OPPORTUNITY_LOST, {"opportunity": opp.number, "reason": reason})
    return opp
