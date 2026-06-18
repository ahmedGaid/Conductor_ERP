"""Accounting ORM models — the General Ledger core.

Chart of Accounts (`Account`), the fiscal calendar (`FiscalYear` / `Period`) used to lock posting,
and double-entry journals (`JournalEntry` + `JournalLine`). Amounts are integer **minor units**
(see domain/money.py) — there is no float anywhere in the ledger.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models

from erp.core.models import AuditedModel, TimeStampedModel

from .accounts import AccountType


class Account(AuditedModel):
    """A Chart-of-Accounts node. Only *postable* accounts may receive journal lines."""

    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=16, choices=AccountType.choices)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="children"
    )
    # Group/header accounts aggregate children and cannot be posted to directly.
    is_postable = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    # Cash/bank accounts — drive the cash-flow statement.
    is_cash = models.BooleanField(default=False)
    currency = models.CharField(max_length=3, default="EGP")

    class Meta:
        db_table = "accounting_account"
        ordering = ["code"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.code} — {self.name}"


class TaxCode(AuditedModel):
    """A VAT/tax code. ``rate_bps`` is basis points (1400 = 14%).

    One rate plus the two GL accounts it touches: **output** (sales) VAT credits a payable, and
    **input** (purchase) VAT debits a recoverable asset. The VAT return nets output minus input.
    Other modules reference a tax code by its string ``code`` via the accounting contract — never
    this ORM model.
    """

    code = models.CharField(max_length=16, unique=True)
    name = models.CharField(max_length=120)
    rate_bps = models.IntegerField(default=0)  # basis points: 1400 == 14.00%
    output_account_code = models.CharField(max_length=32, default="2100")  # VAT Payable (liability)
    input_account_code = models.CharField(max_length=32, default="1190")  # VAT Recoverable (asset)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "accounting_tax_code"
        ordering = ["code"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.code} ({self.rate_bps / 100:.2f}%)"


class AssetStatus(models.TextChoices):
    ACTIVE = "active", "Active"          # in service, depreciating
    DISPOSED = "disposed", "Disposed"    # sold/written off, derecognized


class FixedAsset(AuditedModel):
    """A capitalised fixed asset depreciated straight-line over its useful life.

    Money is integer **minor units**. The GL accounts it touches are referenced by *code*
    (asset/accumulated-depreciation/expense), mirroring how tax codes reference accounts — the
    depreciation run and disposal post through ``post_journal`` like any other entry.
    """

    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=120, blank=True, default="")
    acquisition_date = models.DateField()
    in_service_date = models.DateField()
    cost_minor = models.BigIntegerField()              # capitalised cost
    salvage_minor = models.BigIntegerField(default=0)  # residual value (never depreciated below)
    useful_life_months = models.IntegerField()

    asset_account_code = models.CharField(max_length=32, default="1500")        # Fixed Assets
    accumulated_account_code = models.CharField(max_length=32, default="1590")  # Accum. Depreciation
    expense_account_code = models.CharField(max_length=32, default="5300")      # Depreciation Expense

    accumulated_depreciation_minor = models.BigIntegerField(default=0)
    months_depreciated = models.IntegerField(default=0)
    acquire_journal_number = models.CharField(max_length=32, blank=True, default="")

    status = models.CharField(max_length=16, choices=AssetStatus.choices, default=AssetStatus.ACTIVE)
    disposed_date = models.DateField(null=True, blank=True)
    disposal_proceeds_minor = models.BigIntegerField(null=True, blank=True)
    disposal_gain_loss_minor = models.BigIntegerField(null=True, blank=True)  # +gain / -loss
    disposal_journal_number = models.CharField(max_length=32, blank=True, default="")

    class Meta:
        db_table = "accounting_fixed_asset"
        ordering = ["code"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.code} — {self.name}"

    @property
    def depreciable_minor(self) -> int:
        return self.cost_minor - self.salvage_minor

    @property
    def net_book_value_minor(self) -> int:
        return self.cost_minor - self.accumulated_depreciation_minor


class DepreciationEntry(TimeStampedModel):
    """One posted monthly depreciation charge for an asset. Unique per (asset, period)."""

    asset = models.ForeignKey(FixedAsset, on_delete=models.CASCADE, related_name="depreciation_entries")
    period_code = models.CharField(max_length=16)
    amount_minor = models.BigIntegerField()
    journal_number = models.CharField(max_length=32, blank=True, default="")

    class Meta:
        db_table = "accounting_depreciation_entry"
        ordering = ["asset", "period_code"]
        unique_together = [("asset", "period_code")]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.asset.code} {self.period_code}: {self.amount_minor}"


class CostCenter(AuditedModel):
    """A reporting dimension tagged onto journal lines (department / project / branch unit).

    Optional everywhere: a line with no cost center is untagged, so the dimension is purely additive
    and never disturbs existing posts. Referenced by string ``code`` like accounts and tax codes.
    """

    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "accounting_cost_center"
        ordering = ["code"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.code} — {self.name}"


class BankStatementStatus(models.TextChoices):
    OPEN = "open", "Open"              # being reconciled
    RECONCILED = "reconciled", "Reconciled"  # tied out to the cash GL


class BankStatement(AuditedModel):
    """A bank statement reconciled against a cash/bank GL account.

    Reconciliation matches each statement line to a posted GL line on the same cash account; bank-only
    items (fees/interest) are booked with an adjustment journal. Money is integer minor units.
    """

    account_code = models.CharField(max_length=32)  # the cash/bank GL account (Account.is_cash)
    statement_date = models.DateField()
    opening_balance_minor = models.BigIntegerField(default=0)
    closing_balance_minor = models.BigIntegerField()
    reference = models.CharField(max_length=128, blank=True, default="")
    status = models.CharField(
        max_length=16, choices=BankStatementStatus.choices, default=BankStatementStatus.OPEN
    )

    class Meta:
        db_table = "accounting_bank_statement"
        ordering = ["-statement_date"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.account_code} @ {self.statement_date}"


class BankStatementLine(TimeStampedModel):
    """One line on a bank statement. ``amount_minor`` is signed: + increases cash, − decreases it.

    ``matched_line`` points at the posted GL journal line this reconciles to (null until matched).
    """

    statement = models.ForeignKey(
        BankStatement, on_delete=models.CASCADE, related_name="lines"
    )
    line_no = models.IntegerField()
    date = models.DateField()
    description = models.CharField(max_length=255, blank=True, default="")
    amount_minor = models.BigIntegerField()  # signed: + deposit / − withdrawal
    matched_line = models.ForeignKey(
        "JournalLine", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        db_table = "accounting_bank_statement_line"
        ordering = ["statement", "line_no"]
        unique_together = [("statement", "line_no")]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.statement_id} #{self.line_no}: {self.amount_minor}"

    @property
    def is_matched(self) -> bool:
        return self.matched_line_id is not None


class Budget(AuditedModel):
    """A named budget for one fiscal year. Its lines hold the planned amount per account+period.

    Budget-vs-actual compares these planned amounts to the posted GL. Money is integer minor units.
    """

    name = models.CharField(max_length=200)
    fiscal_year_code = models.CharField(max_length=16)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "accounting_budget"
        ordering = ["fiscal_year_code", "name"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.name} ({self.fiscal_year_code})"


class BudgetLine(TimeStampedModel):
    """A planned amount for one account in one period of the budget's fiscal year."""

    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name="lines")
    account_code = models.CharField(max_length=32)
    period_code = models.CharField(max_length=16)
    amount_minor = models.BigIntegerField(default=0)

    class Meta:
        db_table = "accounting_budget_line"
        ordering = ["budget", "account_code", "period_code"]
        unique_together = [("budget", "account_code", "period_code")]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.account_code} {self.period_code}: {self.amount_minor}"


class ReportGroupBy(models.TextChoices):
    ACCOUNT = "account", "By account"
    PERIOD = "period", "By period"


class ReportSchedule(models.TextChoices):
    NONE = "none", "Not scheduled"
    DAILY = "daily", "Daily"
    WEEKLY = "weekly", "Weekly"
    MONTHLY = "monthly", "Monthly"


class ReportDefinition(AuditedModel):
    """A user-defined GL report: filter posted lines by account type/codes + date range, grouped by
    account or period. Saved, re-runnable, exportable, and optionally scheduled."""

    name = models.CharField(max_length=200)
    account_type = models.CharField(max_length=16, blank=True, default="")   # "" = all types
    account_codes = models.CharField(max_length=500, blank=True, default="")  # comma-separated; "" = all
    date_from = models.DateField(null=True, blank=True)
    date_to = models.DateField(null=True, blank=True)
    group_by = models.CharField(max_length=16, choices=ReportGroupBy.choices, default=ReportGroupBy.ACCOUNT)
    schedule = models.CharField(max_length=16, choices=ReportSchedule.choices, default=ReportSchedule.NONE)
    last_run_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "accounting_report_definition"
        ordering = ["name"]

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class PeriodStatus(models.TextChoices):
    OPEN = "open", "Open"
    CLOSED = "closed", "Closed"


class FiscalYear(TimeStampedModel):
    code = models.CharField(max_length=16, unique=True)
    start_date = models.DateField()
    end_date = models.DateField()
    is_closed = models.BooleanField(default=False)

    class Meta:
        db_table = "accounting_fiscal_year"
        ordering = ["start_date"]

    def __str__(self) -> str:  # pragma: no cover
        return self.code


class Period(TimeStampedModel):
    """An accounting period. Posting is allowed only while the period is OPEN."""

    fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.PROTECT, related_name="periods")
    code = models.CharField(max_length=16, unique=True)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(
        max_length=8, choices=PeriodStatus.choices, default=PeriodStatus.OPEN
    )

    class Meta:
        db_table = "accounting_period"
        ordering = ["start_date"]

    def __str__(self) -> str:  # pragma: no cover
        return self.code

    @property
    def is_open(self) -> bool:
        return self.status == PeriodStatus.OPEN


class EntryStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    POSTED = "posted", "Posted"
    VOID = "void", "Void"


class JournalEntry(AuditedModel):
    """A balanced double-entry transaction. Immutable once posted (reverse, never edit)."""

    number = models.CharField(max_length=32, unique=True)
    date = models.DateField()
    period = models.ForeignKey(Period, on_delete=models.PROTECT, related_name="entries")
    currency = models.CharField(max_length=3, default="EGP")
    memo = models.TextField(blank=True, default="")
    reference = models.CharField(max_length=128, blank=True, default="")
    # Originating module (e.g. "sales", "manual") for traceability.
    source = models.CharField(max_length=32, blank=True, default="manual")
    status = models.CharField(max_length=8, choices=EntryStatus.choices, default=EntryStatus.DRAFT)
    posted_at = models.DateTimeField(null=True, blank=True)
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    # For a reversal entry, points back at the entry it reverses.
    reverses = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="reversed_by"
    )

    class Meta:
        db_table = "accounting_journal_entry"
        ordering = ["-date", "number"]
        indexes = [models.Index(fields=["status"]), models.Index(fields=["period"])]

    def __str__(self) -> str:  # pragma: no cover
        return self.number


class JournalLine(models.Model):
    """One side of a journal entry. Exactly one of debit/credit is > 0 (the other is 0)."""

    id = models.BigAutoField(primary_key=True)
    entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name="lines")
    line_no = models.IntegerField()
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="+")
    debit = models.BigIntegerField(default=0)  # minor units
    credit = models.BigIntegerField(default=0)  # minor units
    memo = models.CharField(max_length=255, blank=True, default="")
    # Optional reporting dimension (department/project). Blank ⇒ untagged.
    cost_center_code = models.CharField(max_length=32, blank=True, default="")

    class Meta:
        db_table = "accounting_journal_line"
        ordering = ["entry", "line_no"]
        unique_together = [("entry", "line_no")]
        indexes = [models.Index(fields=["account"])]
        constraints = [
            models.CheckConstraint(
                check=models.Q(debit__gte=0) & models.Q(credit__gte=0),
                name="acct_line_amounts_non_negative",
            ),
            # A line is either a debit or a credit, never both.
            models.CheckConstraint(
                check=~(models.Q(debit__gt=0) & models.Q(credit__gt=0)),
                name="acct_line_not_both_sides",
            ),
        ]
