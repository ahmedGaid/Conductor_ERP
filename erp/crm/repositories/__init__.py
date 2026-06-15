"""Data-access boundary for CRM."""
from __future__ import annotations

from django.db.models import Sum

from erp.core.repository import Repository

from ..domain.models import Lead, Opportunity, OPEN_STAGES, Ticket


class LeadRepository(Repository[Lead]):
    model = Lead

    def by_code(self, code: str) -> Lead | None:
        return self.model._default_manager.filter(code=code).first()


class OpportunityRepository(Repository[Opportunity]):
    model = Opportunity

    def by_number(self, number: str) -> Opportunity | None:
        return self.model._default_manager.filter(number=number).first()

    def open_pipeline_minor(self) -> int:
        agg = Opportunity.objects.filter(stage__in=OPEN_STAGES).aggregate(total=Sum("amount_minor"))
        return agg["total"] or 0


class TicketRepository(Repository[Ticket]):
    model = Ticket

    def by_number(self, number: str) -> Ticket | None:
        return self.model._default_manager.filter(number=number).first()


leads = LeadRepository()
opportunities = OpportunityRepository()
tickets = TicketRepository()
