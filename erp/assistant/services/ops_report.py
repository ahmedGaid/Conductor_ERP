"""Weekly AI operations report (ai-reliability T1.9): aggregates ``Trace`` rows into the same
shape ``api.ops.OpsSummaryView`` shows an admin live, but as a standing weekly artifact — a
Markdown file under ``Docs/ops/`` plus a notification to every System Admin.

Mirrors ``services.digest``'s shape (``build_*`` returns the content, ``send_*`` dispatches it) so
the two ambient reports read the same way; ``send_weekly_report`` is the function the management
command and the Celery beat entry both call, exactly as ``send_digests`` is for the daily digest.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from django.db import models as django_models
from django.db.models import Count, Sum
from django.utils import timezone

from erp.notifications.domain.models import NotificationChannel
from erp.notifications.services import dispatch

from ..models import Trace

DOCS_OPS_DIR = Path(__file__).resolve().parents[3] / "Docs" / "ops"
RESULTS_DIR = Path(__file__).resolve().parents[1] / "evals" / "results"

DEFAULT_DAYS = 7


def isoweek_label(d: date | None = None) -> str:
    iso = (d or date.today()).isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _scoreboard_files() -> list[Path]:
    if not RESULTS_DIR.exists():
        return []
    return sorted(f for f in RESULTS_DIR.glob("*.json") if f.stem != "judge_calibration")


def _load_scoreboard(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def eval_delta() -> dict | None:
    """Pass rate of the latest offline ``run_evals`` scoreboard vs. the run before it. ``None``
    when no scoreboard has been recorded yet; ``previous_pass_rate``/``delta`` stay ``None`` when
    only one run exists (nothing to compare against yet)."""
    files = _scoreboard_files()
    if not files:
        return None
    latest = _load_scoreboard(files[-1])
    if latest is None:
        return None
    previous = _load_scoreboard(files[-2]) if len(files) > 1 else None
    latest_rate = latest.get("pass_rate")
    previous_rate = previous.get("pass_rate") if previous else None
    return {
        "date": files[-1].stem,
        "pass_rate": latest_rate,
        "previous_date": files[-2].stem if previous else None,
        "previous_pass_rate": previous_rate,
        "delta": (latest_rate - previous_rate) if previous_rate is not None and latest_rate is not None else None,
    }


def build_report(*, days: int = DEFAULT_DAYS) -> dict:
    """Aggregate the last ``days`` of Trace rows: volume, cost, error mix, and the eval delta."""
    since = timezone.now() - timedelta(days=days)
    qs = Trace.objects.filter(created_at__gte=since)
    total = qs.count()
    error_count = qs.exclude(status=Trace.Status.OK).count()
    totals = qs.aggregate(
        input_tokens=Sum("input_tokens"), output_tokens=Sum("output_tokens"),
        cost_microcents=Sum("cost_microcents"),
    )
    error_mix = [
        {"error_class": r["error_class"] or "unknown", "count": r["count"]}
        for r in (
            qs.exclude(status=Trace.Status.OK)
            .values("error_class")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
    ]
    return {
        "days": days,
        "total_calls": total,
        "error_rate": (error_count / total) if total else 0.0,
        "input_tokens": totals["input_tokens"] or 0,
        "output_tokens": totals["output_tokens"] or 0,
        "cost_microcents": totals["cost_microcents"] or 0,
        "error_mix": error_mix,
        "eval": eval_delta(),
    }


def _format_cost(cost_microcents: int) -> str:
    # Same unit convention as OpsPage.tsx's formatCost: microcents are 1e-6 of a currency cent.
    return f"${cost_microcents / 100_000_000:.4f}"


def render_markdown(report: dict, *, week: str) -> str:
    lines = [f"# AI weekly report — {week}", ""]
    lines.append(f"- Calls: **{report['total_calls']}** over the last {report['days']} days")
    lines.append(f"- Error rate: **{report['error_rate']:.1%}**")
    lines.append(f"- Cost: **{_format_cost(report['cost_microcents'])}**")
    lines.append(f"- Tokens: {report['input_tokens']} in / {report['output_tokens']} out")
    lines.append("")
    lines.append("## Error mix")
    if report["error_mix"]:
        lines.append("")
        lines.append("| error_class | count |")
        lines.append("| --- | --- |")
        for row in report["error_mix"]:
            lines.append(f"| {row['error_class']} | {row['count']} |")
    else:
        lines.append("")
        lines.append("No errors this week.")
    lines.append("")
    lines.append("## Offline eval scoreboard")
    lines.append("")
    ev = report["eval"]
    if ev is None:
        lines.append("No `run_evals` scoreboard recorded yet.")
    else:
        lines.append(f"- Latest ({ev['date']}): **{ev['pass_rate']:.0%}** pass rate")
        if ev["delta"] is not None:
            sign = "+" if ev["delta"] >= 0 else ""
            lines.append(
                f"- Previous ({ev['previous_date']}): {ev['previous_pass_rate']:.0%} "
                f"(delta {sign}{ev['delta']:.1%})"
            )
        else:
            lines.append("- No previous run to compare against yet.")
    lines.append("")
    return "\n".join(lines)


def write_report_file(markdown: str, *, week: str) -> Path:
    DOCS_OPS_DIR.mkdir(parents=True, exist_ok=True)
    path = DOCS_OPS_DIR / f"ai-week-{week}.md"
    path.write_text(markdown, encoding="utf-8")
    return path


def _admin_recipients():
    from erp.identity.models import User
    from erp.identity.roles import SYSTEM_ADMIN

    return User.objects.filter(is_active=True).filter(
        django_models.Q(is_superuser=True) | django_models.Q(groups__name=SYSTEM_ADMIN)
    ).distinct()


def send_weekly_report(*, days: int = DEFAULT_DAYS) -> Path:
    """Build the report, write ``Docs/ops/ai-week-<isoweek>.md``, and notify every System Admin —
    same dispatch path as the morning digest (``services.digest.send_digests``): one in-app row
    always, one email row when the recipient has an address."""
    week = isoweek_label()
    report = build_report(days=days)
    markdown = render_markdown(report, week=week)
    path = write_report_file(markdown, week=week)

    subject = f"AI weekly report — {week}"
    for user in _admin_recipients():
        dispatch(channel=NotificationChannel.INAPP, recipient=user.username, subject=subject,
                 body=markdown, event_name="assistant.WeeklyReport", actor=user)
        if user.email:
            dispatch(channel=NotificationChannel.EMAIL, recipient=user.email, subject=subject,
                     body=markdown, event_name="assistant.WeeklyReport", actor=user)
    return path
