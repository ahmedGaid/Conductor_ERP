"""Chart-of-accounts classification and the normal-balance rule.

The five account types and their *normal balance* side drive every report sign convention:
assets and expenses increase on the debit side; liabilities, equity and income on the credit side.
"""
from __future__ import annotations

from django.db import models


class AccountType(models.TextChoices):
    ASSET = "asset", "Asset"
    LIABILITY = "liability", "Liability"
    EQUITY = "equity", "Equity"
    INCOME = "income", "Income"
    EXPENSE = "expense", "Expense"


# Side on which the account's balance naturally increases.
DEBIT = "debit"
CREDIT = "credit"

_NORMAL_BALANCE: dict[str, str] = {
    AccountType.ASSET: DEBIT,
    AccountType.EXPENSE: DEBIT,
    AccountType.LIABILITY: CREDIT,
    AccountType.EQUITY: CREDIT,
    AccountType.INCOME: CREDIT,
}


def normal_balance(account_type: str) -> str:
    """Return 'debit' or 'credit' — the side this account type increases on."""
    return _NORMAL_BALANCE[account_type]


def signed_balance(account_type: str, debit_minor: int, credit_minor: int) -> int:
    """Account balance in minor units, signed positive in the type's normal direction.

    For a debit-normal account: debit - credit. For a credit-normal account: credit - debit.
    """
    if normal_balance(account_type) == DEBIT:
        return debit_minor - credit_minor
    return credit_minor - debit_minor
