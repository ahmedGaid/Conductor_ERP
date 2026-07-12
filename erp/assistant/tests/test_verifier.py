"""L1 verifier (os-foundations FILE_02) — framework + the six invariant packs.

Each pack is pinned with ≥1 passing case (clean books) and ≥1 catching case (deliberately corrupted
books, mutated directly via the ORM to bypass the service-layer guards). The framework is pinned to
fail soft on unknown/throwing packs, and every pack is proven read-only (row counts unchanged).
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from erp.accounting.domain.accounts import AccountType
from erp.accounting.domain.models import (Account, EntryStatus, FiscalYear, JournalEntry,
                                          JournalLine, Period, PeriodStatus)
from erp.assistant import verifier
from erp.inventory.domain.models import (Item, StockBalance, StockTransfer, TransferStatus,
                                         Warehouse)
from erp.sales.domain.models import Customer, OrderStatus, SalesOrder, SalesOrderLine

pytestmark = pytest.mark.django_db

TODAY = dt.date(2026, 3, 15)


# --- fixtures (built straight through the ORM, no service validation) ---------------------------

def _period(status=PeriodStatus.OPEN) -> Period:
    fy = FiscalYear.objects.create(code="FY2026", start_date=dt.date(2026, 1, 1),
                                   end_date=dt.date(2026, 12, 31))
    return Period.objects.create(fiscal_year=fy, code="2026-03", start_date=dt.date(2026, 3, 1),
                                 end_date=dt.date(2026, 3, 31), status=status)


def _posted_entry(period: Period, *, debit: int = 1000, credit: int = 1000) -> JournalEntry:
    cash = Account.objects.create(code="1000", name="Cash", type=AccountType.ASSET)
    sales = Account.objects.create(code="4000", name="Sales", type=AccountType.INCOME)
    entry = JournalEntry.objects.create(number="JE-2026-000001", date=TODAY, period=period,
                                        status=EntryStatus.POSTED)
    JournalLine.objects.create(entry=entry, line_no=1, account=cash, debit=debit, credit=0)
    JournalLine.objects.create(entry=entry, line_no=2, account=sales, debit=0, credit=credit)
    return entry


def _order(number: str = "SO-2026-000001", *, subtotal: int = 3000) -> SalesOrder:
    cust = Customer.objects.create(code="C-1", name="Nile Traders")
    order = SalesOrder.objects.create(number=number, customer=cust, order_date=TODAY,
                                      warehouse_code="WH-1", subtotal_minor=subtotal,
                                      status=OrderStatus.DRAFT)
    SalesOrderLine.objects.create(order=order, line_no=1, item_sku="SKU-1", quantity=Decimal("2"),
                                  unit_price_minor=1000, line_total_minor=2000)
    SalesOrderLine.objects.create(order=order, line_no=2, item_sku="SKU-2", quantity=Decimal("1"),
                                  unit_price_minor=1000, line_total_minor=1000)
    return order


def _balance(qty: str = "10") -> StockBalance:
    item = Item.objects.create(sku="SKU-1", name="Blue Widget")
    wh = Warehouse.objects.create(code="WH-1", name="Main")
    return StockBalance.objects.create(item=item, warehouse=wh, quantity=Decimal(qty))


def _scope(**links_and_payload) -> dict:
    """Build a scope from ``type=value`` link kwargs plus an optional ``payload``."""
    payload = links_and_payload.pop("payload", {})
    links = [{"type": t, "value": v} for t, v in links_and_payload.items()]
    return {"links": links, "payload": payload}


# --- T2.1 framework -----------------------------------------------------------------------------

def test_unknown_pack_becomes_a_failing_finding():
    report = verifier.run(["no_such_pack"], _scope())
    assert report.ok is False
    assert report.findings[0].pack == "no_such_pack"
    assert report.findings[0].data["error"] == "unknown_pack"


def test_throwing_pack_becomes_a_failing_finding_no_exception_escapes():
    verifier.PACKS["_boom"] = lambda scope: (_ for _ in ()).throw(ValueError("planted"))
    try:
        report = verifier.run(["_boom"], _scope())
    finally:
        del verifier.PACKS["_boom"]
    assert report.ok is False
    assert report.findings[0].data["error"] == "ValueError"


def test_report_ok_is_the_and_of_findings():
    period = _period()
    _posted_entry(period)
    report = verifier.run(["trial_balance", "no_such_pack"], _scope())
    assert report.ok is False  # one good, one unknown -> overall fail
    assert [f.ok for f in report.findings] == [True, False]


# --- T2.2 accounting packs ----------------------------------------------------------------------

def test_trial_balance_passes_on_balanced_books():
    _posted_entry(_period())
    assert verifier.run(["trial_balance"], _scope()).ok is True


def test_trial_balance_catches_a_corrupted_line():
    entry = _posted_entry(_period())
    JournalLine.objects.filter(entry=entry, line_no=1).update(debit=9999)  # bypass service guards
    report = verifier.run(["trial_balance"], _scope())
    assert report.ok is False
    assert report.findings[0].data["total_debit"] != report.findings[0].data["total_credit"]


def test_journal_balanced_passes_and_catches():
    period = _period()
    entry = _posted_entry(period)
    scope = _scope(journalEntry=str(entry.id))
    assert verifier.run(["journal_balanced"], scope).ok is True
    JournalLine.objects.filter(entry=entry, line_no=1).update(debit=5)
    caught = verifier.run(["journal_balanced"], scope)
    assert caught.ok is False
    assert caught.findings[0].data["entry"] == entry.number


def test_journal_balanced_not_applicable_without_a_journal_link():
    finding = verifier.run(["journal_balanced"], _scope())
    assert finding.ok is True
    assert finding.findings[0].data["applicable"] is False


def test_period_open_passes_in_open_period_and_catches_a_closed_one():
    period = _period()
    entry = _posted_entry(period)
    scope = _scope(journalEntry=str(entry.id))
    assert verifier.run(["period_open"], scope).ok is True
    Period.objects.filter(pk=period.pk).update(status=PeriodStatus.CLOSED)
    caught = verifier.run(["period_open"], scope)
    assert caught.ok is False
    assert caught.findings[0].data["period"] == period.code


def test_period_open_catches_a_date_with_no_period():
    _period()
    order = _order(number="SO-2099-000001")
    SalesOrder.objects.filter(pk=order.pk).update(order_date=dt.date(2099, 1, 1))
    caught = verifier.run(["period_open"], _scope(order=str(order.id)))
    assert caught.ok is False
    assert caught.findings[0].data["date"] == "2099-01-01"


# --- T2.3 document / stock packs ----------------------------------------------------------------

def test_doc_totals_passes_and_catches():
    order = _order()
    scope = _scope(order=str(order.id))
    assert verifier.run(["doc_totals"], scope).ok is True
    SalesOrder.objects.filter(pk=order.pk).update(subtotal_minor=1)  # header now lies
    caught = verifier.run(["doc_totals"], scope)
    assert caught.ok is False
    assert caught.findings[0].data["header"] == 1
    assert caught.findings[0].data["lines"] == 3000


def test_doc_totals_not_applicable_without_a_document_link():
    finding = verifier.run(["doc_totals"], _scope()).findings[0]
    assert finding.ok is True and finding.data["applicable"] is False


def test_stock_non_negative_passes_and_catches_via_payload():
    _balance("10")
    ok_scope = _scope(payload={"item_sku": "SKU-1", "warehouse": "WH-1"})
    assert verifier.run(["stock_non_negative"], ok_scope).ok is True
    StockBalance.objects.update(quantity=Decimal("-3"))  # oversold, bypassing services
    caught = verifier.run(["stock_non_negative"], ok_scope)
    assert caught.ok is False
    assert caught.findings[0].data["item"] == "SKU-1"


def test_stock_non_negative_catches_via_a_transfer_link():
    bal = _balance("-1")
    transfer = StockTransfer.objects.create(item=bal.item, source=bal.warehouse,
                                            destination=bal.warehouse, quantity=Decimal("1"),
                                            date=TODAY, status=TransferStatus.DRAFT)
    caught = verifier.run(["stock_non_negative"], _scope(stockTransfer=str(transfer.id)))
    assert caught.ok is False


def test_stock_non_negative_not_applicable_without_stock_scope():
    assert verifier.run(["stock_non_negative"], _scope()).findings[0].data["applicable"] is False


def test_sequence_unbroken_passes_and_catches_a_gap():
    _order("SO-2026-000001")
    Customer.objects.get(code="C-1")  # reuse
    mid = SalesOrder.objects.create(number="SO-2026-000002",
                                    customer=Customer.objects.get(code="C-1"),
                                    order_date=TODAY, warehouse_code="WH-1")
    SalesOrder.objects.create(number="SO-2026-000003",
                              customer=Customer.objects.get(code="C-1"),
                              order_date=TODAY, warehouse_code="WH-1")
    scope = _scope(order=str(SalesOrder.objects.get(number="SO-2026-000003").id))
    assert verifier.run(["sequence_unbroken"], scope).ok is True
    mid.delete()  # plant a gap in the middle of the SO-2026- sequence
    caught = verifier.run(["sequence_unbroken"], scope)
    assert caught.ok is False
    assert caught.findings[0].data["missing"] == [2]


def test_sequence_unbroken_not_applicable_without_a_document_link():
    finding = verifier.run(["sequence_unbroken"], _scope()).findings[0]
    assert finding.ok is True and finding.data["applicable"] is False


# --- read-only guarantee (every pack) -----------------------------------------------------------

def test_every_pack_is_read_only():
    """Running any pack must not change a single row (compensation is FILE_03's job, not a pack's)."""
    period = _period()
    entry = _posted_entry(period)
    order = _order()
    _balance("10")
    scope = _scope(journalEntry=str(entry.id), order=str(order.id),
                   payload={"item_sku": "SKU-1", "warehouse": "WH-1"})
    watched = (JournalEntry, JournalLine, SalesOrder, SalesOrderLine, StockBalance, Period, Account)
    before = {m: m.objects.count() for m in watched}
    for name in verifier.PACKS:
        verifier.run([name], scope)
    after = {m: m.objects.count() for m in watched}
    assert before == after
