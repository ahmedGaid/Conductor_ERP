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
    currency = models.CharField(max_length=3, default="EGP")

    class Meta:
        db_table = "accounting_account"
        ordering = ["code"]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.code} — {self.name}"


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
