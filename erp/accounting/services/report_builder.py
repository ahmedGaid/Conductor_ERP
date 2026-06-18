"""Custom report builder — run a saved `ReportDefinition` over the posted GL.

A definition parameterises a query of posted journal lines (account type / explicit codes / date range)
and a grouping (by account or by period). Running it produces a deterministic table that can be served
as JSON or exported (CSV/XLSX) through the shared renderer. Scheduled definitions are run by a Celery
task that writes the export to disk. Money is integer **minor units**.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from django.conf import settings
from django.db.models import Sum
from django.utils import timezone

from ..domain.accounts import signed_balance
from ..domain.models import EntryStatus, JournalLine, ReportDefinition, ReportGroupBy, ReportSchedule


@dataclass
class BuiltRow:
    group_key: str
    group_label: str
    debit: int
    credit: int
    balance: int


@dataclass
class BuiltReport:
    definition_id: str
    name: str
    group_by: str
    date_from: str | None
    date_to: str | None
    rows: list[BuiltRow]
    total_debit: int
    total_credit: int
    total_balance: int


def _filtered_lines(defn: ReportDefinition):
    qs = JournalLine.objects.filter(entry__status=EntryStatus.POSTED)
    if defn.account_type:
        qs = qs.filter(account__type=defn.account_type)
    codes = [c.strip() for c in defn.account_codes.split(",") if c.strip()]
    if codes:
        qs = qs.filter(account__code__in=codes)
    if defn.date_from:
        qs = qs.filter(entry__date__gte=defn.date_from)
    if defn.date_to:
        qs = qs.filter(entry__date__lte=defn.date_to)
    return qs


def run_definition(defn: ReportDefinition) -> BuiltReport:
    """Execute a saved definition and return the grouped result. Deterministic for a fixed ledger."""
    qs = _filtered_lines(defn)
    rows: list[BuiltRow] = []
    total_debit = total_credit = total_balance = 0

    if defn.group_by == ReportGroupBy.PERIOD:
        agg = (
            qs.values("entry__period__code")
            .annotate(debit=Sum("debit"), credit=Sum("credit"))
            .order_by("entry__period__code")
        )
        for r in agg:
            debit, credit = r["debit"] or 0, r["credit"] or 0
            balance = debit - credit  # net movement (mixed account types)
            code = r["entry__period__code"] or "—"
            rows.append(BuiltRow(code, code, debit, credit, balance))
            total_debit += debit
            total_credit += credit
            total_balance += balance
    else:  # by account
        agg = (
            qs.values("account__code", "account__name", "account__type")
            .annotate(debit=Sum("debit"), credit=Sum("credit"))
            .order_by("account__code")
        )
        for r in agg:
            debit, credit = r["debit"] or 0, r["credit"] or 0
            balance = signed_balance(r["account__type"], debit, credit)
            rows.append(BuiltRow(r["account__code"], f"{r['account__code']} — {r['account__name']}",
                                 debit, credit, balance))
            total_debit += debit
            total_credit += credit
            total_balance += balance

    return BuiltReport(
        definition_id=str(defn.id), name=defn.name, group_by=defn.group_by,
        date_from=str(defn.date_from) if defn.date_from else None,
        date_to=str(defn.date_to) if defn.date_to else None,
        rows=rows, total_debit=total_debit, total_credit=total_credit, total_balance=total_balance,
    )


# --- Scheduling ------------------------------------------------------------

_INTERVAL = {
    ReportSchedule.DAILY: dt.timedelta(days=1),
    ReportSchedule.WEEKLY: dt.timedelta(weeks=1),
    ReportSchedule.MONTHLY: dt.timedelta(days=30),
}


def _reports_dir():
    path = getattr(settings, "REPORTS_DIR", None)
    if path is None:
        path = settings.STORAGE_ROOT / "reports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def is_due(defn: ReportDefinition, now=None) -> bool:
    if defn.schedule == ReportSchedule.NONE:
        return False
    now = now or timezone.now()
    if defn.last_run_at is None:
        return True
    return (now - defn.last_run_at) >= _INTERVAL[defn.schedule]


def run_scheduled(now=None) -> list[tuple[str, str]]:
    """Run every due scheduled definition, write a CSV export to the reports dir, stamp last_run_at.

    Returns a list of (definition name, file path). Imported lazily by the Celery task so importing
    this module never drags in the export renderer.
    """
    from erp.core.exports import render_bytes

    from ..api import exports as export_tables  # report_table builder

    now = now or timezone.now()
    written: list[tuple[str, str]] = []
    for defn in ReportDefinition.objects.exclude(schedule=ReportSchedule.NONE):
        if not is_due(defn, now):
            continue
        built = run_definition(defn)
        table = export_tables.built_report_table(built, "en")
        payload = render_bytes(table, "csv")
        safe = "".join(ch if ch.isalnum() else "-" for ch in defn.name)[:40]
        file_path = _reports_dir() / f"{safe}-{now.date().isoformat()}.csv"
        file_path.write_bytes(payload)
        defn.last_run_at = now
        defn.save(update_fields=["last_run_at"])
        written.append((defn.name, str(file_path)))
    return written
