"""Celery tasks for scheduled (non-event) workflow triggers — low stock, overdue invoices, stale
leads, ticket escalation. Mirrors erp/accounting/tasks.py's single-purpose @shared_task pattern;
the beat schedule (config/settings/base.py CELERY_BEAT_SCHEDULE) fires this once daily and this
task decides what's due, same shape as `accounting.run_scheduled_reports`.
"""
from __future__ import annotations

from celery import shared_task
from django.db.models import Sum
from django.utils import timezone

from .engine import engine
from .models import WorkflowTrigger


def _check_low_stock() -> None:
    from erp.inventory.domain.models import Item, StockBalance

    for item in Item.objects.filter(reorder_point__gt=0):
        on_hand = StockBalance.objects.filter(item=item).aggregate(total=Sum("quantity"))["total"] or 0
        if on_hand < item.reorder_point:
            for trigger in WorkflowTrigger.objects.filter(schedule="low_stock", is_active=True):
                engine.start_instance(trigger.workflow, {"item_name": item.name, "on_hand": float(on_hand)})


def _check_overdue_invoices(days: int) -> None:
    from erp.sales.domain.models import OrderStatus, SalesOrder

    cutoff = timezone.now().date() - timezone.timedelta(days=days)
    # outstanding_minor is a Python property (invoiced_minor - paid_minor), not a queryable field,
    # so the outstanding>0 filter runs in Python after the DB narrows by status/due_date.
    candidates = SalesOrder.objects.filter(status=OrderStatus.INVOICED, due_date__lt=cutoff)
    overdue = [o for o in candidates if o.outstanding_minor > 0]
    for order in overdue:
        for trigger in WorkflowTrigger.objects.filter(schedule=f"overdue_invoice:{days}", is_active=True):
            engine.start_instance(trigger.workflow, {"order_number": order.number})


def _check_stale_leads(days: int) -> None:
    from erp.crm.domain.models import Lead, LeadStatus

    cutoff = timezone.now() - timezone.timedelta(days=days)
    stale = Lead.objects.filter(status=LeadStatus.NEW, created_at__lt=cutoff)
    for lead in stale:
        for trigger in WorkflowTrigger.objects.filter(schedule=f"stale_lead:{days}", is_active=True):
            engine.start_instance(trigger.workflow, {"lead_name": lead.name, "owner": lead.owner})


def _check_ticket_escalations() -> None:
    from erp.crm.services.support import run_escalations

    escalated = run_escalations()
    if escalated:
        for trigger in WorkflowTrigger.objects.filter(schedule="ticket_escalation", is_active=True):
            engine.start_instance(trigger.workflow, {"escalated_count": len(escalated)})


@shared_task(name="workflow.run_scheduled_triggers")
def run_scheduled_triggers() -> None:
    """Run every scheduled-trigger check once. Each checker is independently idempotent (matches
    the existing `run_escalations` guard pattern) — running this twice in a row is always safe."""
    _check_low_stock()
    _check_ticket_escalations()
    for trigger in WorkflowTrigger.objects.filter(is_active=True).exclude(schedule=""):
        if trigger.schedule.startswith("overdue_invoice:"):
            _check_overdue_invoices(int(trigger.schedule.split(":")[1]))
        elif trigger.schedule.startswith("stale_lead:"):
            _check_stale_leads(int(trigger.schedule.split(":")[1]))
