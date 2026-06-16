"""Bank reconciliation — matching statement lines to the cash GL, adjustments, and tie-out.

A fully-matched statement (with bank-only items booked as adjustments) must reconcile exactly to the
cash GL balance; every adjustment posts a balanced journal.
"""
from __future__ import annotations

import datetime as dt

import pytest

from erp.accounting.domain.accounts import AccountType
from erp.accounting.domain.models import Account, BankStatementStatus
from erp.accounting.errors import BankMatchError, NotACashAccountError, NotReconciledError
from erp.accounting.services import (
    BankLineInput,
    JournalInput,
    LineInput,
    auto_match,
    create_statement,
    mark_reconciled,
    post_adjustment,
    post_journal,
    reconciliation,
    trial_balance,
)

from .factories import make_period

pytestmark = pytest.mark.django_db

D = dt.date(2026, 6, 30)


def _seed():
    Account.objects.create(code="1010", name="Bank", type=AccountType.ASSET, is_cash=True)
    Account.objects.create(code="3000", name="Capital", type=AccountType.EQUITY)
    Account.objects.create(code="4000", name="Sales", type=AccountType.INCOME)
    Account.objects.create(code="6100", name="Bank Charges", type=AccountType.EXPENSE)
    Account.objects.create(code="4100", name="Interest Income", type=AccountType.INCOME)
    make_period("2026-06")


def _post(lines, date=dt.date(2026, 6, 10)):
    return post_journal(JournalInput(date=date, lines=lines))


def test_create_statement_requires_cash_account():
    _seed()
    with pytest.raises(NotACashAccountError):
        create_statement(account_code="4000", statement_date=D, closing_balance_minor=0)


def test_auto_match_and_reconcile_to_cash_gl():
    _seed()
    # Two cash movements in the books: +10,000 capital, +400 sale.
    _post([LineInput("1010", debit=10_000_00), LineInput("3000", credit=10_000_00)])
    _post([LineInput("1010", debit=400_00), LineInput("4000", credit=400_00)])

    stmt = create_statement(
        account_code="1010", statement_date=D, closing_balance_minor=10_400_00,
        lines=[
            BankLineInput(date=dt.date(2026, 6, 10), amount_minor=10_000_00, description="Capital"),
            BankLineInput(date=dt.date(2026, 6, 10), amount_minor=400_00, description="Sale"),
        ],
    )
    assert auto_match(stmt) == 2
    rec = reconciliation(stmt)
    assert rec.book_balance == 10_400_00
    assert rec.statement_closing == 10_400_00
    assert rec.difference == 0
    assert rec.unmatched_statement == []
    assert rec.unmatched_book == []
    assert rec.is_reconciled is True

    mark_reconciled(stmt)
    stmt.refresh_from_db()
    assert stmt.status == BankStatementStatus.RECONCILED


def test_bank_only_fee_handled_by_adjustment():
    _seed()
    _post([LineInput("1010", debit=10_000_00), LineInput("3000", credit=10_000_00)])

    # Statement shows the deposit AND a bank fee of 50.00 not yet in the books.
    stmt = create_statement(
        account_code="1010", statement_date=D, closing_balance_minor=9_950_00,
        lines=[
            BankLineInput(date=dt.date(2026, 6, 10), amount_minor=10_000_00, description="Capital"),
            BankLineInput(date=dt.date(2026, 6, 30), amount_minor=-50_00, description="Bank fee"),
        ],
    )
    auto_match(stmt)  # matches only the deposit; the fee has no GL line yet
    assert reconciliation(stmt).is_reconciled is False

    # Book the fee → creates a cash GL line that auto-matches the bank-only statement line.
    post_adjustment(stmt, amount_minor=-50_00, contra_account_code="6100", memo="Monthly fee")
    rec = reconciliation(stmt)
    assert rec.book_balance == 9_950_00
    assert rec.is_reconciled is True
    assert trial_balance().is_balanced


def test_interest_adjustment_increases_cash():
    _seed()
    _post([LineInput("1010", debit=1_000_00), LineInput("3000", credit=1_000_00)])
    stmt = create_statement(
        account_code="1010", statement_date=D, closing_balance_minor=1_005_00,
        lines=[
            BankLineInput(date=dt.date(2026, 6, 10), amount_minor=1_000_00, description="Capital"),
            BankLineInput(date=dt.date(2026, 6, 30), amount_minor=5_00, description="Interest"),
        ],
    )
    auto_match(stmt)
    post_adjustment(stmt, amount_minor=5_00, contra_account_code="4100", memo="Interest earned")
    rec = reconciliation(stmt)
    assert rec.book_balance == 1_005_00
    assert rec.is_reconciled is True
    assert trial_balance().is_balanced


def test_outstanding_book_item_blocks_reconcile():
    _seed()
    # Book has two deposits but the statement only shows one (the other is in transit).
    _post([LineInput("1010", debit=500_00), LineInput("4000", credit=500_00)])
    _post([LineInput("1010", debit=300_00), LineInput("4000", credit=300_00)])
    stmt = create_statement(
        account_code="1010", statement_date=D, closing_balance_minor=500_00,
        lines=[BankLineInput(date=dt.date(2026, 6, 10), amount_minor=500_00)],
    )
    auto_match(stmt)
    rec = reconciliation(stmt)
    assert rec.book_balance == 800_00
    assert rec.difference == 500_00 - 800_00
    assert len(rec.unmatched_book) == 1   # the in-transit deposit
    assert rec.is_reconciled is False
    with pytest.raises(NotReconciledError):
        mark_reconciled(stmt)


def test_manual_match_rejects_amount_mismatch():
    _seed()
    entry = _post([LineInput("1010", debit=200_00), LineInput("4000", credit=200_00)])
    gl_cash = entry.lines.get(account__code="1010")
    stmt = create_statement(
        account_code="1010", statement_date=D, closing_balance_minor=200_00,
        lines=[BankLineInput(date=dt.date(2026, 6, 10), amount_minor=999_00)],
    )
    from erp.accounting.services import match_line
    with pytest.raises(BankMatchError):
        match_line(stmt.lines.first(), gl_cash)
