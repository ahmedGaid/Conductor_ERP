"""Journal posting — the double-entry invariant enforcement point.

`post_journal` is the single sanctioned way money enters the ledger. It validates the entry
(balanced, valid lines, postable accounts, open period), writes the entry + lines atomically,
stamps it posted, records an immutable audit row, and publishes ``accounting.JournalPosted``.
Either the whole entry posts or nothing is written.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from django.db import transaction
from django.utils import timezone

from erp.audit import services as audit
from erp.core.events import bus

from .. import events
from ..domain.models import (
    Account,
    EntryStatus,
    JournalEntry,
    JournalLine,
    Period,
)
from ..errors import (
    AlreadyPostedError,
    ClosedPeriodError,
    InvalidLineError,
    NoPeriodError,
    NonPostableAccountError,
    UnbalancedEntryError,
)
from ..repositories import accounts as account_repo
from ..repositories import periods as period_repo


@dataclass
class LineInput:
    """One requested journal line. Amounts are integer minor units; exactly one side is > 0."""

    account_code: str
    debit: int = 0
    credit: int = 0
    memo: str = ""


@dataclass
class JournalInput:
    date: object  # datetime.date
    lines: list[LineInput]
    memo: str = ""
    reference: str = ""
    source: str = "manual"
    currency: str = "EGP"
    number: str | None = None
    period_code: str | None = None
    extra: dict = field(default_factory=dict)


def _next_number() -> str:
    """Sequential human-readable entry number, e.g. JE-2026-000123."""
    year = timezone.now().year
    prefix = f"JE-{year}-"
    last = (
        JournalEntry.objects.filter(number__startswith=prefix)
        .order_by("-number")
        .values_list("number", flat=True)
        .first()
    )
    seq = (int(last.rsplit("-", 1)[1]) + 1) if last else 1
    return f"{prefix}{seq:06d}"


def _resolve_period(data: JournalInput) -> Period:
    if data.period_code:
        period = period_repo.by_code(data.period_code)
    else:
        period = period_repo.containing(data.date)
    if period is None:
        raise NoPeriodError(data={"date": str(data.date)})
    if not period.is_open:
        raise ClosedPeriodError(data={"period": period.code})
    return period


def _validate_and_load_accounts(data: JournalInput) -> dict[str, Account]:
    if len(data.lines) < 2:
        raise InvalidLineError("a journal entry needs at least two lines")

    total_debit = 0
    total_credit = 0
    resolved: dict[str, Account] = {}
    for i, line in enumerate(data.lines, start=1):
        if line.debit < 0 or line.credit < 0:
            raise InvalidLineError(f"line {i}: amounts cannot be negative")
        if (line.debit > 0) == (line.credit > 0):
            raise InvalidLineError(
                f"line {i}: exactly one of debit/credit must be > 0"
            )
        if line.account_code not in resolved:
            account = account_repo.by_code(line.account_code)
            if account is None:
                raise InvalidLineError(f"line {i}: unknown account {line.account_code!r}")
            if not (account.is_postable and account.is_active):
                raise NonPostableAccountError(data={"account": line.account_code})
            resolved[line.account_code] = account
        total_debit += line.debit
        total_credit += line.credit

    if total_debit != total_credit:
        raise UnbalancedEntryError(
            data={"total_debit": total_debit, "total_credit": total_credit}
        )
    if total_debit == 0:
        raise UnbalancedEntryError("entry total is zero")
    return resolved


@transaction.atomic
def post_journal(data: JournalInput, actor=None) -> JournalEntry:
    """Validate and post a balanced double-entry journal. All-or-nothing."""
    period = _resolve_period(data)
    resolved_accounts = _validate_and_load_accounts(data)

    entry = JournalEntry.objects.create(
        number=data.number or _next_number(),
        date=data.date,
        period=period,
        currency=data.currency,
        memo=data.memo,
        reference=data.reference,
        source=data.source,
        status=EntryStatus.POSTED,
        posted_at=timezone.now(),
        posted_by=actor if getattr(actor, "is_authenticated", False) else None,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
    )
    JournalLine.objects.bulk_create(
        [
            JournalLine(
                entry=entry,
                line_no=i,
                account=resolved_accounts[line.account_code],
                debit=line.debit,
                credit=line.credit,
                memo=line.memo,
            )
            for i, line in enumerate(data.lines, start=1)
        ]
    )

    audit.record(
        module="accounting",
        action="post_journal",
        entity_type="JournalEntry",
        entity_id=entry.number,
        actor=actor,
        after={
            "number": entry.number,
            "date": str(entry.date),
            "period": period.code,
            "lines": len(data.lines),
            "total": sum(line.debit for line in data.lines),
            "currency": entry.currency,
        },
    )
    bus.publish(
        events.JOURNAL_POSTED,
        {"entry_id": str(entry.id), "number": entry.number, "period": period.code},
    )
    return entry


@transaction.atomic
def reverse_journal(entry: JournalEntry, actor=None, date=None) -> JournalEntry:
    """Post the mirror-image of a posted entry (the only correct way to undo one)."""
    if entry.status != EntryStatus.POSTED:
        raise AlreadyPostedError("only a posted entry can be reversed")
    lines = [
        LineInput(
            account_code=line.account.code,
            debit=line.credit,  # swap sides
            credit=line.debit,
            memo=line.memo,
        )
        for line in entry.lines.select_related("account").order_by("line_no")
    ]
    reversal_input = JournalInput(
        date=date or entry.date,
        lines=lines,
        memo=f"Reversal of {entry.number}",
        reference=entry.number,
        source=entry.source,
        currency=entry.currency,
        period_code=None,
    )
    reversal = post_journal(reversal_input, actor=actor)
    reversal.reverses = entry
    reversal.save(update_fields=["reverses"])
    return reversal
