"""Cost centers — an optional reporting dimension on journal lines.

The dimension must be purely additive: posting with a cost center still balances, untagged posting is
unchanged, and the per-cost-center P&L slices sum back to the un-dimensioned income statement.
"""
from __future__ import annotations

import datetime as dt

import pytest

from erp.accounting.domain.accounts import AccountType
from erp.accounting.domain.models import Account, CostCenter
from erp.accounting.errors import UnknownCostCenterError
from erp.accounting.services import (
    JournalInput,
    LineInput,
    income_statement,
    post_journal,
    trial_balance,
)

from .factories import make_period

pytestmark = pytest.mark.django_db

D = dt.date(2026, 6, 10)


def _seed():
    for code, name, type_ in [
        ("1000", "Cash", AccountType.ASSET),
        ("4000", "Sales Revenue", AccountType.INCOME),
        ("5100", "Rent Expense", AccountType.EXPENSE),
    ]:
        Account.objects.create(code=code, name=name, type=type_)
    CostCenter.objects.create(code="CC-A", name="Dept A")
    CostCenter.objects.create(code="CC-B", name="Dept B")
    make_period("2026-06")


def _sale(amount, cc=""):
    return post_journal(JournalInput(date=D, lines=[
        LineInput("1000", debit=amount),
        LineInput("4000", credit=amount, cost_center_code=cc),
    ]))


def test_posting_with_dimension_balances_and_persists():
    _seed()
    entry = _sale(1_000_00, cc="CC-A")
    line = entry.lines.get(account__code="4000")
    assert line.cost_center_code == "CC-A"
    assert trial_balance().is_balanced


def test_unknown_cost_center_rejected():
    _seed()
    with pytest.raises(UnknownCostCenterError):
        _sale(500_00, cc="CC-NOPE")
    # nothing written
    assert trial_balance().total_debit == 0


def test_dimensional_pl_sums_to_total():
    _seed()
    _sale(1_000_00, cc="CC-A")
    _sale(600_00, cc="CC-B")
    _sale(400_00, cc="")  # untagged

    total = income_statement().total_revenue
    a = income_statement(cost_center="CC-A").total_revenue
    b = income_statement(cost_center="CC-B").total_revenue
    assert total == 2_000_00
    assert a == 1_000_00
    assert b == 600_00
    # The slices (incl. the untagged remainder) reconcile to the whole.
    untagged = total - a - b
    assert untagged == 400_00


def test_untagged_posting_unchanged():
    _seed()
    _sale(750_00)  # no cost center
    line = post_journal(JournalInput(date=D, lines=[
        LineInput("5100", debit=100_00),
        LineInput("1000", credit=100_00),
    ])).lines.first()
    assert line.cost_center_code == ""
    assert trial_balance().is_balanced
