"""Monthly AI usage & cost visibility (twenty-harvest FILE_20 Task A): admin-only read endpoint
over Trace + Budget/SpendRollup, the same records ``api.ops`` already aggregates — this session
adds zero new tracking. Every number here answers "should the AI budget go up or down", so
anything the endpoint can't derive from stored data (e.g. an EGP conversion with no FX rate on
file) is left out rather than shown as fact.
"""
from __future__ import annotations

from datetime import date, datetime

from django.conf import settings
from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from erp.core.errors import ValidationError
from erp.identity.permissions import HasAnyRole
from erp.identity.roles import SYSTEM_ADMIN

from ..models import Budget, SpendRollup, Trace, TraceStep

# Same operational-data bar as api.ops._CanViewOps: cost, per-user activity, company-wide spend.
_CanViewUsage = HasAnyRole.require(SYSTEM_ADMIN)


def _month_start(raw: str | None) -> date:
    if not raw:
        return timezone.localdate().replace(day=1)
    try:
        year_s, month_s = raw.split("-", 1)
        return date(int(year_s), int(month_s), 1)
    except (TypeError, ValueError):
        raise ValidationError(f"Invalid month '{raw}' — expected YYYY-MM.")


def _next_month_start(month_start: date) -> date:
    if month_start.month == 12:
        return date(month_start.year + 1, 1, 1)
    return date(month_start.year, month_start.month + 1, 1)


def _aware(d: date) -> datetime:
    return timezone.make_aware(datetime.combine(d, datetime.min.time()))


def _degraded_minutes(qs) -> int:
    """Distinct calendar-minutes in the period that contain at least one call whose routing
    chain skipped a provider (``gateway/core.py``'s ``routing.skipped``, the same evidence
    ``gateway/status.py``'s live ``mode()`` reads for "degraded"). An exact count of stored
    evidence, not a live-state estimate replayed onto the past."""
    minutes = set()
    for created_at, meta in qs.values_list("created_at", "meta"):
        if isinstance(meta, dict) and meta.get("routing", {}).get("skipped"):
            minutes.add(created_at.replace(second=0, microsecond=0))
    return len(minutes)


def _cache_hit_share(qs, *, range_start: datetime, range_end: datetime) -> float:
    cache_tasks = sorted(getattr(settings, "ASSISTANT_CACHE_TASKS", set()))
    lookups = qs.filter(feature__in=cache_tasks).count()
    if not lookups:
        return 0.0
    hits = TraceStep.objects.filter(
        trace__created_at__gte=range_start, trace__created_at__lt=range_end,
        detail__cache="exact",
    ).count()
    return hits / lookups


def _by_provider(qs) -> list[dict]:
    rows = (
        qs.values("provider")
        .annotate(requests=Count("id"), input_tokens=Sum("input_tokens"),
                  output_tokens=Sum("output_tokens"), cost_microcents=Sum("cost_microcents"))
        .order_by("-cost_microcents")
    )
    return [
        {
            "provider": r["provider"] or "unknown",
            "requests": r["requests"],
            "input_tokens": r["input_tokens"] or 0,
            "output_tokens": r["output_tokens"] or 0,
            "cost_microcents": r["cost_microcents"] or 0,
        }
        for r in rows
    ]


def _by_user(qs) -> list[dict]:
    rows = (
        qs.filter(actor__isnull=False)
        .values("actor_id", "actor__username")
        .annotate(requests=Count("id"), input_tokens=Sum("input_tokens"),
                  output_tokens=Sum("output_tokens"), cost_microcents=Sum("cost_microcents"))
        .order_by("-cost_microcents")
    )
    return [
        {
            "user_id": r["actor_id"],
            "username": r["actor__username"],
            "requests": r["requests"],
            "input_tokens": r["input_tokens"] or 0,
            "output_tokens": r["output_tokens"] or 0,
            "cost_microcents": r["cost_microcents"] or 0,
        }
        for r in rows
    ]


def _budget_row(scope: str) -> dict:
    b = Budget.objects.filter(scope=scope).first()
    return {
        "limit_microcents": b.limit_microcents if b else None,
        "action": b.action if b else None,
    }


def _budget_vs_consumed(month_start: date) -> dict:
    """Config (``Budget``) paired with actual spend (``SpendRollup``) wherever the two share the
    same period grain. ``org`` resets monthly — its rollup row for this exact month is a direct,
    exact "consumed" figure. ``user`` and ``request`` scopes reset per-call/per-day (see
    ``gateway/budgets.py``), so there is no single monthly "consumed" number to pair with their
    limit without averaging/estimating one — the per-user table already gives the real monthly
    total per user, so only the configured ceiling is surfaced here."""
    org = _budget_row(Budget.Scope.ORG)
    org_rollup = SpendRollup.objects.filter(
        scope=Budget.Scope.ORG, scope_key="org", period=month_start).first()
    org["consumed_microcents"] = org_rollup.spend_microcents if org_rollup else 0
    return {
        "request": _budget_row(Budget.Scope.REQUEST),
        "user_daily": _budget_row(Budget.Scope.USER),
        "org": org,
    }


class UsageView(APIView):
    """``GET /api/assistant/usage/?month=YYYY-MM`` — one month's AI totals, provider split,
    per-user table, and budget vs consumed. Defaults to the current month."""

    permission_classes = [_CanViewUsage]

    def get(self, request: Request) -> Response:
        month_start = _month_start(request.query_params.get("month"))
        range_start = _aware(month_start)
        range_end = _aware(_next_month_start(month_start))

        qs = Trace.objects.filter(created_at__gte=range_start, created_at__lt=range_end)
        totals = qs.aggregate(
            input_tokens=Sum("input_tokens"), output_tokens=Sum("output_tokens"),
            cost_microcents=Sum("cost_microcents"),
        )

        return Response({"data": {
            "month": month_start.strftime("%Y-%m"),
            "totals": {
                "requests": qs.count(),
                "input_tokens": totals["input_tokens"] or 0,
                "output_tokens": totals["output_tokens"] or 0,
                "cost_microcents": totals["cost_microcents"] or 0,
                "cache_hit_share": _cache_hit_share(qs, range_start=range_start, range_end=range_end),
                "degraded_minutes": _degraded_minutes(qs),
            },
            "by_provider": _by_provider(qs),
            "by_user": _by_user(qs),
            "budget": _budget_vs_consumed(month_start),
        }})
