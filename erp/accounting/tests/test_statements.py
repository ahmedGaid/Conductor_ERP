"""Financial statements — income statement, balance sheet (must balance), cash flow (reconciles)."""
from __future__ import annotations

import datetime as dt

import pytest

from erp.accounting.domain.models import Account
from erp.accounting.services import (
    JournalInput,
    LineInput,
    balance_sheet,
    cash_flow,
    income_statement,
    post_journal,
)

from .factories import make_coa, make_period

pytestmark = pytest.mark.django_db

D1 = dt.date(2026, 6, 10)
D2 = dt.date(2026, 6, 20)


def _post(lines, date=D1, **kw):
    return post_journal(JournalInput(date=date, lines=lines, **kw))


def _seed():
    make_coa()
    make_period()
    Account.objects.filter(code="1000").update(is_cash=True)  # Cash is a cash account
    # Capital injection: Dr Cash 1,000 / Cr Capital 1,000
    _post([LineInput("1000", debit=1000_00), LineInput("3000", credit=1000_00)], date=D1)
    # Cash sale: Dr Cash 400 / Cr Sales 400
    _post([LineInput("1000", debit=400_00), LineInput("4000", credit=400_00)], date=D2)
    # Pay rent: Dr Rent 250 / Cr Cash 250
    _post([LineInput("5100", debit=250_00), LineInput("1000", credit=250_00)], date=D2)


def test_income_statement_net_income():
    _seed()
    st = income_statement()
    assert st.total_revenue == 400_00
    assert st.total_expenses == 250_00
    assert st.net_income == 150_00


def test_income_statement_respects_date_range():
    _seed()
    # Only D1 activity: capital injection has no income/expense → zero P&L
    st = income_statement(date_from=D1, date_to=D1)
    assert st.total_revenue == 0
    assert st.net_income == 0


def test_balance_sheet_always_balances():
    _seed()
    bs = balance_sheet()
    assert bs.is_balanced
    assert bs.total_assets == bs.total_liabilities_and_equity
    # Assets: Cash 1000+400-250 = 1150 ; Equity capital 1000 + net income 150 = 1150
    assert bs.total_assets == 1150_00
    assert bs.total_equity == 1000_00
    assert bs.net_income == 150_00


def test_balance_sheet_balances_with_a_liability():
    make_coa()
    make_period()
    # Buy on credit: Dr Cash 500 / Cr AP 500  -> assets 500 = liabilities 500
    _post([LineInput("1000", debit=500_00), LineInput("2000", credit=500_00)])
    bs = balance_sheet()
    assert bs.is_balanced
    assert bs.total_assets == 500_00
    assert bs.total_liabilities == 500_00


def test_cash_flow_reconciles_to_gl():
    _seed()
    cf = cash_flow(date_from=D2, date_to=D2)
    # Opening (before D2) = 1000 from the capital injection
    assert cf.opening_balance == 1000_00
    assert cf.cash_in == 400_00
    assert cf.cash_out == 250_00
    assert cf.net_change == 150_00
    assert cf.closing_balance == 1150_00
    assert cf.reconciles  # matches the cash GL balance as of date_to


def test_cash_flow_full_range_opens_at_zero():
    _seed()
    cf = cash_flow()
    assert cf.opening_balance == 0
    assert cf.closing_balance == 1150_00
    assert cf.reconciles
