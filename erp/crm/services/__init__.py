"""CRM services — campaigns, leads, pipeline (opportunities), and support (tickets + activities)."""
from __future__ import annotations

from .campaigns import (
    CampaignMetrics,
    campaign_metrics,
    create_campaign,
    set_campaign_status,
)
from .leads import convert_lead, create_lead, set_lead_status
from .pipeline import (
    OppLineInput,
    advance_stage,
    create_opportunity,
    lose_opportunity,
    update_opportunity,
    win_opportunity,
)
from .support import (
    close_ticket,
    complete_activity,
    create_ticket,
    escalate_ticket,
    log_activity,
    resolve_ticket,
    run_escalations,
    start_ticket,
)

__all__ = [
    "CampaignMetrics",
    "campaign_metrics",
    "create_campaign",
    "set_campaign_status",
    "create_lead",
    "set_lead_status",
    "convert_lead",
    "OppLineInput",
    "create_opportunity",
    "advance_stage",
    "update_opportunity",
    "win_opportunity",
    "lose_opportunity",
    "create_ticket",
    "start_ticket",
    "resolve_ticket",
    "close_ticket",
    "escalate_ticket",
    "run_escalations",
    "log_activity",
    "complete_activity",
]
