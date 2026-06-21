"""Lead lifecycle: capture → qualify → convert into an opportunity.

A lead is the raw top of the funnel. Converting it qualifies a real pipeline opportunity and stamps
the lead ``converted`` (once only). Conversion is atomic.
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from erp.audit import services as audit
from erp.core.events import bus

from .. import events
from ..domain.models import Lead, LeadStatus
from ..errors import InvalidTransitionError, LeadAlreadyConvertedError


def _next_code() -> str:
    year = timezone.now().year
    prefix = f"LEAD-{year}-"
    last = (
        Lead.objects.filter(code__startswith=prefix)
        .order_by("-code")
        .values_list("code", flat=True)
        .first()
    )
    seq = (int(last.rsplit("-", 1)[1]) + 1) if last else 1
    return f"{prefix}{seq:06d}"


@transaction.atomic
def create_lead(
    *, name: str, company: str = "", email: str = "", phone: str = "",
    source: str = "other", owner: str = "", notes: str = "", campaign_code: str = "", actor=None,
) -> Lead:
    lead = Lead.objects.create(
        code=_next_code(), name=name, company=company, email=email, phone=phone,
        source=source, owner=owner, notes=notes, campaign_code=campaign_code, status=LeadStatus.NEW,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
        branch=actor.branch if getattr(actor, "is_authenticated", False) else None,
        department=actor.department if getattr(actor, "is_authenticated", False) else None,
        team=actor.team if getattr(actor, "is_authenticated", False) else None,
    )
    audit.record(module="crm", action="create_lead", entity_type="Lead",
                 entity_id=lead.code, actor=actor)
    return lead


@transaction.atomic
def set_lead_status(lead: Lead, status: str, actor=None) -> Lead:
    if lead.status == LeadStatus.CONVERTED:
        raise LeadAlreadyConvertedError(data={"lead": lead.code})
    if status not in {LeadStatus.NEW, LeadStatus.CONTACTED, LeadStatus.QUALIFIED, LeadStatus.UNQUALIFIED}:
        raise InvalidTransitionError(data={"lead": lead.code, "status": status})
    lead.status = status
    lead.save(update_fields=["status", "updated_at"])
    audit.record(module="crm", action="set_lead_status", entity_type="Lead",
                 entity_id=lead.code, actor=actor, after={"status": status})
    return lead


@transaction.atomic
def convert_lead(
    lead: Lead, *, opportunity_name: str = "", customer_code: str = "", actor=None,
):
    """Convert a lead into a pipeline opportunity. Marks the lead converted (once only)."""
    if lead.status == LeadStatus.CONVERTED:
        raise LeadAlreadyConvertedError(data={"lead": lead.code})

    # Local import avoids a circular import (pipeline imports nothing from leads).
    from .pipeline import create_opportunity

    opp = create_opportunity(
        name=opportunity_name or f"{lead.company or lead.name}",
        lead=lead, customer_code=customer_code, lines=[], actor=actor,
    )
    lead.status = LeadStatus.CONVERTED
    lead.save(update_fields=["status", "updated_at"])
    audit.record(module="crm", action="convert_lead", entity_type="Lead",
                 entity_id=lead.code, actor=actor, after={"opportunity": opp.number})
    bus.publish(events.LEAD_CONVERTED, {"lead": lead.code, "opportunity": opp.number})
    return opp
