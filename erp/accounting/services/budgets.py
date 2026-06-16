"""Budgets and budget-vs-actual.

A `Budget` holds planned amounts per account+period (`BudgetLine`); the variance report compares them
to the **posted GL** for the same scope. Actuals are read with the same signed-balance convention as
the statements, so a budget on income/expense accounts reads in its natural direction. Money is
integer **minor units**; variance is always `actual − budget`.
"""
from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.db.models import Sum

from ..domain.accounts import signed_balance
from ..domain.models import Account, Budget, BudgetLine, EntryStatus, FiscalYear, JournalLine, Period
from ..errors import InvalidBudgetError


@dataclass
class BudgetLineInput:
    account_code: str
    period_code: str
    amount_minor: int


@transaction.atomic
def create_budget(*, name: str, fiscal_year_code: str, actor=None) -> Budget:
    if not FiscalYear.objects.filter(code=fiscal_year_code).exists():
        raise InvalidBudgetError(data={"fiscal_year": fiscal_year_code})
    return Budget.objects.create(
        name=name, fiscal_year_code=fiscal_year_code,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
    )


@transaction.atomic
def set_budget_line(budget: Budget, account_code: str, period_code: str, amount_minor: int) -> BudgetLine:
    """Upsert one planned amount. A zero amount removes the line."""
    if not Account.objects.filter(code=account_code).exists():
        raise InvalidBudgetError(data={"account": account_code})
    if amount_minor == 0:
        BudgetLine.objects.filter(budget=budget, account_code=account_code, period_code=period_code).delete()
        return BudgetLine(budget=budget, account_code=account_code, period_code=period_code, amount_minor=0)
    line, _ = BudgetLine.objects.update_or_create(
        budget=budget, account_code=account_code, period_code=period_code,
        defaults={"amount_minor": amount_minor},
    )
    return line


@transaction.atomic
def set_budget_lines(budget: Budget, lines: list[BudgetLineInput]) -> int:
    for ln in lines:
        set_budget_line(budget, ln.account_code, ln.period_code, ln.amount_minor)
    return len(lines)


@dataclass
class VarianceRow:
    account_code: str
    account_name: str
    account_type: str
    budget_minor: int
    actual_minor: int
    variance_minor: int  # actual − budget


@dataclass
class BudgetVsActual:
    budget_id: str
    budget_name: str
    fiscal_year_code: str
    period_code: str | None
    rows: list[VarianceRow]
    total_budget: int
    total_actual: int
    total_variance: int


def _scope_dates(budget: Budget, period_code: str | None):
    """The [start, end] the actuals are summed over: a single period, else the whole fiscal year."""
    if period_code:
        period = Period.objects.filter(code=period_code).first()
        if period is not None:
            return period.start_date, period.end_date
    fy = FiscalYear.objects.filter(code=budget.fiscal_year_code).first()
    if fy is not None:
        return fy.start_date, fy.end_date
    return None, None


def budget_vs_actual(budget: Budget, *, period_code: str | None = None) -> BudgetVsActual:
    """Planned vs posted-actual per budgeted account over the chosen scope; variance = actual − budget."""
    line_qs = budget.lines.all()
    if period_code:
        line_qs = line_qs.filter(period_code=period_code)

    # Planned per account (summed over the scope's periods).
    budget_by_account: dict[str, int] = {}
    for ln in line_qs:
        budget_by_account[ln.account_code] = budget_by_account.get(ln.account_code, 0) + ln.amount_minor

    # Actuals per account over the scope's date range, signed in the account's normal direction.
    start, end = _scope_dates(budget, period_code)
    actual_by_account: dict[str, int] = {}
    if budget_by_account and start and end:
        agg = (
            JournalLine.objects.filter(
                entry__status=EntryStatus.POSTED,
                account__code__in=budget_by_account.keys(),
                entry__date__gte=start, entry__date__lte=end,
            )
            .values("account__code", "account__type")
            .annotate(debit=Sum("debit"), credit=Sum("credit"))
        )
        for r in agg:
            actual_by_account[r["account__code"]] = signed_balance(
                r["account__type"], r["debit"] or 0, r["credit"] or 0
            )

    accounts = {a.code: a for a in Account.objects.filter(code__in=budget_by_account.keys())}
    rows: list[VarianceRow] = []
    total_budget = total_actual = 0
    for code in sorted(budget_by_account):
        budgeted = budget_by_account[code]
        actual = actual_by_account.get(code, 0)
        account = accounts.get(code)
        rows.append(VarianceRow(
            account_code=code,
            account_name=account.name if account else code,
            account_type=account.type if account else "",
            budget_minor=budgeted,
            actual_minor=actual,
            variance_minor=actual - budgeted,
        ))
        total_budget += budgeted
        total_actual += actual

    return BudgetVsActual(
        budget_id=str(budget.id),
        budget_name=budget.name,
        fiscal_year_code=budget.fiscal_year_code,
        period_code=period_code,
        rows=rows,
        total_budget=total_budget,
        total_actual=total_actual,
        total_variance=total_actual - total_budget,
    )
