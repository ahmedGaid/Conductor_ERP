"""Calm milestone moments API (arp-roadmap track P, item 2) — any authenticated user.

Useful, quiet delight: a gentle, dismissible acknowledgment when the company crosses a real
milestone (first profitable month, a round invoice count). No confetti, no sound — that would
break the quiet/calm brand. Company-wide state (``MilestoneAck``): once anyone dismisses it, it's
gone for everyone, so this never nags on every login. At most one milestone is surfaced at a time.
"""
from __future__ import annotations

from django.urls import path
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from erp.accounting.contracts import income_statement_summary
from erp.sales.contracts import invoiced_order_count

from .models import MilestoneAck

# Round numbers worth a quiet nod — checked from the top so only the highest one crossed fires.
INVOICE_COUNT_THRESHOLDS = (100, 500, 1_000, 5_000, 10_000, 50_000, 100_000)


def _invoice_count_key(threshold: int) -> str:
    return f"invoices_{threshold}"


def _pending_invoice_count_milestone(acked_keys: set[str]) -> dict | None:
    count = invoiced_order_count()
    for threshold in sorted(INVOICE_COUNT_THRESHOLDS, reverse=True):
        key = _invoice_count_key(threshold)
        if count >= threshold and key not in acked_keys:
            return {"key": key, "kind": "invoice_count", "value": threshold}
    return None


def _pending_first_profitable_month_milestone(acked_keys: set[str]) -> dict | None:
    key = "first_profitable_month"
    if key in acked_keys:
        return None
    stmt = income_statement_summary(period="this_month")
    if stmt["net_income_minor"] > 0:
        return {"key": key, "kind": "first_profitable_month", "value": None}
    return None


def pending_milestone() -> dict | None:
    """The single highest-priority uncrossed milestone, or ``None``."""
    acked_keys = set(MilestoneAck.objects.values_list("key", flat=True))
    return (
        _pending_invoice_count_milestone(acked_keys)
        or _pending_first_profitable_month_milestone(acked_keys)
    )


class MilestonesView(APIView):
    """``GET /api/dashboard/milestones/`` — the one pending milestone to show, if any."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        return Response({"data": {"milestone": pending_milestone()}})


class MilestoneDismissView(APIView):
    """``POST /api/dashboard/milestones/<key>/dismiss/`` — idempotent, company-wide."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request, key: str) -> Response:
        MilestoneAck.objects.get_or_create(key=key)
        return Response({"data": {"key": key, "dismissed": True}})


urlpatterns = [
    path("milestones/", MilestonesView.as_view(), name="dashboard-milestones"),
    path("milestones/<str:key>/dismiss/", MilestoneDismissView.as_view(), name="dashboard-milestone-dismiss"),
]
