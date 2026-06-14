"""Data-access boundary for accounting. Business logic uses these, never the ORM directly."""
from __future__ import annotations

from erp.core.repository import Repository

from ..domain.models import Account, FiscalYear, JournalEntry, Period


class AccountRepository(Repository[Account]):
    model = Account

    def by_code(self, code: str) -> Account | None:
        return self.model._default_manager.filter(code=code).first()

    def postable_active(self):
        return self.model._default_manager.filter(is_postable=True, is_active=True)


class PeriodRepository(Repository[Period]):
    model = Period

    def by_code(self, code: str) -> Period | None:
        return self.model._default_manager.filter(code=code).first()

    def containing(self, on_date) -> Period | None:
        return (
            self.model._default_manager.filter(start_date__lte=on_date, end_date__gte=on_date)
            .order_by("start_date")
            .first()
        )


class JournalRepository(Repository[JournalEntry]):
    model = JournalEntry


class FiscalYearRepository(Repository[FiscalYear]):
    model = FiscalYear


accounts = AccountRepository()
periods = PeriodRepository()
journals = JournalRepository()
fiscal_years = FiscalYearRepository()
