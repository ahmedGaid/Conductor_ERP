"""Marketing campaigns and their ROI.

A campaign is referenced by ``code`` from leads and opportunities. Its metrics roll up the linked
leads and opportunities — **won value** (sum of won-opportunity amounts) against the campaign
**cost** gives ROI. Money is integer minor units.
"""
from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.db.models import Sum

from erp.audit import services as audit

from ..domain.models import (
    Campaign,
    CampaignStatus,
    Lead,
    OppStage,
    Opportunity,
)
from ..errors import InvalidTransitionError


@transaction.atomic
def create_campaign(*, code: str, name: str, channel: str = "other", cost_minor: int = 0,
                    start_date=None, end_date=None, notes: str = "", actor=None) -> Campaign:
    campaign = Campaign.objects.create(
        code=code, name=name, channel=channel, cost_minor=cost_minor,
        start_date=start_date, end_date=end_date, notes=notes, status=CampaignStatus.DRAFT,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
        branch=actor.branch if getattr(actor, "is_authenticated", False) else None,
    )
    audit.record(module="crm", action="create_campaign", entity_type="Campaign",
                 entity_id=campaign.code, actor=actor)
    return campaign


@transaction.atomic
def set_campaign_status(campaign: Campaign, status: str, actor=None) -> Campaign:
    if status not in CampaignStatus.values:
        raise InvalidTransitionError(data={"campaign": campaign.code, "to": status})
    campaign.status = status
    campaign.save(update_fields=["status", "updated_at"])
    audit.record(module="crm", action="set_campaign_status", entity_type="Campaign",
                 entity_id=campaign.code, actor=actor, after={"status": status})
    return campaign


@dataclass
class CampaignMetrics:
    code: str
    name: str
    cost_minor: int
    lead_count: int
    opportunity_count: int
    won_count: int
    open_pipeline_minor: int   # amount of still-open opportunities
    won_value_minor: int       # amount of won opportunities
    roi_minor: int             # won_value − cost

    @property
    def is_profitable(self) -> bool:
        return self.roi_minor >= 0


def campaign_metrics(campaign: Campaign) -> CampaignMetrics:
    """Roll up leads + opportunities linked to the campaign into a won-value-vs-cost ROI."""
    lead_count = Lead.objects.filter(campaign_code=campaign.code).count()
    opps = Opportunity.objects.filter(campaign_code=campaign.code)
    opp_count = opps.count()
    won = opps.filter(stage=OppStage.WON)
    won_count = won.count()
    won_value = won.aggregate(s=Sum("amount_minor"))["s"] or 0
    open_pipeline = (
        opps.filter(stage__in=OppStage.values).exclude(stage__in=[OppStage.WON, OppStage.LOST])
        .aggregate(s=Sum("amount_minor"))["s"] or 0
    )
    return CampaignMetrics(
        code=campaign.code, name=campaign.name, cost_minor=campaign.cost_minor,
        lead_count=lead_count, opportunity_count=opp_count, won_count=won_count,
        open_pipeline_minor=open_pipeline, won_value_minor=won_value,
        roi_minor=won_value - campaign.cost_minor,
    )
