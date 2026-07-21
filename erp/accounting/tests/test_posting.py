"""Double-entry posting invariants — the accounting module's acceptance criteria."""
from __future__ import annotations

import datetime as dt

import pytest

from erp.accounting.domain.models import (
    Account,
    EntryStatus,
    JournalEntry,
    JournalLine,
    PeriodStatus,
)
from erp.accounting.errors import (
    AlreadyPostedError,
    ClosedPeriodError,
    InvalidLineError,
    NonPostableAccountError,
    UnbalancedEntryError,
)
from erp.accounting.services import (
    JournalInput,
    LineInput,
    post_draft_journal_entry,
    post_journal,
    reverse_journal,
)
from erp.accounting.services.posting import create_draft_journal

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


# --- post_draft_journal_entry (draft → posted transition) ---------------------------------------

def _draft(**kw):
    return create_draft_journal(
        _entry([LineInput("1000", debit=70_00), LineInput("3000", credit=70_00)], **kw)
    )


def test_post_draft_flips_status_with_audit_and_event():
    from erp.audit.models import AuditEntry
    from erp.core.events import bus

    received = []
    bus.subscribe("accounting.JournalPosted", lambda e: received.append(e.payload))
    make_coa()
    make_period()
    draft = _draft()
    assert draft.status == EntryStatus.DRAFT

    posted = post_draft_journal_entry(draft)
    assert posted.id == draft.id  # the same entry, not a new one
    assert posted.status == EntryStatus.POSTED
    assert posted.posted_at is not None
    # Same business event as a fresh post: the shared "post_journal" audit action + JOURNAL_POSTED.
    assert AuditEntry.objects.filter(
        module="accounting", action="post_journal", entity_id=posted.number
    ).count() == 1
    assert any(p.get("number") == posted.number for p in received)


def test_post_draft_on_already_posted_is_rejected():
    make_coa()
    make_period()
    draft = _draft()
    post_draft_journal_entry(draft)
    with pytest.raises(AlreadyPostedError):
        post_draft_journal_entry(draft)


def test_post_draft_rejects_period_closed_since_draft():
    make_coa()
    period = make_period()  # open when the draft is written
    draft = _draft()
    period.status = PeriodStatus.CLOSED
    period.save(update_fields=["status"])
    draft.refresh_from_db()  # drop the cached (open) period so the check re-reads it
    with pytest.raises(ClosedPeriodError):
        post_draft_journal_entry(draft)
    draft.refresh_from_db()
    assert draft.status == EntryStatus.DRAFT  # nothing flipped


def test_post_draft_rejects_account_deactivated_since_draft():
    make_coa()
    make_period()
    draft = _draft()
    Account.objects.filter(code="1000").update(is_active=False)  # deactivated after the draft
    with pytest.raises(NonPostableAccountError):
        post_draft_journal_entry(draft)
    draft.refresh_from_db()
    assert draft.status == EntryStatus.DRAFT
