"""Trial balance + general ledger reporting."""
from __future__ import annotations

import datetime as dt

import pytest

from erp.accounting.services import JournalInput, LineInput, general_ledger, post_journal, trial_balance

from .factories import make_coa, make_period

pytestmark = pytest.mark.django_db

DATE = dt.date(2026, 6, 15)


def _post(lines, **kw):
    return post_journal(JournalInput(date=DATE, lines=lines, **kw))


def _seed_activity():
    make_coa()
    make_period()
    # Capital injection: Dr Cash 1,000.00 / Cr Capital 1,000.00
    _post([LineInput("1000", debit=1000_00), LineInput("3000", credit=1000_00)])
    # Sale on credit: Dr AR 300.00 / Cr Sales 300.00
    _post([LineInput("1100", debit=300_00), LineInput("4000", credit=300_00)])
    # Pay rent in cash: Dr Rent 200.00 / Cr Cash 200.00
    _post([LineInput("5100", debit=200_00), LineInput("1000", credit=200_00)])


def test_trial_balance_always_balances():
    _seed_activity()
    tb = trial_balance()
    assert tb.is_balanced
    assert tb.total_debit == tb.total_credit
    assert tb.total_debit == 1000_00 + 300_00 + 200_00


def test_trial_balance_account_balances_are_signed_by_type():
    _seed_activity()
    by_code = {r.account_code: r for r in trial_balance().rows}
    # Cash (asset, debit-normal): 1000 in - 200 out = 800 debit balance
    assert by_code["1000"].balance == 800_00
    # Sales (income, credit-normal): 300 credit balance, positive
    assert by_code["4000"].balance == 300_00
    # Rent (expense, debit-normal): 200 debit balance, positive
    assert by_code["5100"].balance == 200_00


def test_general_ledger_running_balance():
    _seed_activity()
    gl = general_ledger("1000")  # Cash
    assert gl.account_code == "1000"
    assert [ln.running_balance for ln in gl.lines] == [1000_00, 800_00]
    assert gl.closing_balance == 800_00


def test_trial_balance_excludes_zero_activity_accounts():
    make_coa()
    make_period()
    _post([LineInput("1000", debit=10_00), LineInput("3000", credit=10_00)])
    codes = {r.account_code for r in trial_balance().rows}
    assert codes == {"1000", "3000"}
