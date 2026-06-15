"""CRM services — leads, pipeline (opportunities), and support (tickets + activities)."""
from __future__ import annotations

from .leads import convert_lead, create_lead, set_lead_status
from .pipeline import (
    OppLineInput,
    advance_stage,
    create_opportunity,
    lose_opportunity,
    win_opportunity,
)
from .support import (
    close_ticket,
    complete_activity,
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
    "close_ticket",
    "log_activity",
    "complete_activity",
]
