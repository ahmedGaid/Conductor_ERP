"""FILE_04 — status reconciliation: poll backoff/cap on ``poll_invoice`` and the beat sweep
(``due_polls`` / ``einvoice.reconcile_submitted``)."""
from __future__ import annotations

import datetime as dt

import pytest
from django.utils import timezone

from erp.einvoice.domain.models import ETAInvoice, ETAStatus
from erp.einvoice.services import EInvoiceInput, due_polls, poll_invoice, record_invoice, submit_invoice
from erp.einvoice.services.issue import MAX_POLL_ATTEMPTS, POLL_BACKOFF_SCHEDULE

pytestmark = pytest.mark.django_db


def _submitted(number="INV-RECON-1") -> ETAInvoice:
    eta = record_invoice(EInvoiceInput(invoice_number=number, issue_date=dt.date(2026, 6, 16),
                                       net_minor=100_00, tax_minor=14_00, total_minor=114_00))
    submit_invoice(eta)
    eta.refresh_from_db()
    return eta


def test_pending_poll_increments_attempts_and_backs_off():
    eta = _submitted()
    poll_invoice(eta)
    eta.refresh_from_db()
    assert eta.poll_attempts == 1
    assert eta.poll_stalled is False
    assert eta.next_poll_at is not None
    expected = timezone.now() + dt.timedelta(seconds=POLL_BACKOFF_SCHEDULE[0])
    assert abs((eta.next_poll_at - expected).total_seconds()) < 5


def test_repeated_pending_polls_use_the_backoff_schedule_then_repeat_last_step():
    eta = _submitted()
    for _ in range(len(POLL_BACKOFF_SCHEDULE) + 2):
        poll_invoice(eta)
        eta.refresh_from_db()
    # Schedule exhausted -> repeats the last (longest) step, not an IndexError.
    expected = timezone.now() + dt.timedelta(seconds=POLL_BACKOFF_SCHEDULE[-1])
    assert abs((eta.next_poll_at - expected).total_seconds()) < 5


def test_poll_stalls_after_max_attempts_and_alerts():
    eta = _submitted()
    for _ in range(MAX_POLL_ATTEMPTS):
        poll_invoice(eta)
        eta.refresh_from_db()
    assert eta.poll_attempts == MAX_POLL_ATTEMPTS
    assert eta.poll_stalled is True
    assert eta.next_poll_at is None


def test_valid_outcome_resets_attempts_and_stalled_flag(monkeypatch):
    from erp.einvoice.services import eta_adapter

    eta = _submitted()
    eta.poll_attempts = MAX_POLL_ATTEMPTS
    eta.poll_stalled = True
    eta.save(update_fields=["poll_attempts", "poll_stalled"])

    monkeypatch.setattr(eta_adapter, "query", lambda uuid: "valid")
    poll_invoice(eta)
    eta.refresh_from_db()
    assert eta.status == ETAStatus.VALID
    assert eta.poll_attempts == 0
    assert eta.poll_stalled is False
    assert eta.next_poll_at is None


def test_due_polls_excludes_stalled_and_not_yet_due_rows():
    due_now = _submitted("INV-RECON-DUE")
    stalled = _submitted("INV-RECON-STALLED")
    stalled.poll_stalled = True
    stalled.save(update_fields=["poll_stalled"])
    not_yet_due = _submitted("INV-RECON-FUTURE")
    not_yet_due.next_poll_at = timezone.now() + dt.timedelta(hours=1)
    not_yet_due.save(update_fields=["next_poll_at"])

    ids = set(due_polls().values_list("invoice_number", flat=True))
    assert due_now.invoice_number in ids
    assert stalled.invoice_number not in ids
    assert not_yet_due.invoice_number not in ids


def test_reconcile_submitted_task_polls_due_rows_only(monkeypatch):
    from erp.einvoice import tasks

    due_now = _submitted("INV-RECON-TASK-DUE")
    not_yet_due = _submitted("INV-RECON-TASK-FUTURE")
    not_yet_due.next_poll_at = timezone.now() + dt.timedelta(hours=1)
    not_yet_due.save(update_fields=["next_poll_at"])

    polled: list[str] = []
    from erp.einvoice.services import eta_adapter

    def _query(uuid):
        polled.append(uuid)
        return "pending"

    monkeypatch.setattr(eta_adapter, "query", _query)
    count = tasks.reconcile_submitted()
    assert count == 1
    assert polled == [due_now.uuid]
