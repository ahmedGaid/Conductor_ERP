"""Financial statements derived from the posted General Ledger.

All three are pure functions of posted journal lines:
- **Income Statement** — income vs expense over a date range → net income.
- **Balance Sheet** — assets vs (liabilities + equity + current net income) as of a date. It always
  balances because the underlying ledger does (Σdebit == Σcredit).
- **Cash Flow** — movement of cash/bank accounts over a range; closing == opening + in − out, and
  reconciles to the cash accounts' GL balance.

Note: AR/AP **aging** is intentionally NOT here — it needs per-customer/vendor open-item sub-ledgers
that arrive with the Sales/Purchasing modules; the GL alone only has account balances.
"""
from __future__ import annotations

from dataclasses import dataclass

from django.db.models import Sum

from ..domain.accounts import AccountType, signed_balance
from ..domain.models import Account, EntryStatus, JournalLine, Period


def _resolve_range(date_from, date_to, period_code: str | None):
    """A period_code expands to its [start, end]; explicit dates win if both given."""
    if period_code and not (date_from or date_to):
        period = Period.objects.filter(code=period_code).first()
        if period is not None:
            return period.start_date, period.end_date
    return date_from, date_to


def _lines(date_from=None, date_to=None):
    qs = JournalLine.objects.filter(entry__status=EntryStatus.POSTED)
    if date_from:
        qs = qs.filter(entry__date__gte=date_from)
    if date_to:
        qs = qs.filter(entry__date__lte=date_to)
    return qs


def _by_account(qs):
    return (
        qs.values("account__code", "account__name", "account__type")
        .annotate(debit=Sum("debit"), credit=Sum("credit"))
        .order_by("account__code")
    )


@dataclass
class StatementLine:
    account_code: str
    account_name: str
    amount: int  # signed in the account type's normal direction


@dataclass
class IncomeStatement:
    date_from: str | None
    date_to: str | None
    revenue: list[StatementLine]
    expenses: list[StatementLine]
    total_revenue: int
    total_expenses: int
    net_income: int


def income_statement(*, date_from=None, date_to=None, period_code: str | None = None) -> IncomeStatement:
    date_from, date_to = _resolve_range(date_from, date_to, period_code)
    rows = _by_account(_lines(date_from, date_to))
    revenue: list[StatementLine] = []
    expenses: list[StatementLine] = []
    total_revenue = 0
    total_expenses = 0
    for r in rows:
        amount = signed_balance(r["account__type"], r["debit"] or 0, r["credit"] or 0)
        if amount == 0:
            continue
        line = StatementLine(r["account__code"], r["account__name"], amount)
        if r["account__type"] == AccountType.INCOME:
            revenue.append(line)
            total_revenue += amount
        elif r["account__type"] == AccountType.EXPENSE:
            expenses.append(line)
            total_expenses += amount
    return IncomeStatement(
        date_from=str(date_from) if date_from else None,
        date_to=str(date_to) if date_to else None,
        revenue=revenue,
        expenses=expenses,
        total_revenue=total_revenue,
        total_expenses=total_expenses,
        net_income=total_revenue - total_expenses,
    )


@dataclass
class BalanceSheet:
    as_of: str | None
    assets: list[StatementLine]
    liabilities: list[StatementLine]
    equity: list[StatementLine]
    total_assets: int
    total_liabilities: int
    total_equity: int
    net_income: int  # current-period earnings, folded into equity for the balance check
    total_liabilities_and_equity: int
    is_balanced: bool


def balance_sheet(*, as_of=None) -> BalanceSheet:
    rows = _by_account(_lines(date_to=as_of))
    sections: dict[str, list[StatementLine]] = {"asset": [], "liability": [], "equity": []}
    totals = {"asset": 0, "liability": 0, "equity": 0}
    net_income = 0
    for r in rows:
        amount = signed_balance(r["account__type"], r["debit"] or 0, r["credit"] or 0)
        if amount == 0:
            continue
        type_ = r["account__type"]
        if type_ in sections:
            sections[type_].append(StatementLine(r["account__code"], r["account__name"], amount))
            totals[type_] += amount
        elif type_ == AccountType.INCOME:
            net_income += amount
        elif type_ == AccountType.EXPENSE:
            net_income -= amount
    total_liab_equity = totals["liability"] + totals["equity"] + net_income
    return BalanceSheet(
        as_of=str(as_of) if as_of else None,
        assets=sections["asset"],
        liabilities=sections["liability"],
        equity=sections["equity"],
        total_assets=totals["asset"],
        total_liabilities=totals["liability"],
        total_equity=totals["equity"],
        net_income=net_income,
        total_liabilities_and_equity=total_liab_equity,
        is_balanced=totals["asset"] == total_liab_equity,
    )


@dataclass
class CashFlow:
    date_from: str | None
    date_to: str | None
    opening_balance: int
    cash_in: int
    cash_out: int
    net_change: int
    closing_balance: int
    reconciles: bool


def cash_flow(*, date_from=None, date_to=None, period_code: str | None = None) -> CashFlow:
    date_from, date_to = _resolve_range(date_from, date_to, period_code)
    cash_account_ids = list(
        Account.objects.filter(is_cash=True).values_list("id", flat=True)
    )
    base = JournalLine.objects.filter(
        entry__status=EntryStatus.POSTED, account_id__in=cash_account_ids
    )

    def _movement(qs) -> tuple[int, int]:
        agg = qs.aggregate(d=Sum("debit"), c=Sum("credit"))
        return agg["d"] or 0, agg["c"] or 0

    # Opening = net cash movement strictly before the range start.
    if date_from:
        od, oc = _movement(base.filter(entry__date__lt=date_from))
    else:
        od, oc = 0, 0
    opening = od - oc  # cash is asset (debit-normal): debits increase

    period_qs = base
    if date_from:
        period_qs = period_qs.filter(entry__date__gte=date_from)
    if date_to:
        period_qs = period_qs.filter(entry__date__lte=date_to)
    cash_in, cash_out = _movement(period_qs)
    net_change = cash_in - cash_out
    closing = opening + net_change

    # Independent reconciliation: closing must equal the cash GL balance up to date_to.
    cd, cc = _movement(base.filter(entry__date__lte=date_to) if date_to else base)
    gl_cash_balance = cd - cc

    return CashFlow(
        date_from=str(date_from) if date_from else None,
        date_to=str(date_to) if date_to else None,
        opening_balance=opening,
        cash_in=cash_in,
        cash_out=cash_out,
        net_change=net_change,
        closing_balance=closing,
        reconciles=closing == gl_cash_balance,
    )
