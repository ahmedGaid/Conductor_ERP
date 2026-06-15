"""Support tickets (priority-driven SLA) and activities."""
from __future__ import annotations

import datetime as dt

import pytest
from django.utils import timezone

from erp.crm.domain.models import (
    ActivityType,
    RelatedType,
    TicketPriority,
    TicketStatus,
)
from erp.crm.errors import InvalidTransitionError
from erp.crm.services import (
    close_ticket,
    complete_activity,
    create_ticket,
    log_activity,
    resolve_ticket,
    start_ticket,
)

pytestmark = pytest.mark.django_db


def test_sla_due_is_computed_from_priority():
    urgent = create_ticket(subject="Down!", priority=TicketPriority.URGENT)
    low = create_ticket(subject="Typo", priority=TicketPriority.LOW)
    assert urgent.sla_due_at == urgent.opened_at + dt.timedelta(hours=4)
    assert low.sla_due_at == low.opened_at + dt.timedelta(hours=72)


def test_open_ticket_past_due_is_breached():
    ticket = create_ticket(subject="Late", priority=TicketPriority.URGENT)
    # Force the SLA into the past without resolving.
    ticket.sla_due_at = timezone.now() - dt.timedelta(hours=1)
    ticket.save(update_fields=["sla_due_at"])
    assert ticket.is_breached is True


def test_within_sla_and_resolved_are_not_breached():
    ticket = create_ticket(subject="On time", priority=TicketPriority.MEDIUM)
    assert ticket.is_breached is False  # plenty of time left
    start_ticket(ticket)
    resolve_ticket(ticket, resolution="Patched")
    assert ticket.status == TicketStatus.RESOLVED
    assert ticket.resolved_at is not None
    assert ticket.is_breached is False  # resolved tickets are never breaching


def test_ticket_lifecycle_guards():
    ticket = create_ticket(subject="Flow")
    with pytest.raises(InvalidTransitionError):
        close_ticket(ticket)  # can't close before resolving
    start_ticket(ticket)
    with pytest.raises(InvalidTransitionError):
        start_ticket(ticket)  # already in progress
    resolve_ticket(ticket)
    close_ticket(ticket)
    assert ticket.status == TicketStatus.CLOSED
    assert ticket.closed_at is not None


def test_activity_log_and_complete():
    activity = log_activity(
        type=ActivityType.CALL, subject="Intro call",
        related_type=RelatedType.LEAD, related_ref="LEAD-2026-000001",
    )
    assert activity.done is False
    complete_activity(activity)
    activity.refresh_from_db()
    assert activity.done is True
    assert activity.done_at is not None
