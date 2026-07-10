"""Ops view (ai-reliability T1.8): admin-only read surface over Trace/TraceStep — what the AI
did, what it cost, whether it's healthy. Aggregation only; no write path here.
"""
from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from erp.identity.permissions import HasAnyRole
from erp.identity.roles import SYSTEM_ADMIN

from ..models import Trace, TraceStep

# The ops view exposes cost, error detail and every user's activity — company-wide operational
# data, same bar as knowledge-base management (see api/views.py's _CanManageKnowledge).
_CanViewOps = HasAnyRole.require(SYSTEM_ADMIN)

RESULTS_DIR = Path(__file__).resolve().parents[1] / "evals" / "results"
DEFAULT_DAYS = 7
MAX_DAYS = 90
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


def _envelope(data, status: int = 200) -> Response:
    return Response({"data": data}, status=status)


def _int_param(request: Request, name: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = request.query_params.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, value))


def _percentile(sorted_values: list[int], pct: float) -> int:
    if not sorted_values:
        return 0
    index = min(len(sorted_values) - 1, int(round(pct * (len(sorted_values) - 1))))
    return sorted_values[index]


def _latest_scoreboard() -> dict | None:
    """The most recent ``run_evals`` output (T1.6), or None if none has been recorded yet."""
    if not RESULTS_DIR.exists():
        return None
    files = sorted(f for f in RESULTS_DIR.glob("*.json") if f.stem != "judge_calibration")
    if not files:
        return None
    try:
        data = json.loads(files[-1].read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return {
        "date": files[-1].stem,
        "pass_rate": data.get("pass_rate"),
        "pass": data.get("pass"),
        "fail": data.get("fail"),
        "needs_judge": data.get("needs_judge"),
        "error": data.get("error"),
    }


class OpsSummaryView(APIView):
    """Per-day/feature volume, error rate, latency percentiles, tokens, cost, top error classes,
    and the latest offline eval scoreboard — everything the ops page's tiles + chart need."""

    permission_classes = [_CanViewOps]

    def get(self, request: Request) -> Response:
        days = _int_param(request, "days", DEFAULT_DAYS, minimum=1, maximum=MAX_DAYS)
        since = timezone.now() - timedelta(days=days)
        qs = Trace.objects.filter(created_at__gte=since)

        daily: dict[str, dict] = {}
        rows = (
            qs.annotate(day=TruncDate("created_at"))
            .values("day", "feature")
            .annotate(count=Count("id"))
            .order_by("day", "feature")
        )
        for row in rows:
            d = row["day"].isoformat()
            bucket = daily.setdefault(d, {"date": d, "count": 0, "by_feature": {}})
            bucket["count"] += row["count"]
            bucket["by_feature"][row["feature"]] = row["count"]

        total = qs.count()
        error_count = qs.exclude(status=Trace.Status.OK).count()
        error_rate = (error_count / total) if total else 0.0

        latencies = sorted(qs.values_list("latency_ms", flat=True))
        ttfts = sorted(
            int(meta["ttft_ms"])
            for meta in qs.values_list("meta", flat=True)
            if isinstance(meta, dict) and isinstance(meta.get("ttft_ms"), (int, float))
        )

        totals = qs.aggregate(
            input_tokens=Sum("input_tokens"), output_tokens=Sum("output_tokens"),
            cost_microcents=Sum("cost_microcents"),
        )

        top_errors = [
            {"error_class": r["error_class"] or "unknown", "count": r["count"]}
            for r in (
                qs.exclude(status=Trace.Status.OK)
                .values("error_class")
                .annotate(count=Count("id"))
                .order_by("-count")[:5]
            )
        ]

        return _envelope({
            "days": days,
            "total_calls": total,
            "error_rate": error_rate,
            "daily": sorted(daily.values(), key=lambda r: r["date"]),
            "latency_ms": {"p50": _percentile(latencies, 0.5), "p95": _percentile(latencies, 0.95)},
            "ttft_ms": {"p50": _percentile(ttfts, 0.5), "p95": _percentile(ttfts, 0.95)},
            "input_tokens": totals["input_tokens"] or 0,
            "output_tokens": totals["output_tokens"] or 0,
            "cost_microcents": totals["cost_microcents"] or 0,
            "top_error_classes": top_errors,
            "eval_scoreboard": _latest_scoreboard(),
        })


def _trace_row(trace: Trace, *, steps: list[dict]) -> dict:
    return {
        "id": str(trace.id),
        "created_at": trace.created_at.isoformat(),
        "feature": trace.feature,
        "actor": (
            {"id": trace.actor_id, "username": trace.actor.username} if trace.actor_id else None
        ),
        "provider": trace.provider,
        "model": trace.model,
        "prompt_ref": trace.prompt_ref,
        "input_tokens": trace.input_tokens,
        "output_tokens": trace.output_tokens,
        "latency_ms": trace.latency_ms,
        "cost_microcents": trace.cost_microcents,
        "status": trace.status,
        "error_class": trace.error_class,
        "meta": trace.meta,
        "steps": steps,
    }


class OpsTracesView(APIView):
    """Paginated trace list with step drill-down, filterable by feature/status/day-window."""

    permission_classes = [_CanViewOps]

    def get(self, request: Request) -> Response:
        days = _int_param(request, "days", DEFAULT_DAYS, minimum=1, maximum=MAX_DAYS)
        page = _int_param(request, "page", 1, minimum=1, maximum=1_000_000)
        page_size = _int_param(request, "page_size", DEFAULT_PAGE_SIZE, minimum=1, maximum=MAX_PAGE_SIZE)

        qs = Trace.objects.select_related("actor").filter(
            created_at__gte=timezone.now() - timedelta(days=days)
        ).order_by("-created_at")

        feature = request.query_params.get("feature")
        if feature:
            qs = qs.filter(feature=feature)
        status = request.query_params.get("status")
        if status:
            qs = qs.filter(status=status)

        total = qs.count()
        start = (page - 1) * page_size
        page_traces = list(qs[start:start + page_size])

        steps_by_trace: dict[str, list[dict]] = {}
        for step in TraceStep.objects.filter(trace_id__in=[t.id for t in page_traces]).order_by(
            "trace_id", "seq"
        ):
            steps_by_trace.setdefault(str(step.trace_id), []).append({
                "seq": step.seq, "kind": step.kind, "name": step.name,
                "latency_ms": step.latency_ms, "ok": step.ok, "detail": step.detail,
            })

        return _envelope({
            "count": total,
            "page": page,
            "page_size": page_size,
            "results": [
                _trace_row(t, steps=steps_by_trace.get(str(t.id), [])) for t in page_traces
            ],
        })
