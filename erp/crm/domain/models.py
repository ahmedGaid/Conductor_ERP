"""CRM ORM models.

The relationship side of the ERP: Leads → Opportunities (pipeline) → won creates a Sales Order
(via the sales public contract, by customer code — no cross-module FK), plus Activities (calls/
meetings/tasks logged against any record) and support Tickets with priority-driven SLA timers.

Customers are referenced by **code string** (the same key the sales module uses) so CRM never holds
a FK into another module. Money is integer minor units; quantities are Decimal.
"""
from __future__ import annotations

import datetime as dt

from django.db import models
from django.utils import timezone

from erp.core.models import AuditedModel


# --- Leads -----------------------------------------------------------------

class LeadSource(models.TextChoices):
    WEB = "web", "Web"
    REFERRAL = "referral", "Referral"
    CALL = "call", "Cold call"
    CAMPAIGN = "campaign", "Campaign"
    OTHER = "other", "Other"


class LeadStatus(models.TextChoices):
    NEW = "new", "New"
    CONTACTED = "contacted", "Contacted"
    QUALIFIED = "qualified", "Qualified"
    UNQUALIFIED = "unqualified", "Unqualified"
    CONVERTED = "converted", "Converted"


class Lead(AuditedModel):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=200)
    company = models.CharField(max_length=200, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=40, blank=True, default="")
    source = models.CharField(max_length=16, choices=LeadSource.choices, default=LeadSource.OTHER)
    status = models.CharField(max_length=16, choices=LeadStatus.choices, default=LeadStatus.NEW)
    owner = models.CharField(max_length=120, blank=True, default="")
    notes = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        db_table = "crm_lead"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status"])]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.code} — {self.name}"


# --- Opportunities (pipeline) ----------------------------------------------

class OppStage(models.TextChoices):
    QUALIFYING = "qualifying", "Qualifying"
    PROPOSAL = "proposal", "Proposal"
    NEGOTIATION = "negotiation", "Negotiation"
    WON = "won", "Won"
    LOST = "lost", "Lost"


OPEN_STAGES = (OppStage.QUALIFYING, OppStage.PROPOSAL, OppStage.NEGOTIATION)


class Opportunity(AuditedModel):
    number = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=200)
    lead = models.ForeignKey(
        Lead, null=True, blank=True, on_delete=models.SET_NULL, related_name="opportunities"
    )
    customer_code = models.CharField(max_length=32, blank=True, default="")  # sales customer key
    warehouse_code = models.CharField(max_length=32, blank=True, default="")  # for the won → SO
    stage = models.CharField(max_length=16, choices=OppStage.choices, default=OppStage.QUALIFYING)
    currency = models.CharField(max_length=3, default="EGP")
    amount_minor = models.BigIntegerField(default=0)  # sum of line totals
    probability = models.IntegerField(default=10)  # 0–100
    expected_close = models.DateField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    sales_order_number = models.CharField(max_length=32, blank=True, default="")  # set on win
    notes = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        db_table = "crm_opportunity"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["stage"]), models.Index(fields=["customer_code"])]

    def __str__(self) -> str:  # pragma: no cover
        return self.number

    @property
    def is_open(self) -> bool:
        return self.stage in OPEN_STAGES

    @property
    def weighted_minor(self) -> int:
        return round(self.amount_minor * self.probability / 100)


class OpportunityLine(models.Model):
    id = models.BigAutoField(primary_key=True)
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name="lines")
    line_no = models.IntegerField()
    item_sku = models.CharField(max_length=64)
    description = models.CharField(max_length=200, blank=True, default="")
    quantity = models.DecimalField(max_digits=18, decimal_places=4)
    unit_price_minor = models.BigIntegerField()
    line_total_minor = models.BigIntegerField()

    class Meta:
        db_table = "crm_opportunity_line"
        ordering = ["opportunity", "line_no"]
        unique_together = [("opportunity", "line_no")]


# --- Activities ------------------------------------------------------------

class ActivityType(models.TextChoices):
    CALL = "call", "Call"
    EMAIL = "email", "Email"
    MEETING = "meeting", "Meeting"
    TASK = "task", "Task"
    NOTE = "note", "Note"


class RelatedType(models.TextChoices):
    LEAD = "lead", "Lead"
    OPPORTUNITY = "opportunity", "Opportunity"
    TICKET = "ticket", "Ticket"


class Activity(AuditedModel):
    type = models.CharField(max_length=16, choices=ActivityType.choices, default=ActivityType.NOTE)
    subject = models.CharField(max_length=200)
    related_type = models.CharField(max_length=16, choices=RelatedType.choices)
    related_ref = models.CharField(max_length=64)  # the related record's code/number
    owner = models.CharField(max_length=120, blank=True, default="")
    due_date = models.DateField(null=True, blank=True)
    done = models.BooleanField(default=False)
    done_at = models.DateTimeField(null=True, blank=True)
    notes = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        db_table = "crm_activity"
        ordering = ["done", "due_date", "-created_at"]
        indexes = [models.Index(fields=["related_type", "related_ref"]), models.Index(fields=["done"])]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.type}: {self.subject}"


# --- Support tickets (SLA) -------------------------------------------------

class TicketPriority(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    URGENT = "urgent", "Urgent"


class TicketStatus(models.TextChoices):
    OPEN = "open", "Open"
    IN_PROGRESS = "in_progress", "In progress"
    RESOLVED = "resolved", "Resolved"
    CLOSED = "closed", "Closed"


# SLA response window per priority, in hours.
SLA_HOURS = {
    TicketPriority.URGENT: 4,
    TicketPriority.HIGH: 8,
    TicketPriority.MEDIUM: 24,
    TicketPriority.LOW: 72,
}

OPEN_TICKET_STATUSES = (TicketStatus.OPEN, TicketStatus.IN_PROGRESS)


class Ticket(AuditedModel):
    number = models.CharField(max_length=32, unique=True)
    customer_code = models.CharField(max_length=32, blank=True, default="")
    subject = models.CharField(max_length=200)
    description = models.CharField(max_length=1000, blank=True, default="")
    priority = models.CharField(
        max_length=16, choices=TicketPriority.choices, default=TicketPriority.MEDIUM
    )
    status = models.CharField(max_length=16, choices=TicketStatus.choices, default=TicketStatus.OPEN)
    owner = models.CharField(max_length=120, blank=True, default="")
    opened_at = models.DateTimeField(default=timezone.now)
    sla_due_at = models.DateTimeField()
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "crm_ticket"
        ordering = ["-opened_at"]
        indexes = [models.Index(fields=["status"]), models.Index(fields=["priority"])]

    def __str__(self) -> str:  # pragma: no cover
        return self.number

    @property
    def is_open(self) -> bool:
        return self.status in OPEN_TICKET_STATUSES

    @property
    def is_breached(self) -> bool:
        """SLA breached: still unresolved and past the due time."""
        if not self.is_open:
            return False
        return timezone.now() > self.sla_due_at

    @staticmethod
    def sla_due(opened_at: dt.datetime, priority: str) -> dt.datetime:
        hours = SLA_HOURS.get(priority, SLA_HOURS[TicketPriority.MEDIUM])
        return opened_at + dt.timedelta(hours=hours)
