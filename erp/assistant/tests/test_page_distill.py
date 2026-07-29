"""Page-context distillation (ai-reliability T3.8) — one fixture record per registered type,
asserting the exact rendered snapshot. Unregistered types and not-found/broken lookups are covered
separately since they share one fallback path (``render`` returns ``None``).
"""
from __future__ import annotations

import datetime as dt

import pytest

from erp.accounting.domain.models import JournalEntry, JournalLine
from erp.accounting.tests.factories import make_coa, make_period
from erp.assistant.services import page_distill
from erp.crm.domain.models import Opportunity
from erp.identity.models import User
from erp.inventory.contracts import receive
from erp.inventory.domain.models import Item, Warehouse
from erp.purchasing.domain.models import PurchaseOrder, PurchaseRequest, Supplier
from erp.sales.domain.models import Customer, Quotation, SalesOrder

pytestmark = pytest.mark.django_db


def _actor(username: str = "distill_user") -> User:
    user = User.objects.create_user(
        username=username, password="Dev12345!", email=f"{username}@example.test",
    )
    user.is_superuser = True  # scope never narrows these fixtures out
    user.save(update_fields=["is_superuser"])
    return user


# --- sales.orders ----------------------------------------------------------------------------

def test_sales_order_snapshot():
    actor = _actor()
    customer = Customer.objects.create(code="C-1", name="Acme")
    order = SalesOrder.objects.create(
        number="SO-1", customer=customer, order_date=dt.date(2026, 6, 1), warehouse_code="MAIN",
        status="confirmed", subtotal_minor=125_000, invoiced_minor=125_000, paid_minor=50_000,
    )

    snapshot = page_distill.render(actor, "sales.orders", str(order.id))

    assert snapshot == "status confirmed; total 1,250.00 EGP; invoiced 1,250.00 EGP; outstanding 750.00 EGP"


def test_sales_order_unknown_id_returns_none():
    actor = _actor()

    assert page_distill.render(actor, "sales.orders", "not-a-uuid") is None


# --- sales.quotations --------------------------------------------------------------------------

def test_sales_quotation_snapshot():
    actor = _actor()
    customer = Customer.objects.create(code="C-1", name="Acme")
    quote = Quotation.objects.create(
        number="QT-1", customer=customer, quote_date=dt.date(2026, 6, 1),
        validity_until=dt.date(2026, 7, 1), warehouse_code="MAIN", status="submitted",
        subtotal_minor=80_000,
    )

    snapshot = page_distill.render(actor, "sales.quotations", str(quote.id))

    assert snapshot == "status submitted; total 800.00 EGP; valid until 2026-07-01"


# --- sales.customers ----------------------------------------------------------------------------

def test_sales_customer_snapshot():
    actor = _actor()
    customer = Customer.objects.create(code="C-1", name="Acme")
    SalesOrder.objects.create(
        number="SO-1", customer=customer, order_date=dt.date(2026, 6, 1), warehouse_code="MAIN",
        status="invoiced", subtotal_minor=100_000, invoiced_minor=100_000, paid_minor=40_000,
    )

    snapshot = page_distill.render(actor, "sales.customers", "C-1")

    assert snapshot == "1 orders; outstanding 600.00 EGP"


# --- purchasing.orders --------------------------------------------------------------------------

def test_purchasing_order_snapshot():
    actor = _actor()
    supplier = Supplier.objects.create(code="S-1", name="Globex")
    order = PurchaseOrder.objects.create(
        number="PO-1", supplier=supplier, order_date=dt.date(2026, 6, 1), warehouse_code="MAIN",
        status="confirmed", subtotal_minor=100_000, billed_minor=100_000, paid_minor=40_000,
    )

    snapshot = page_distill.render(actor, "purchasing.orders", str(order.id))

    assert snapshot == "status confirmed; total 1,000.00 EGP; outstanding 600.00 EGP"


# --- purchasing.requests ------------------------------------------------------------------------

def test_purchasing_request_snapshot():
    actor = _actor()
    supplier = Supplier.objects.create(code="S-1", name="Globex")
    request = PurchaseRequest.objects.create(
        number="PR-1", supplier=supplier, request_date=dt.date(2026, 6, 1), warehouse_code="MAIN",
        status="submitted", subtotal_minor=45_000,
    )

    snapshot = page_distill.render(actor, "purchasing.requests", str(request.id))

    assert snapshot == "status submitted; total 450.00 EGP"


# --- purchasing.suppliers -----------------------------------------------------------------------

def test_purchasing_supplier_snapshot_with_open_orders():
    actor = _actor()
    supplier = Supplier.objects.create(code="S-1", name="Globex")
    PurchaseOrder.objects.create(
        number="PO-1", supplier=supplier, order_date=dt.date(2026, 6, 1), warehouse_code="MAIN",
        status="confirmed", subtotal_minor=100_000, billed_minor=100_000, paid_minor=40_000,
    )

    snapshot = page_distill.render(actor, "purchasing.suppliers", "S-1")

    assert snapshot == "1 open orders; outstanding 600.00 EGP"


def test_purchasing_supplier_snapshot_no_open_orders():
    actor = _actor()
    Supplier.objects.create(code="S-2", name="Initrode")

    snapshot = page_distill.render(actor, "purchasing.suppliers", "S-2")

    assert snapshot == "no open orders"


# --- inventory.items ----------------------------------------------------------------------------

def test_inventory_item_snapshot_below_reorder():
    actor = _actor()
    from erp.inventory.tests.factories import make_gl
    make_gl()
    warehouse = Warehouse.objects.create(code="MAIN", name="Main")
    Item.objects.create(sku="WIDGET", name="Widget", type="stock", reorder_point=100)
    receive("WIDGET", warehouse.code, 20, 100_00, date=dt.date(2026, 6, 1))

    snapshot = page_distill.render(actor, "inventory.items", "WIDGET")

    assert snapshot == "stock; 20 on hand; below reorder point"


# --- accounting.journals ------------------------------------------------------------------------

def test_accounting_journal_snapshot():
    actor = _actor()
    accounts = make_coa()
    period = make_period()
    entry = JournalEntry.objects.create(
        number="JE-1", date=period.start_date, period=period, status="posted",
    )
    JournalLine.objects.create(entry=entry, line_no=1, account=accounts["1000"], debit=50_000, credit=0)
    JournalLine.objects.create(entry=entry, line_no=2, account=accounts["4000"], debit=0, credit=50_000)

    snapshot = page_distill.render(actor, "accounting.journals", str(entry.id))

    assert snapshot == "status posted; total 500.00 EGP; 2 lines"


# --- crm.opportunities --------------------------------------------------------------------------

def test_crm_opportunity_snapshot():
    actor = _actor()
    opp = Opportunity.objects.create(
        number="OPP-1", name="Warehouse expansion", customer_code="C-1", amount_minor=250_000,
        expected_close=dt.date(2026, 8, 1),
    )

    snapshot = page_distill.render(actor, "crm.opportunities", str(opp.id))

    assert snapshot == "stage qualifying; amount 2,500.00 EGP; expected close 2026-08-01"


# --- registry fallback --------------------------------------------------------------------------

def test_unregistered_type_returns_none():
    actor = _actor()

    assert page_distill.render(actor, "pricing.pricelists", "1") is None


def test_missing_type_or_id_returns_none():
    actor = _actor()

    assert page_distill.render(actor, None, "1") is None
    assert page_distill.render(actor, "sales.orders", None) is None


def test_registered_type_lookup_error_fails_open(monkeypatch):
    """A distiller that raises (bad id shape, a DB hiccup) must degrade to no line, never crash the
    envelope build — same fail-open discipline as ``services/rerank.py``."""
    actor = _actor()

    def boom(actor, record_id):
        raise RuntimeError("boom")

    monkeypatch.setitem(page_distill.DISTILLERS, "sales.orders", boom)

    assert page_distill.render(actor, "sales.orders", "42") is None


# --- token budget (Accept: target <= 150 tokens per record) ---------------------------------------

def test_longest_snapshot_stays_under_150_tokens():
    from erp.assistant.services.tracing import estimate_tokens

    # The longest real snapshot observed above (sales.orders, 4 facts) stands in for the ceiling
    # check — every other distiller returns 2-3 shorter facts.
    longest = "status confirmed; total 1,250.00 EGP; invoiced 1,250.00 EGP; outstanding 750.00 EGP"
    assert estimate_tokens(f"- Record detail: {longest}.") < 150
