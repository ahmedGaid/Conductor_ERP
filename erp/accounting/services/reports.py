"""Ledger reports computed from posted journal lines.

The trial balance is the integrity check of double-entry bookkeeping: total debits always equal
total credits. The general ledger lists an account's posted activity with a running balance.
"""
from __future__ import annotations

from dataclasses import dataclass

from django.db.models import Sum

from ..domain.accounts import signed_balance
from ..domain.models import Account, EntryStatus, JournalLine, TaxCode


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


@dataclass
class VatReturn:
    start_date: str
    end_date: str
    output_vat: int        # VAT credited on sales invoices over the range
    reversals: int         # output VAT debited back (sales returns / credit notes)
    input_vat: int         # VAT debited (recoverable) on purchase bills over the range
    input_reversals: int   # input VAT credited back (supplier returns / debit notes)
    net_payable: int       # (output_vat - reversals) - (input_vat - input_reversals)

    @property
    def is_payable(self) -> bool:
        return self.net_payable >= 0


def _vat_movement(accounts: set[str], start_date, end_date) -> tuple[int, int]:
    """(debit, credit) totals on the given GL accounts over the posted range."""
    if not accounts:
        return 0, 0
    qs = (
        JournalLine.objects.filter(entry__status=EntryStatus.POSTED)
        .filter(account__code__in=accounts)
        .filter(entry__date__gte=start_date, entry__date__lte=end_date)
        .aggregate(debit=Sum("debit"), credit=Sum("credit"))
    )
    return qs["debit"] or 0, qs["credit"] or 0


def vat_return(start_date, end_date) -> VatReturn:
    """VAT collected and recovered over a date range, from the tax codes' GL accounts.

    Output VAT = credits to the VAT-output (payable) accounts, less debits (sales returns).
    Input VAT = debits to the VAT-input (recoverable) accounts, less credits (supplier returns).
    The net payable to the authority is net output − net input (negative ⇒ a refund position).
    """
    codes = TaxCode.objects.filter(is_active=True)
    output_accounts = set(codes.values_list("output_account_code", flat=True))
    input_accounts = set(codes.values_list("input_account_code", flat=True))

    out_debit, out_credit = _vat_movement(output_accounts, start_date, end_date)
    # Input accounts are distinct from output accounts; exclude any overlap defensively.
    in_debit, in_credit = _vat_movement(input_accounts - output_accounts, start_date, end_date)

    output_vat, reversals = out_credit, out_debit
    input_vat, input_reversals = in_debit, in_credit
    net_payable = (output_vat - reversals) - (input_vat - input_reversals)
    return VatReturn(
        start_date=str(start_date), end_date=str(end_date),
        output_vat=output_vat, reversals=reversals,
        input_vat=input_vat, input_reversals=input_reversals,
        net_payable=net_payable,
    )


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
