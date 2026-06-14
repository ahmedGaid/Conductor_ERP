"""Test helpers: a minimal Chart of Accounts and an open period."""
from __future__ import annotations

import datetime as dt

from erp.accounting.domain.accounts import AccountType
from erp.accounting.domain.models import Account, FiscalYear, Period, PeriodStatus

ACCOUNTS = [
    ("1000", "Cash", AccountType.ASSET),
    ("1100", "Accounts Receivable", AccountType.ASSET),
    ("2000", "Accounts Payable", AccountType.LIABILITY),
    ("3000", "Share Capital", AccountType.EQUITY),
    ("4000", "Sales Revenue", AccountType.INCOME),
    ("5100", "Rent Expense", AccountType.EXPENSE),
]


def make_coa() -> dict[str, Account]:
    out: dict[str, Account] = {}
    for code, name, type_ in ACCOUNTS:
        out[code] = Account.objects.create(code=code, name=name, type=type_)
    # a non-postable group account for the "reject non-postable" test
    out["GRP"] = Account.objects.create(
        code="9", name="Group", type=AccountType.ASSET, is_postable=False
    )
    return out


def make_period(code: str = "2026-06", status: str = PeriodStatus.OPEN) -> Period:
    fy, _ = FiscalYear.objects.get_or_create(
        code="2026",
        defaults={"start_date": dt.date(2026, 1, 1), "end_date": dt.date(2026, 12, 31)},
    )
    return Period.objects.create(
        fiscal_year=fy,
        code=code,
        start_date=dt.date(2026, 6, 1),
        end_date=dt.date(2026, 6, 30),
        status=status,
    )
