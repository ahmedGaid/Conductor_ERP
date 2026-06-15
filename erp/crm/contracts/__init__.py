"""Public contract for the CRM module — pipeline + support services and event names.

Other modules react to CRM events on the bus (e.g. a won opportunity creating a sales order is
handled inside CRM via the sales contract). External callers use these helpers by business key.
"""
from __future__ import annotations

from ..events import (
    LEAD_CONVERTED,
    OPPORTUNITY_LOST,
    OPPORTUNITY_WON,
    TICKET_OPENED,
    TICKET_RESOLVED,
)
from ..services.leads import convert_lead, create_lead, set_lead_status
from ..services.pipeline import (
    OppLineInput,
    advance_stage,
    create_opportunity,
    lose_opportunity,
    win_opportunity,
)
from ..services.support import (
    create_ticket,
    log_activity,
    resolve_ticket,
    start_ticket,
)

__all__ = [
    "create_lead",
    "set_lead_status",
    "convert_lead",
    "OppLineInput",
    "create_opportunity",
    "advance_stage",
    "win_opportunity",
    "lose_opportunity",
    "create_ticket",
    "start_ticket",
    "resolve_ticket",
    "log_activity",
    "LEAD_CONVERTED",
    "OPPORTUNITY_WON",
    "OPPORTUNITY_LOST",
    "TICKET_OPENED",
    "TICKET_RESOLVED",
]
