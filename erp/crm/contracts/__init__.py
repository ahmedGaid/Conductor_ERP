"""Public contract for the CRM module — pipeline + support services and event names.

Other modules react to CRM events on the bus (e.g. a won opportunity creating a sales order is
handled inside CRM via the sales contract). External callers use these helpers by business key.
"""
from __future__ import annotations

from django.db.models import Q

from erp.identity.scoping import scope_queryset

from ..domain.models import Opportunity
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

# --- scoped read helper for the AI assistant (ai-workspace session 11) --------------------------
# Mirrors the sales contract's read helpers: plain dicts, narrowed to what ``actor`` may see via
# ``scope_queryset`` — the same enforcement the CRM pipeline endpoints use.

def _scoped_opportunities(actor):
    return scope_queryset(actor, Opportunity.objects.all(), "crm.opportunity.view")


def find_opportunities(actor, *, query: str = "", limit: int = 8) -> list[dict]:
    """Find opportunities by number, name or customer code — scoped to the actor."""
    q = (query or "").strip()
    qs = _scoped_opportunities(actor)
    if q:
        qs = qs.filter(
            Q(number__icontains=q) | Q(name__icontains=q) | Q(customer_code__icontains=q)
        )
    return [
        {"number": o.number, "name": o.name, "stage": o.stage,
         "customer_code": o.customer_code, "amount_minor": o.amount_minor,
         "expected_close": str(o.expected_close) if o.expected_close else None}
        for o in qs.order_by("-created_at")[: max(1, min(limit, 20))]
    ]


__all__ = [
    "create_lead",
    "set_lead_status",
    "convert_lead",
    "OppLineInput",
    "find_opportunities",
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
