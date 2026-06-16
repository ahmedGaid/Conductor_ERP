"""Budgets — planned amounts vs the posted GL. Variance = actual − budget, and the totals tie out."""
from __future__ import annotations

import datetime as dt

import pytest

from erp.accounting.domain.accounts import AccountType
from erp.accounting.domain.models import Account
from erp.accounting.errors import InvalidBudgetError
from erp.accounting.services import (
    BudgetLineInput,
    JournalInput,
    LineInput,
    budget_vs_actual,
    create_budget,
    post_journal,
    set_budget_line,
    set_budget_lines,
)

from .factories import make_period

pytestmark = pytest.mark.django_db


def _seed():
    Account.objects.create(code="1000", name="Cash", type=AccountType.ASSET)
    Account.objects.create(code="4000", name="Sales", type=AccountType.INCOME)
    Account.objects.create(code="5100", name="Rent", type=AccountType.EXPENSE)
    # FiscalYear 2026 + period 2026-06 via the factory.
    make_period("2026-06")


def _post(lines, date=dt.date(2026, 6, 15)):
    return post_journal(JournalInput(date=date, lines=lines))


def test_create_budget_requires_known_fiscal_year():
    _seed()
    with pytest.raises(InvalidBudgetError):
        create_budget(name="2099 plan", fiscal_year_code="2099")


def test_variance_is_actual_minus_budget_and_totals_tie_out():
    _seed()
    budget = create_budget(name="2026 plan", fiscal_year_code="2026")
    set_budget_lines(budget, [
        BudgetLineInput("4000", "2026-06", 1_000_00),  # plan to earn 1,000
        BudgetLineInput("5100", "2026-06", 300_00),    # plan to spend 300
    ])
    # Actuals: earned 1,200 (over plan), spent 250 (under plan).
    _post([LineInput("1000", debit=1_200_00), LineInput("4000", credit=1_200_00)])
    _post([LineInput("5100", debit=250_00), LineInput("1000", credit=250_00)])

    bva = budget_vs_actual(budget, period_code="2026-06")
    by_code = {r.account_code: r for r in bva.rows}
    assert by_code["4000"].budget_minor == 1_000_00
    assert by_code["4000"].actual_minor == 1_200_00
    assert by_code["4000"].variance_minor == 200_00       # income over plan
    assert by_code["5100"].actual_minor == 250_00
    assert by_code["5100"].variance_minor == -50_00       # expense under plan

    # Totals tie out: Σ variance == total_actual − total_budget.
    assert bva.total_variance == bva.total_actual - bva.total_budget
    assert bva.total_budget == 1_300_00
    assert bva.total_actual == 1_450_00


def test_zero_amount_removes_line():
    _seed()
    budget = create_budget(name="b", fiscal_year_code="2026")
    set_budget_line(budget, "4000", "2026-06", 500_00)
    assert budget.lines.count() == 1
    set_budget_line(budget, "4000", "2026-06", 0)
    assert budget.lines.count() == 0


def test_budgeted_account_with_no_actuals_shows_zero():
    _seed()
    budget = create_budget(name="b", fiscal_year_code="2026")
    set_budget_line(budget, "5100", "2026-06", 400_00)
    bva = budget_vs_actual(budget, period_code="2026-06")
    row = bva.rows[0]
    assert row.actual_minor == 0
    assert row.variance_minor == -400_00


def test_whole_year_scope_sums_all_periods():
    from erp.accounting.domain.models import FiscalYear, Period
    _seed()
    fy = FiscalYear.objects.get(code="2026")
    Period.objects.create(fiscal_year=fy, code="2026-07", start_date=dt.date(2026, 7, 1),
                          end_date=dt.date(2026, 7, 31), status="open")
    budget = create_budget(name="b", fiscal_year_code="2026")
    set_budget_lines(budget, [
        BudgetLineInput("4000", "2026-06", 1_000_00),
        BudgetLineInput("4000", "2026-07", 1_000_00),
    ])
    _post([LineInput("1000", debit=900_00), LineInput("4000", credit=900_00)], date=dt.date(2026, 6, 15))
    _post([LineInput("1000", debit=1_100_00), LineInput("4000", credit=1_100_00)], date=dt.date(2026, 7, 15))
    bva = budget_vs_actual(budget)  # no period → whole fiscal year
    row = {r.account_code: r for r in bva.rows}["4000"]
    assert row.budget_minor == 2_000_00
    assert row.actual_minor == 2_000_00
    assert row.variance_minor == 0
