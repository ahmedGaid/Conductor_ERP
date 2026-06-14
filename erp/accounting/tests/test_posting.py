"""Double-entry posting invariants — the accounting module's acceptance criteria."""
from __future__ import annotations

import datetime as dt

import pytest

from erp.accounting.domain.models import EntryStatus, JournalEntry, JournalLine
from erp.accounting.errors import (
    ClosedPeriodError,
    InvalidLineError,
    NonPostableAccountError,
    UnbalancedEntryError,
)
from erp.accounting.services import JournalInput, LineInput, post_journal, reverse_journal

from .factories import make_coa, make_period

pytestmark = pytest.mark.django_db

DATE = dt.date(2026, 6, 15)


def _entry(lines, **kw) -> JournalInput:
    return JournalInput(date=DATE, lines=lines, **kw)


def test_balanced_entry_posts_atomically():
    make_coa()
    make_period()
    entry = post_journal(
        _entry(
            [
                LineInput("1000", debit=100_00),
                LineInput("3000", credit=100_00),
            ],
            memo="Owner funds the company",
        )
    )
    assert entry.status == EntryStatus.POSTED
    assert entry.posted_at is not None
    assert entry.number.startswith("JE-")
    assert JournalLine.objects.filter(entry=entry).count() == 2


def test_unbalanced_entry_is_rejected_and_writes_nothing():
    make_coa()
    make_period()
    with pytest.raises(UnbalancedEntryError):
        post_journal(
            _entry(
                [
                    LineInput("1000", debit=100_00),
                    LineInput("3000", credit=90_00),
                ]
            )
        )
    # Atomicity: no partial entry/lines persisted.
    assert JournalEntry.objects.count() == 0
    assert JournalLine.objects.count() == 0


def test_line_with_both_sides_is_rejected():
    make_coa()
    make_period()
    with pytest.raises(InvalidLineError):
        post_journal(
            _entry(
                [
                    LineInput("1000", debit=50_00, credit=50_00),
                    LineInput("3000", credit=50_00),
                ]
            )
        )
    assert JournalEntry.objects.count() == 0


def test_single_line_entry_is_rejected():
    make_coa()
    make_period()
    with pytest.raises(InvalidLineError):
        post_journal(_entry([LineInput("1000", debit=100_00)]))


def test_posting_to_closed_period_is_rejected():
    make_coa()
    make_period(status="closed")
    with pytest.raises(ClosedPeriodError):
        post_journal(
            _entry(
                [
                    LineInput("1000", debit=100_00),
                    LineInput("3000", credit=100_00),
                ]
            )
        )
    assert JournalEntry.objects.count() == 0


def test_posting_to_non_postable_account_is_rejected():
    make_coa()
    make_period()
    with pytest.raises(NonPostableAccountError):
        post_journal(
            _entry(
                [
                    LineInput("9", debit=100_00),  # group account
                    LineInput("3000", credit=100_00),
                ]
            )
        )


def test_entry_numbers_are_sequential():
    make_coa()
    make_period()
    e1 = post_journal(_entry([LineInput("1000", debit=1_00), LineInput("3000", credit=1_00)]))
    e2 = post_journal(_entry([LineInput("1000", debit=2_00), LineInput("3000", credit=2_00)]))
    assert e1.number != e2.number
    assert int(e2.number.rsplit("-", 1)[1]) == int(e1.number.rsplit("-", 1)[1]) + 1


def test_reversal_mirrors_the_original():
    make_coa()
    make_period()
    original = post_journal(
        _entry([LineInput("1000", debit=100_00), LineInput("3000", credit=100_00)])
    )
    reversal = reverse_journal(original)
    assert reversal.reverses_id == original.id
    orig_lines = {(l.account.code, l.debit, l.credit) for l in original.lines.all()}
    rev_lines = {(l.account.code, l.debit, l.credit) for l in reversal.lines.all()}
    assert rev_lines == {(code, credit, debit) for (code, debit, credit) in orig_lines}


def test_journal_posted_event_is_published():
    from erp.core.events import bus

    received = []
    bus.subscribe("accounting.JournalPosted", lambda e: received.append(e.payload))
    make_coa()
    make_period()
    entry = post_journal(_entry([LineInput("1000", debit=5_00), LineInput("3000", credit=5_00)]))
    assert any(p.get("number") == entry.number for p in received)
