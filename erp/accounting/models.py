"""Django discovers models here; the definitions live in the domain layer.

Re-exported so the app's models module (`erp.accounting.models`) resolves for migrations/admin
while the strict module layout keeps the ORM models under `domain/`.
"""
from __future__ import annotations

from .domain.models import (  # noqa: F401
    Account,
    EntryStatus,
    FiscalYear,
    JournalEntry,
    JournalLine,
    Period,
    PeriodStatus,
)

__all__ = [
    "Account",
    "EntryStatus",
    "FiscalYear",
    "JournalEntry",
    "JournalLine",
    "Period",
    "PeriodStatus",
]
