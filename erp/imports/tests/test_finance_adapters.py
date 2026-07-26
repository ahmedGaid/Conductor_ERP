"""Finance adapters (FILE_16): ``journal_entries`` + ``account_opening``.

Both write DRAFT journal entries via ``contracts.create_journal_entry_draft`` and are grouped
document adapters, so — like ``test_document_adapters.py`` — these tests build ``ImportRow``
fixtures directly (the shape ``analyze``/``normalize_row`` would have produced) and drive
``engine.execute_batch``/``rollback_batch``. They also exercise the engine's new ``validate_group``
hook: the per-entry balance guard (``journal_entries``) and the human-in-the-loop suspense
correction (``account_opening``).

``payments``/``receipts`` now ship too (session 16b) — see ``erp/imports/tests/
test_receipt_adapter.py`` and ``test_payment_adapter.py``, and ``erp.sales``/``erp.purchasing``'s
own ``pending_payments`` service tests; not repeated here. The inventory-opening adapters are still
deliberately NOT built (see ``adapters/accounting.py`` and ``DESIGN_PENDING_PAYMENTS_AND_STOCK.md``)
— the guard test below pins that decision.
"""
from __future__ import annotations

import pytest
from django.contrib.auth.models import Group

from erp.accounting.domain.models import EntryStatus, JournalEntry
from erp.accounting.services.reports import trial_balance
from erp.accounting.services.seeding import seed_baseline_accounting
from erp.identity.models import User
from erp.identity.roles import BRANCH_MANAGER
from erp.imports import engine, registry
from erp.imports.models import ImportBatch, ImportRow

pytestmark = pytest.mark.django_db


# --- helpers ---------------------------------------------------------------------------------
def _manager(username: str) -> User:
    """A superuser: satisfies ``require_role`` and ``scope_queryset``'s ALL-scope (see the same
    helper in ``test_document_adapters.py``)."""
    bm, _ = Group.objects.get_or_create(name=BRANCH_MANAGER)
    u = User.objects.create_user(
        username=username, email=f"{username}@erp.local", password="pw12345!", is_superuser=True,
    )
    u.groups.add(bm)
    return u


def _row(batch, row_number, normalized, *, status=ImportRow.Status.VALID) -> ImportRow:
    return ImportRow.objects.create(
        batch=batch, row_number=row_number, normalized=normalized, status=status,
    )


def _batch(entity, strategy=ImportBatch.Strategy.CREATE_ONLY) -> ImportBatch:
    return ImportBatch.objects.create(entity=entity, strategy=strategy)


@pytest.fixture()
def coa():
    """Baseline chart of accounts + current-year fiscal periods — journals need a postable account
    and a period covering their date (dates below sit in the seeded current year)."""
    seed_baseline_accounting()


def _je_line(**over):
    base = {"account_ref": "1100", "debit_minor": 0, "credit_minor": 0, "line_memo": ""}
    base.update(over)
    return base


# --- journal_entries: balanced draft creation ----------------------------------------------------
def test_journal_entry_creates_a_balanced_draft(coa):
    actor = _manager("je1")
    batch = _batch("journal_entries")
    # JE-1: Dr Cash 100.00 / Cr Sales Revenue 100.00, two rows, header on row 1 (merged-cell).
    _row(batch, 1, {"entry_ref": "JE-1", "date": "2026-06-01", "memo": "Cash sale",
                    **_je_line(account_ref="1000", debit_minor=100_00)})
    _row(batch, 2, _je_line(account_ref="4000", credit_minor=100_00))

    report = engine.execute_batch(actor, batch)

    assert report["created"] == 2  # two rows imported (report counts rows, not documents)
    assert JournalEntry.objects.count() == 1
    entry = JournalEntry.objects.get(reference="import-je:JE-1")
    assert entry.status == EntryStatus.DRAFT
    assert entry.memo == "Cash sale"
    lines = list(entry.lines.order_by("line_no"))
    assert [(ln.account.code, ln.debit, ln.credit) for ln in lines] == [
        ("1000", 100_00, 0), ("4000", 0, 100_00),
    ]
    assert set(batch.rows.values_list("status", flat=True)) == {ImportRow.Status.IMPORTED}


def test_unbalanced_entry_errors_only_that_entry_with_the_difference(coa):
    actor = _manager("je2")
    batch = _batch("journal_entries")
    # JE-BAD: debits 100.00 vs credits 60.00 — 40.00 short.
    _row(batch, 1, {"entry_ref": "JE-BAD", "date": "2026-06-01",
                    **_je_line(account_ref="1000", debit_minor=100_00)})
    _row(batch, 2, _je_line(account_ref="4000", credit_minor=60_00))
    # JE-OK: balanced — must still import despite the bad entry above it.
    _row(batch, 3, {"entry_ref": "JE-OK", "date": "2026-06-01",
                    **_je_line(account_ref="1000", debit_minor=10_00)})
    _row(batch, 4, _je_line(account_ref="4000", credit_minor=10_00))

    report = engine.execute_batch(actor, batch)

    assert report["created"] == 2  # only JE-OK's two rows
    assert report["errors"] == 2   # JE-BAD's two rows
    assert JournalEntry.objects.filter(reference="import-je:JE-OK").exists()
    assert not JournalEntry.objects.filter(reference="import-je:JE-BAD").exists()

    bad_rows = batch.rows.filter(row_number__in=[1, 2])
    for row in bad_rows:
        assert row.status == ImportRow.Status.ERROR
        issue = next(i for i in row.issues if i["code"] == "unbalanced_entry")
        assert issue["meta"]["difference_minor"] == 40_00
    # batch-level whole-file imbalance summary
    batch.refresh_from_db()
    summary = batch.stats.get("unbalanced_entries")
    assert summary == [{"entry_ref": "JE-BAD", "difference_minor": 40_00}]


def test_journal_entry_rollback_deletes_the_draft(coa):
    actor = _manager("je3")
    batch = _batch("journal_entries")
    _row(batch, 1, {"entry_ref": "JE-7", "date": "2026-06-01",
                    **_je_line(account_ref="1000", debit_minor=50_00)})
    _row(batch, 2, _je_line(account_ref="4000", credit_minor=50_00))
    engine.execute_batch(actor, batch)
    assert JournalEntry.objects.filter(reference="import-je:JE-7").exists()

    result = engine.rollback_batch(actor, batch)

    assert result == {"reverted": 1, "skipped": 0, "cannot": []}  # one DOCUMENT, not two rows
    assert not JournalEntry.objects.filter(reference="import-je:JE-7").exists()
    assert set(batch.rows.values_list("status", flat=True)) == {ImportRow.Status.REVERTED}


def test_posted_entry_cannot_be_rolled_back(coa):
    """If a human posts the imported draft before a rollback, the rollback refuses it (never deletes
    a live ledger entry) and reports ``cannot_revert`` rather than guessing."""
    actor = _manager("je4")
    batch = _batch("journal_entries")
    _row(batch, 1, {"entry_ref": "JE-8", "date": "2026-06-01",
                    **_je_line(account_ref="1000", debit_minor=30_00)})
    _row(batch, 2, _je_line(account_ref="4000", credit_minor=30_00))
    engine.execute_batch(actor, batch)
    entry = JournalEntry.objects.get(reference="import-je:JE-8")
    entry.status = EntryStatus.POSTED
    entry.save(update_fields=["status"])

    result = engine.rollback_batch(actor, batch)

    assert result["reverted"] == 0
    assert len(result["cannot"]) == 1
    assert JournalEntry.objects.filter(reference="import-je:JE-8").exists()


def test_existing_entry_skipped_under_skip_existing(coa):
    actor = _manager("je5")
    batch = _batch("journal_entries", strategy=ImportBatch.Strategy.SKIP_EXISTING)
    _row(batch, 1, {"entry_ref": "JE-9", "date": "2026-06-01",
                    **_je_line(account_ref="1000", debit_minor=5_00)})
    _row(batch, 2, _je_line(account_ref="4000", credit_minor=5_00))
    engine.execute_batch(actor, batch)
    assert JournalEntry.objects.filter(reference="import-je:JE-9").count() == 1

    batch2 = _batch("journal_entries", strategy=ImportBatch.Strategy.SKIP_EXISTING)
    _row(batch2, 1, {"entry_ref": "JE-9", "date": "2026-06-01",
                     **_je_line(account_ref="1000", debit_minor=5_00)})
    _row(batch2, 2, _je_line(account_ref="4000", credit_minor=5_00))
    report = engine.execute_batch(actor, batch2)

    assert report["skipped"] == 2
    assert JournalEntry.objects.filter(reference="import-je:JE-9").count() == 1


def test_unknown_account_errors_only_that_entry(coa):
    actor = _manager("je6")
    batch = _batch("journal_entries")
    _row(batch, 1, {"entry_ref": "JE-X", "date": "2026-06-01",
                    **_je_line(account_ref="9999", debit_minor=5_00)})  # no such account
    _row(batch, 2, _je_line(account_ref="4000", credit_minor=5_00))

    report = engine.execute_batch(actor, batch)

    assert report["created"] == 0
    assert not JournalEntry.objects.filter(reference="import-je:JE-X").exists()
    row = batch.rows.get(row_number=1)
    assert row.status == ImportRow.Status.ERROR
    assert any(i["code"] == "group_write_failed" for i in row.issues)


def test_account_resolves_by_name(coa):
    actor = _manager("je7")
    batch = _batch("journal_entries")
    _row(batch, 1, {"entry_ref": "JE-N", "date": "2026-06-01",
                    **_je_line(account_ref="Cash", debit_minor=7_00)})
    _row(batch, 2, _je_line(account_ref="Sales Revenue", credit_minor=7_00))

    report = engine.execute_batch(actor, batch)

    assert report["created"] == 2
    entry = JournalEntry.objects.get(reference="import-je:JE-N")
    assert {ln.account.code for ln in entry.lines.all()} == {"1000", "4000"}


# --- account_opening: whole file = one balanced opening entry ------------------------------------
def _opening_rows(batch, lines):
    """A trial-balance file: no header column, so ``opening_ref`` comes from the FieldSpec default
    (``"opening"``) — here injected directly since these fixtures bypass ``normalize``. Every row is
    one account's opening balance."""
    for i, (account, debit, credit) in enumerate(lines, start=1):
        normalized = {"opening_ref": "opening", "date": "2026-01-01",
                      "account_ref": account, "debit_minor": debit, "credit_minor": credit}
        _row(batch, i, normalized)


def test_balanced_opening_creates_one_draft_entry_and_trial_balances(coa):
    actor = _manager("ao1")
    batch = _batch("account_opening")
    # Assets (Dr) = Cash 500 + Inventory 300 = 800; funded by Share Capital (Cr) 800.
    _opening_rows(batch, [
        ("1000", 500_00, 0),
        ("1200", 300_00, 0),
        ("3000", 0, 800_00),
    ])

    report = engine.execute_batch(actor, batch)

    assert report["created"] == 3
    assert JournalEntry.objects.count() == 1
    entry = JournalEntry.objects.get(reference="import-open:opening")
    assert entry.status == EntryStatus.DRAFT
    assert entry.source == "import-opening"
    total_debit = sum(ln.debit for ln in entry.lines.all())
    total_credit = sum(ln.credit for ln in entry.lines.all())
    assert total_debit == total_credit == 800_00
    # no correction proposed for an already-balanced file
    batch.refresh_from_db()
    assert "opening_correction" not in (batch.stats or {})


def test_imbalanced_opening_blocks_and_proposes_a_suspense_line(coa):
    actor = _manager("ao2")
    batch = _batch("account_opening")
    # Debits 800 but credits only 700 — 100 short; needs a 100 CREDIT to a suspense account.
    _opening_rows(batch, [
        ("1000", 500_00, 0),
        ("1200", 300_00, 0),
        ("3000", 0, 700_00),
    ])

    report = engine.execute_batch(actor, batch)

    assert report["created"] == 0
    assert not JournalEntry.objects.exists()  # nothing imported without approval
    for row in batch.rows.all():
        assert row.status == ImportRow.Status.ERROR
        issue = next(i for i in row.issues if i["code"] == "opening_imbalance")
        assert issue["meta"]["difference_minor"] == 100_00
        assert issue["meta"]["suspense_account"] == "3100"

    batch.refresh_from_db()
    correction = batch.stats["opening_correction"]
    assert correction["difference_minor"] == 100_00
    assert correction["suspense_account"] == "3100"
    assert correction["proposed_line"] == {
        "account_ref": "3100", "debit_minor": 0, "credit_minor": 100_00,
    }
    assert correction["approved"] is False


def test_approved_suspense_correction_imports_a_balanced_opening(coa):
    actor = _manager("ao3")
    batch = _batch("account_opening")
    _opening_rows(batch, [
        ("1000", 500_00, 0),
        ("1200", 300_00, 0),
        ("3000", 0, 700_00),
    ])
    # A human approves the correction in the panel: flag it, then (re-validation would reset the
    # rows to VALID — simulated here) re-run.
    batch.stats = {"opening_correction": {"approved": True}}
    batch.save(update_fields=["stats"])

    report = engine.execute_batch(actor, batch)

    assert report["created"] == 3
    entry = JournalEntry.objects.get(reference="import-open:opening")
    total_debit = sum(ln.debit for ln in entry.lines.all())
    total_credit = sum(ln.credit for ln in entry.lines.all())
    assert total_debit == total_credit == 800_00
    # the generated balancing line landed on the suspense account
    suspense_lines = [ln for ln in entry.lines.all() if ln.account.code == "3100"]
    assert len(suspense_lines) == 1
    assert suspense_lines[0].credit == 100_00


def test_opening_correction_approve_endpoint_unblocks_a_real_failed_execute(coa):
    """The real round trip, through the actual API — not the earlier tests' direct ``batch.stats``
    write: a first execute attempt fails and blocks on the imbalance (exactly like
    ``test_imbalanced_opening_blocks_and_proposes_a_suspense_line``); the review screen's ONLY way
    to unblock it is ``OpeningCorrectionApproveView``, which previously didn't exist — nothing in
    the API or UI could ever set ``opening_correction.approved`` before this endpoint was added
    (FILE_17 acceptance finding)."""
    from rest_framework.test import APIClient

    actor = _manager("ao5")
    batch = _batch("account_opening")
    _opening_rows(batch, [
        ("1000", 500_00, 0),
        ("1200", 300_00, 0),
        ("3000", 0, 700_00),
    ])

    first = engine.execute_batch(actor, batch)
    assert first["created"] == 0
    batch.refresh_from_db()
    assert batch.status == ImportBatch.Status.DONE
    assert batch.stats["opening_correction"]["approved"] is False
    assert all(row.status == ImportRow.Status.ERROR for row in batch.rows.all())

    client = APIClient()
    client.force_authenticate(user=actor)
    resp = client.post(f"/api/imports/{batch.id}/opening-correction/approve")

    assert resp.status_code == 200
    batch.refresh_from_db()
    assert batch.stats["opening_correction"]["approved"] is True
    assert batch.status == ImportBatch.Status.PREVIEWING
    assert not batch.rows.filter(status=ImportRow.Status.ERROR).exists()

    second = engine.execute_batch(actor, batch)
    assert second["created"] == 3
    entry = JournalEntry.objects.get(reference="import-open:opening")
    total_debit = sum(ln.debit for ln in entry.lines.all())
    total_credit = sum(ln.credit for ln in entry.lines.all())
    assert total_debit == total_credit == 800_00


def test_opening_correction_approve_endpoint_400s_without_a_correction(coa):
    from rest_framework.test import APIClient

    actor = _manager("ao6")
    batch = _batch("account_opening")
    _opening_rows(batch, [("1000", 800_00, 0), ("3000", 0, 800_00)])  # already balanced

    client = APIClient()
    client.force_authenticate(user=actor)
    resp = client.post(f"/api/imports/{batch.id}/opening-correction/approve")

    assert resp.status_code == 400


def test_approved_opening_trial_balance_stays_balanced_after_posting(coa):
    """The Phase-A promise, end to end: an approved opening entry, once posted, leaves the trial
    balance balanced to the piastre."""
    actor = _manager("ao4")
    batch = _batch("account_opening")
    _opening_rows(batch, [("1000", 500_00, 0), ("1200", 300_00, 0), ("3000", 0, 800_00)])
    engine.execute_batch(actor, batch)
    entry = JournalEntry.objects.get(reference="import-open:opening")

    # Post the draft the way the journal screen would (status flip is enough for trial_balance,
    # which reads posted lines).
    entry.status = EntryStatus.POSTED
    entry.save(update_fields=["status"])

    tb = trial_balance()
    assert tb.is_balanced
    assert tb.total_debit == tb.total_credit == 800_00


# --- guard: inventory_transactions (historic movements) stays unbuilt (blocker, by design) --------
def test_blocked_finance_entities_are_not_registered():
    """FILE_16 STOP decision: no GL-correct drafts-only write-path exists for these, so registering
    an adapter would misstate a customer's books. Pin it so a later session re-reads the reasoning
    (adapters/accounting.py) before adding one.

    ``receipts``/``payments`` are deliberately NOT in this list any more: session 16b built
    ``erp.{sales,purchasing}.services.pending_payments.create_pending_payment`` — the standalone,
    unallocated-payment write-paths this guard's original reasoning said didn't exist — and
    registered adapters against them. ``inventory_opening`` is also NO LONGER on this list: session
    16c built ``erp.inventory.services.pending_stock.create_pending_stock_opening`` (posts to a
    dedicated suspense account, never GRNI) and registered an adapter against it
    (``erp/imports/adapters/inventory.py``) — see ``test_inventory_opening_adapter.py`` and the
    ``inventory_double_booked`` guard tests below. ``inventory_transactions`` (historic movements)
    remains blocked: weighted-average costing has no as-of-date, so backdating would corrupt COGS
    (documented architecture blocker, not a TODO — see DESIGN_PENDING_PAYMENTS_AND_STOCK.md)."""
    registered = set(registry.entities())
    assert {"journal_entries", "account_opening", "receipts", "payments",
            "inventory_opening"} <= registered
    assert "inventory_transactions" not in registered


# --- guard: account_opening + inventory_opening double-booking the Inventory control account ------
def test_account_opening_flags_double_booked_when_inventory_opening_already_imported(coa):
    """A TB file that includes the Inventory control account (1200) while item-level opening rows
    have ALSO been imported would double-count Inventory on the balance sheet — one aggregate line
    from the TB, one built up from item quantities. The human must drop the 1200 line from the TB
    file or skip item-level opening; never silently import both."""
    from erp.imports.models import ImportBatch as IB

    IB.objects.create(entity="inventory_opening", status=IB.Status.DONE)
    actor = _manager("ao5")
    batch = _batch("account_opening")
    _opening_rows(batch, [("1000", 500_00, 0), ("1200", 300_00, 0), ("3000", 0, 800_00)])

    report = engine.execute_batch(actor, batch)

    assert report["created"] == 0
    assert not JournalEntry.objects.exists()
    for row in batch.rows.all():
        assert any(i["code"] == "inventory_double_booked" for i in row.issues)


def test_account_opening_without_inventory_opening_imports_1200_normally(coa):
    """Regression: when no ``inventory_opening`` batch exists, a TB file's 1200 line imports exactly
    as before (existing behavior, session 16c must not change it)."""
    actor = _manager("ao6")
    batch = _batch("account_opening")
    _opening_rows(batch, [("1000", 500_00, 0), ("1200", 300_00, 0), ("3000", 0, 800_00)])

    report = engine.execute_batch(actor, batch)

    assert report["created"] == 3
    assert JournalEntry.objects.filter(reference="import-open:opening").exists()


def test_account_opening_ignores_a_rolled_back_inventory_opening_batch(coa):
    """A rolled-back inventory_opening import means nothing was actually kept — the TB's 1200 line
    is not a double-count, so it must import normally."""
    from erp.imports.models import ImportBatch as IB

    IB.objects.create(entity="inventory_opening", status=IB.Status.ROLLED_BACK)
    actor = _manager("ao7")
    batch = _batch("account_opening")
    _opening_rows(batch, [("1000", 500_00, 0), ("1200", 300_00, 0), ("3000", 0, 800_00)])

    report = engine.execute_batch(actor, batch)

    assert report["created"] == 3
    assert JournalEntry.objects.filter(reference="import-open:opening").exists()
