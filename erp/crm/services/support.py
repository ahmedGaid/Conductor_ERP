"""Support tickets (priority-driven SLA) and activities (calls/meetings/tasks logged anywhere).

Ticket SLA: the due time is computed from priority at open (urgent 4h … low 72h). A ticket that is
still open past its due time is breached (``Ticket.is_breached``). Resolving stamps ``resolved_at``;
closing stamps ``closed_at``. Every transition is atomic and guarded.
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from erp.audit import services as audit
from erp.core.events import bus

from .. import events
from ..domain.models import (
    Activity,
    OPEN_TICKET_STATUSES,
    Ticket,
    TicketPriority,
    TicketStatus,
)
from ..errors import InvalidTransitionError


def _next_ticket_number() -> str:
    year = timezone.now().year
    prefix = f"TKT-{year}-"
    last = (
        Ticket.objects.filter(number__startswith=prefix)
        .order_by("-number")
        .values_list("number", flat=True)
        .first()
    )
    seq = (int(last.rsplit("-", 1)[1]) + 1) if last else 1
    return f"{prefix}{seq:06d}"


@transaction.atomic
def create_ticket(
    *, subject: str, customer_code: str = "", description: str = "",
    priority: str = TicketPriority.MEDIUM, owner: str = "", actor=None,
) -> Ticket:
    opened_at = timezone.now()
    ticket = Ticket.objects.create(
        number=_next_ticket_number(), customer_code=customer_code, subject=subject,
        description=description, priority=priority, owner=owner, status=TicketStatus.OPEN,
        opened_at=opened_at, sla_due_at=Ticket.sla_due(opened_at, priority),
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
    )
    audit.record(module="crm", action="create_ticket", entity_type="Ticket",
                 entity_id=ticket.number, actor=actor)
    bus.publish(events.TICKET_OPENED,
                {"ticket": ticket.number, "priority": priority, "customer": customer_code})
    return ticket


@transaction.atomic
def start_ticket(ticket: Ticket, actor=None) -> Ticket:
    if ticket.status != TicketStatus.OPEN:
        raise InvalidTransitionError(data={"ticket": ticket.number, "status": ticket.status})
    ticket.status = TicketStatus.IN_PROGRESS
    ticket.save(update_fields=["status", "updated_at"])
    audit.record(module="crm", action="start_ticket", entity_type="Ticket",
                 entity_id=ticket.number, actor=actor)
    return ticket


@transaction.atomic
def resolve_ticket(ticket: Ticket, *, resolution: str = "", actor=None) -> Ticket:
    if ticket.status not in OPEN_TICKET_STATUSES:
        raise InvalidTransitionError(data={"ticket": ticket.number, "status": ticket.status})
    ticket.status = TicketStatus.RESOLVED
    ticket.resolved_at = timezone.now()
    if resolution:
        ticket.description = (ticket.description + f"\nResolution: {resolution}").strip()
    ticket.save(update_fields=["status", "resolved_at", "description", "updated_at"])
    audit.record(module="crm", action="resolve_ticket", entity_type="Ticket",
                 entity_id=ticket.number, actor=actor,
                 after={"breached": ticket.resolved_at > ticket.sla_due_at})
    bus.publish(events.TICKET_RESOLVED, {"ticket": ticket.number})
    return ticket


@transaction.atomic
def close_ticket(ticket: Ticket, actor=None) -> Ticket:
    if ticket.status != TicketStatus.RESOLVED:
        raise InvalidTransitionError(data={"ticket": ticket.number, "status": ticket.status})
    ticket.status = TicketStatus.CLOSED
    ticket.closed_at = timezone.now()
    ticket.save(update_fields=["status", "closed_at", "updated_at"])
    audit.record(module="crm", action="close_ticket", entity_type="Ticket",
                 entity_id=ticket.number, actor=actor)
    return ticket


@transaction.atomic
def log_activity(
    *, type: str, subject: str, related_type: str, related_ref: str,
    owner: str = "", due_date=None, notes: str = "", actor=None,
) -> Activity:
    activity = Activity.objects.create(
        type=type, subject=subject, related_type=related_type, related_ref=related_ref,
        owner=owner, due_date=due_date, notes=notes,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
    )
    audit.record(module="crm", action="log_activity", entity_type="Activity",
                 entity_id=str(activity.id), actor=actor,
                 after={"related": f"{related_type}:{related_ref}"})
    return activity


@transaction.atomic
def complete_activity(activity: Activity, actor=None) -> Activity:
    activity.done = True
    activity.done_at = timezone.now()
    activity.save(update_fields=["done", "done_at", "updated_at"])
    audit.record(module="crm", action="complete_activity", entity_type="Activity",
                 entity_id=str(activity.id), actor=actor)
    return activity
