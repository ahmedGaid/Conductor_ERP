"""Campaign ROI rollup + ticket SLA escalation (exactly once)."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest
from django.utils import timezone

from erp.crm.domain.models import TicketPriority, TicketStatus
from erp.crm.errors import AlreadyEscalatedError, NotBreachedError
from erp.crm.services import (
    OppLineInput,
    campaign_metrics,
    create_campaign,
    create_opportunity,
    create_ticket,
    escalate_ticket,
    lose_opportunity,
    resolve_ticket,
    run_escalations,
    win_opportunity,
)

from .factories import make_customer, make_item

pytestmark = pytest.mark.django_db


def _breach(ticket):
    """Force a ticket past its SLA due time."""
    ticket.sla_due_at = timezone.now() - dt.timedelta(hours=1)
    ticket.save(update_fields=["sla_due_at"])
    ticket.refresh_from_db()
    return ticket


# --- Campaign ROI ----------------------------------------------------------

def test_campaign_rolls_up_won_value_vs_cost():
    make_customer("ACME")
    make_item("WIDGET")
    camp = create_campaign(code="C1", name="Spring", channel="email", cost_minor=5_000_00)

    # Two opportunities on the campaign: one won (10,000), one open (3,000).
    won = create_opportunity(name="Big deal", customer_code="ACME", campaign_code="C1",
                             lines=[OppLineInput("WIDGET", Decimal("100"), 100_00)])
    create_opportunity(name="Maybe", customer_code="ACME", campaign_code="C1",
                       lines=[OppLineInput("WIDGET", Decimal("30"), 100_00)])
    # An opportunity NOT on the campaign — must not count.
    create_opportunity(name="Other", customer_code="ACME", campaign_code="",
                       lines=[OppLineInput("WIDGET", Decimal("50"), 100_00)])
    win_opportunity(won, create_sales_order=False)

    m = campaign_metrics(camp)
    assert m.opportunity_count == 2
    assert m.won_count == 1
    assert m.won_value_minor == 10_000_00
    assert m.open_pipeline_minor == 3_000_00
    assert m.roi_minor == 10_000_00 - 5_000_00
    assert m.is_profitable is True


def test_campaign_unprofitable_when_cost_exceeds_won():
    camp = create_campaign(code="C2", name="Flop", cost_minor=8_000_00)
    m = campaign_metrics(camp)
    assert m.won_value_minor == 0
    assert m.roi_minor == -8_000_00
    assert m.is_profitable is False


def test_lost_opportunity_excluded_from_pipeline():
    make_customer("ACME")
    make_item("WIDGET")
    camp = create_campaign(code="C3", name="Camp", cost_minor=0)
    opp = create_opportunity(name="Deal", customer_code="ACME", campaign_code="C3",
                             lines=[OppLineInput("WIDGET", Decimal("10"), 100_00)])
    lose_opportunity(opp, reason="no budget")
    m = campaign_metrics(camp)
    assert m.open_pipeline_minor == 0
    assert m.won_value_minor == 0


# --- Ticket escalation -----------------------------------------------------

def test_breached_ticket_escalates_once_and_bumps_priority():
    ticket = create_ticket(subject="Down", priority=TicketPriority.MEDIUM)
    _breach(ticket)
    assert ticket.is_breached is True

    escalate_ticket(ticket)
    ticket.refresh_from_db()
    assert ticket.priority == TicketPriority.HIGH   # bumped one level
    assert ticket.is_escalated is True

    # Re-escalating the same ticket is rejected (exactly once).
    with pytest.raises(AlreadyEscalatedError):
        escalate_ticket(ticket)


def test_run_escalations_sweeps_breached_only_once():
    ok = create_ticket(subject="Fine", priority=TicketPriority.LOW)          # not breached
    breached = create_ticket(subject="Late", priority=TicketPriority.HIGH)
    _breach(breached)

    first = run_escalations()
    assert [t.number for t in first] == [breached.number]
    breached.refresh_from_db()
    assert breached.priority == TicketPriority.URGENT

    # Second sweep finds nothing new (already escalated; the other isn't breached).
    assert run_escalations() == []
    ok.refresh_from_db()
    assert ok.is_escalated is False


def test_non_breached_ticket_cannot_escalate():
    ticket = create_ticket(subject="On time", priority=TicketPriority.LOW)
    with pytest.raises(NotBreachedError):
        escalate_ticket(ticket)


def test_resolved_ticket_not_escalated_by_sweep():
    ticket = create_ticket(subject="Solved", priority=TicketPriority.HIGH)
    _breach(ticket)
    resolve_ticket(ticket)  # resolved ⇒ no longer open
    assert run_escalations() == []
    ticket.refresh_from_db()
    assert ticket.status == TicketStatus.RESOLVED
    assert ticket.is_escalated is False
