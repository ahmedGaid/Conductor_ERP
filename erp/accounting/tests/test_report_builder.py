"""Custom report builder — run a saved definition over the GL + scheduled run writes a file."""
from __future__ import annotations

import datetime as dt

import pytest

from erp.accounting.domain.accounts import AccountType
from erp.accounting.domain.models import Account, ReportDefinition
from erp.accounting.services import (
    JournalInput,
    LineInput,
    is_due,
    post_journal,
    run_definition,
    run_scheduled,
)
from erp.accounting.api import exports as export_tables
from erp.core.exports import render_bytes

from .factories import make_coa, make_period

pytestmark = pytest.mark.django_db

D = dt.date(2026, 6, 15)


def _post(lines, date=D):
    return post_journal(JournalInput(date=date, lines=lines))


def _seed():
    make_coa()
    make_period("2026-06")
    # Two revenue posts + a rent expense.
    _post([LineInput("1000", debit=1_000_00), LineInput("4000", credit=1_000_00)])
    _post([LineInput("1000", debit=400_00), LineInput("4000", credit=400_00)])
    _post([LineInput("5100", debit=250_00), LineInput("1000", credit=250_00)])


def test_run_definition_by_account_filters_by_type():
    _seed()
    defn = ReportDefinition.objects.create(name="Income", account_type=AccountType.INCOME,
                                           group_by="account")
    built = run_definition(defn)
    assert len(built.rows) == 1
    row = built.rows[0]
    assert row.group_key == "4000"
    assert row.credit == 1_400_00
    assert row.balance == 1_400_00  # income credit-normal → positive
    assert built.total_credit == 1_400_00


def test_run_definition_by_explicit_codes():
    _seed()
    defn = ReportDefinition.objects.create(name="Cash only", account_codes="1000",
                                           group_by="account")
    built = run_definition(defn)
    assert [r.group_key for r in built.rows] == ["1000"]
    # Cash: 1,000 + 400 in, 250 out → debit 1,400, credit 250, balance 1,150 (asset debit-normal).
    assert built.rows[0].balance == 1_150_00


def test_run_definition_group_by_period():
    _seed()
    defn = ReportDefinition.objects.create(name="By period", group_by="period")
    built = run_definition(defn)
    assert len(built.rows) == 1
    assert built.rows[0].group_key == "2026-06"
    # Net movement across all accounts in a balanced ledger nets to zero.
    assert built.rows[0].balance == 0


def test_built_report_exports_to_csv():
    _seed()
    defn = ReportDefinition.objects.create(name="Income", account_type=AccountType.INCOME)
    built = run_definition(defn)
    table = export_tables.built_report_table(built, "en")
    payload = render_bytes(table, "csv")
    assert payload.startswith(b"\xef\xbb\xbf")          # UTF-8 BOM
    assert b"1400.00" in payload                         # money rendered in major units


def test_scheduled_run_writes_file_and_is_idempotent(settings, tmp_path):
    settings.REPORTS_DIR = tmp_path
    _seed()
    defn = ReportDefinition.objects.create(name="Daily income", account_type=AccountType.INCOME,
                                           schedule="daily")
    assert is_due(defn) is True                          # never run yet

    written = run_scheduled()
    assert len(written) == 1
    name, path = written[0]
    assert name == "Daily income"
    assert (tmp_path).exists()
    files = list(tmp_path.glob("*.csv"))
    assert len(files) == 1

    defn.refresh_from_db()
    assert defn.last_run_at is not None
    assert is_due(defn) is False                         # just ran ⇒ not due again

    # A second sweep writes nothing more.
    assert run_scheduled() == []


def test_unscheduled_definition_never_due():
    defn = ReportDefinition.objects.create(name="Manual", schedule="none")
    assert is_due(defn) is False
