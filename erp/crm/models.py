"""Django discovers models here; definitions live in the domain layer (strict module layout)."""
from __future__ import annotations

from .domain.models import (  # noqa: F401
    Activity,
    ActivityType,
    Campaign,
    CampaignChannel,
    CampaignStatus,
    Lead,
    LeadSource,
    LeadStatus,
    OppStage,
    Opportunity,
    OpportunityLine,
    RelatedType,
    Ticket,
    TicketPriority,
    TicketStatus,
)

__all__ = [
    "Activity",
    "ActivityType",
    "Campaign",
    "CampaignChannel",
    "CampaignStatus",
    "Lead",
    "LeadSource",
    "LeadStatus",
    "OppStage",
    "Opportunity",
    "OpportunityLine",
    "RelatedType",
    "Ticket",
    "TicketPriority",
    "TicketStatus",
]
