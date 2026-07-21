"""Public contract for the accounting module.

This is the ONLY surface other modules (Sales, Purchasing, ...) may import from. They post to the
ledger via ``post_journal(JournalInput(...))`` and react to ``JOURNAL_POSTED`` on the event bus —
never by importing accounting's ORM models or internals directly.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass

from django.db.models import Q

from erp.identity.scoping import scope_queryset

from ..domain.models import Account, FiscalYear, JournalEntry, Period
from ..events import JOURNAL_POSTED, PERIOD_CLOSED
from ..services import chart as _chart
from ..services import reports as _reports
from ..services import statements as _statements
from ..services.posting import (
    JournalInput,
    LineInput,
    create_draft_journal,
    enforce_journal_approval,
    post_draft_journal_entry,
    post_journal,
    reverse_journal,
)
from ..services.seeding import (
    baseline_summary,
    get_standard_vat_rate_bps,
    seed_baseline_accounting,
    set_standard_vat_rate,
)
from ..services.taxes import TaxCodeInfo, compute_tax, find_tax_code

# --- scoped/gated read helpers for the AI assistant (session 08 tool catalog) -------------------
# The financial statements are company-wide GL aggregates (not per-record scoped); the assistant's
# tool layer gates them by the caller's accounting permission. Journals are per-record and scoped
# here via ``scope_queryset``. All amounts stay in minor units — the tool layer formats them.

def _period_range(period: str) -> tuple[datetime.date, datetime.date, str]:
    today = datetime.date.today()
    if period == "last_month":
        first_this = today.replace(day=1)
        last_prev = first_this - datetime.timedelta(days=1)
        start = last_prev.replace(day=1)
        return start, last_prev, start.strftime("%Y-%m")
    if period == "this_year":
        return today.replace(month=1, day=1), today, str(today.year)
    return today.replace(day=1), today, today.strftime("%Y-%m")


def trial_balance_summary(*, period: str = "this_month", limit: int = 8) -> dict:
    """Trial-balance totals up to the end of a period + the largest balances (integrity check)."""
    _, end, label = _period_range(period)
    tb = _reports.trial_balance(as_of=end)
    top = sorted(tb.rows, key=lambda r: -abs(r.balance))[: max(1, min(limit, 20))]
    return {
        "period_label": label, "as_of": str(end),
        "total_debit_minor": tb.total_debit, "total_credit_minor": tb.total_credit,
        "is_balanced": tb.is_balanced,
        "accounts": [
            {"code": r.account_code, "name": r.account_name, "type": r.account_type,
             "balance_minor": r.balance}
            for r in top
        ],
    }


def income_statement_summary(*, period: str = "this_month") -> dict:
    """Revenue, expenses and net income over a period (top lines of each)."""
    start, end, label = _period_range(period)
    stmt = _statements.income_statement(date_from=start, date_to=end)
    return {
        "period_label": label, "date_from": str(start), "date_to": str(end),
        "total_revenue_minor": stmt.total_revenue,
        "total_expenses_minor": stmt.total_expenses,
        "net_income_minor": stmt.net_income,
        "revenue": [{"code": l.account_code, "name": l.account_name, "amount_minor": l.amount}
                    for l in stmt.revenue[:5]],
        "expenses": [{"code": l.account_code, "name": l.account_name, "amount_minor": l.amount}
                     for l in stmt.expenses[:5]],
    }


def vat_return_status(*, period: str = "this_month") -> dict:
    """VAT collected vs recovered over a period, and the net payable to the authority."""
    start, end, label = _period_range(period)
    vat = _reports.vat_return(start, end)
    return {
        "period_label": label, "start_date": vat.start_date, "end_date": vat.end_date,
        "output_vat_minor": vat.output_vat, "input_vat_minor": vat.input_vat,
        "net_payable_minor": vat.net_payable, "is_payable": vat.is_payable,
    }


def find_journal(actor, *, query: str, limit: int = 8) -> list[dict]:
    """Find posted journal entries by number, reference or memo — scoped to the actor."""
    q = (query or "").strip()
    qs = scope_queryset(actor, JournalEntry.objects.all(), "accounting.journal.view")
    if q:
        qs = qs.filter(Q(number__icontains=q) | Q(reference__icontains=q) | Q(memo__icontains=q))
    return [
        {"id": str(e.id), "number": e.number, "date": str(e.date), "status": e.status,
         "memo": e.memo, "source": e.source}
        for e in qs.order_by("-date", "number")[: max(1, min(limit, 20))]
    ]


def get_journal_entry(actor, entry_id) -> JournalEntry | None:
    """One journal entry (the ORM record, lines + accounts prefetched) scoped to the actor — the
    loader the gated assistant post-draft action uses to feed ``post_draft_journal_entry``. Returns
    the model (as ``post_journal``/``reverse_journal`` already take one) rather than a dict, because
    its consumer posts it. ``None`` if the entry is out of scope or does not exist."""
    return (
        scope_queryset(actor, JournalEntry.objects.all(), "accounting.journal.view")
        .prefetch_related("lines__account")
        .filter(id=entry_id)
        .first()
    )


def account_balance(*, query: str) -> dict:
    """The current (cumulative) balance of one account, resolved from code or name."""
    q = (query or "").strip()
    account = Account.objects.filter(code=q).first() or Account.objects.filter(
        Q(code__icontains=q) | Q(name__icontains=q)
    ).order_by("code").first()
    if account is None:
        return {"account": None}
    gl = _reports.general_ledger(account.code)
    return {
        "account": {"code": account.code, "name": account.name, "type": account.type},
        "balance_minor": gl.closing_balance,
        "entry_count": len(gl.lines),
    }

@dataclass
class AccountInfo:
    code: str
    name: str
    type: str
    is_postable: bool = True
    is_active: bool = True


def find_account(code: str) -> AccountInfo | None:
    """An account by its exact code, or ``None``."""
    account = Account.objects.filter(code=code).first()
    if account is None:
        return None
    return AccountInfo(code=account.code, name=account.name, type=account.type,
                       is_postable=account.is_postable, is_active=account.is_active)


def list_accounts() -> list[AccountInfo]:
    """Light snapshot of every account (for cross-module lookups/matching, e.g. journal lines)."""
    return [
        AccountInfo(code=a.code, name=a.name, type=a.type, is_postable=a.is_postable,
                   is_active=a.is_active)
        for a in Account.objects.all()
    ]


def next_account_code(account_type: str) -> str:
    """Preview the code a new account of this type would receive if none is given."""
    return _chart.next_account_code(account_type)


def create_account(*, name: str, type: str, code: str = "", parent_code: str = "",
                   actor=None) -> AccountInfo | None:
    """Create a chart-of-accounts leaf. ``None`` if ``parent_code`` was given but is stale."""
    account = _chart.create_account(name=name, type=type, code=code, parent_code=parent_code,
                                    actor=actor)
    if account is None:
        return None
    return AccountInfo(code=account.code, name=account.name, type=account.type,
                       is_postable=account.is_postable, is_active=account.is_active)


def create_journal_entry_draft(data: JournalInput, actor=None) -> JournalEntry:
    """Validate and create an UNPOSTED draft journal entry (see ``post_journal`` for the shared
    invariants). A human posts it later from the journal screen."""
    return create_draft_journal(data, actor=actor)


def current_fiscal_period() -> dict | None:
    """The fiscal year + period covering today, or None if neither is set up yet."""
    today = datetime.date.today()
    year = FiscalYear.objects.filter(start_date__lte=today, end_date__gte=today).first()
    period = Period.objects.filter(start_date__lte=today, end_date__gte=today).first()
    if year is None and period is None:
        return None
    return {
        "fiscal_year_code": year.code if year else None,
        "period_code": period.code if period else None,
        "period_status": period.status if period else None,
    }


__all__ = [
    "trial_balance_summary",
    "income_statement_summary",
    "vat_return_status",
    "find_journal",
    "get_journal_entry",
    "account_balance",
    "current_fiscal_period",
    "AccountInfo",
    "find_account",
    "list_accounts",
    "next_account_code",
    "create_account",
    "create_journal_entry_draft",
    "Money",
    "DEFAULT_CURRENCY",
    "JournalInput",
    "LineInput",
    "enforce_journal_approval",
    "post_draft_journal_entry",
    "post_journal",
    "reverse_journal",
    "TaxCodeInfo",
    "compute_tax",
    "find_tax_code",
    "JOURNAL_POSTED",
    "PERIOD_CLOSED",
    "seed_baseline_accounting",
    "baseline_summary",
    "get_standard_vat_rate_bps",
    "set_standard_vat_rate",
]
