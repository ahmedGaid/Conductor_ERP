"""Ledger reports computed from posted journal lines.

The trial balance is the integrity check of double-entry bookkeeping: total debits always equal
total credits. The general ledger lists an account's posted activity with a running balance.
"""
from __future__ import annotations

from dataclasses import dataclass

from django.db.models import Sum

from ..domain.accounts import signed_balance
from ..domain.models import Account, EntryStatus, JournalLine


@dataclass
class TrialBalanceRow:
    account_code: str
    account_name: str
    account_type: str
    debit: int
    credit: int
    balance: int  # signed in the account's normal direction


@dataclass
class TrialBalance:
    rows: list[TrialBalanceRow]
    total_debit: int
    total_credit: int

    @property
    def is_balanced(self) -> bool:
        return self.total_debit == self.total_credit


def _posted_lines(*, period_code: str | None = None, as_of=None):
    qs = JournalLine.objects.filter(entry__status=EntryStatus.POSTED)
    if period_code:
        qs = qs.filter(entry__period__code=period_code)
    if as_of:
        qs = qs.filter(entry__date__lte=as_of)
    return qs


def trial_balance(*, period_code: str | None = None, as_of=None) -> TrialBalance:
    """Debit/credit totals and signed balance per account over posted lines."""
    agg = (
        _posted_lines(period_code=period_code, as_of=as_of)
        .values("account__code", "account__name", "account__type")
        .annotate(debit=Sum("debit"), credit=Sum("credit"))
        .order_by("account__code")
    )
    rows: list[TrialBalanceRow] = []
    total_debit = 0
    total_credit = 0
    for r in agg:
        debit = r["debit"] or 0
        credit = r["credit"] or 0
        if debit == 0 and credit == 0:
            continue
        rows.append(
            TrialBalanceRow(
                account_code=r["account__code"],
                account_name=r["account__name"],
                account_type=r["account__type"],
                debit=debit,
                credit=credit,
                balance=signed_balance(r["account__type"], debit, credit),
            )
        )
        total_debit += debit
        total_credit += credit
    return TrialBalance(rows=rows, total_debit=total_debit, total_credit=total_credit)


@dataclass
class LedgerLine:
    date: str
    entry_number: str
    memo: str
    debit: int
    credit: int
    running_balance: int


@dataclass
class GeneralLedger:
    account_code: str
    account_name: str
    account_type: str
    opening_balance: int
    lines: list[LedgerLine]
    closing_balance: int


def general_ledger(account_code: str, *, period_code: str | None = None) -> GeneralLedger:
    """Posted activity for one account with a running, normal-direction balance."""
    account = Account.objects.get(code=account_code)
    qs = (
        _posted_lines(period_code=period_code)
        .filter(account=account)
        .select_related("entry")
        .order_by("entry__date", "entry__number", "line_no")
    )
    running = 0
    lines: list[LedgerLine] = []
    for line in qs:
        running += signed_balance(account.type, line.debit, line.credit)
        lines.append(
            LedgerLine(
                date=str(line.entry.date),
                entry_number=line.entry.number,
                memo=line.memo or line.entry.memo,
                debit=line.debit,
                credit=line.credit,
                running_balance=running,
            )
        )
    return GeneralLedger(
        account_code=account.code,
        account_name=account.name,
        account_type=account.type,
        opening_balance=0,
        lines=lines,
        closing_balance=running,
    )
