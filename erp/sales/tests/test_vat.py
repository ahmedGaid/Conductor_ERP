"""Sales VAT — invoice posts net + output VAT; returns reverse VAT; the books stay balanced."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

YEAR_START = dt.date(2026, 1, 1)
YEAR_END = dt.date(2026, 12, 31)

from erp.accounting.services import general_ledger, trial_balance, vat_return
from erp.sales.domain.models import OrderStatus
from erp.sales.errors import UnknownTaxCodeError
from erp.sales.services import (
    OrderLineInput,
    confirm_order,
    create_order,
    deliver_order,
    invoice_order,
    receive_payment,
    return_order,
)

from .factories import DATE, make_books, make_customer, make_item, make_vat, make_warehouse, stocked

pytestmark = pytest.mark.django_db


def _setup():
    make_books()
    make_vat()
    item = make_item()
    wh = make_warehouse()
    stocked(item, wh)  # 20 @ 100.00
    return make_customer(), wh


def _order(customer, wh, tax_code="VAT14", qty="10", price=150_00):
    return create_order(
        customer=customer, warehouse_code=wh.code, order_date=DATE, tax_code=tax_code,
        lines=[OrderLineInput(item_sku="WIDGET", quantity=Decimal(qty), unit_price_minor=price)],
    )


def test_invoice_posts_net_revenue_and_output_vat():
    customer, wh = _setup()
    order = _order(customer, wh)  # net 1,500.00
    confirm_order(order)
    deliver_order(order)
    invoice_order(order)
    order.refresh_from_db()

    assert order.tax_minor == 210_00          # 14% of 1,500.00
    assert order.invoiced_minor == 1710_00    # gross = net + VAT
    assert order.outstanding_minor == 1710_00
    assert general_ledger("1100").closing_balance == 1710_00  # AR = gross
    assert general_ledger("4000").closing_balance == 1500_00  # Revenue = net
    assert general_ledger("2100").closing_balance == 210_00   # VAT Payable
    assert trial_balance().is_balanced


def test_payment_settles_gross_then_vat_return():
    customer, wh = _setup()
    order = _order(customer, wh)
    confirm_order(order)
    deliver_order(order)
    invoice_order(order)
    receive_payment(order, 1710_00)
    order.refresh_from_db()
    assert order.status == OrderStatus.PAID
    assert general_ledger("1100").closing_balance == 0

    vr = vat_return(YEAR_START, YEAR_END)
    assert vr.output_vat == 210_00
    assert vr.net_payable == 210_00


def test_return_reverses_vat_proportionally():
    customer, wh = _setup()
    order = _order(customer, wh)  # net 1,500.00, VAT 210.00
    confirm_order(order)
    deliver_order(order)
    invoice_order(order)
    # Return 4 of 10 → net 600.00, VAT 84.00 reversed.
    return_order(order, returned={1: Decimal("4")})
    order.refresh_from_db()
    assert order.returned_minor == 600_00
    assert order.outstanding_minor == 1710_00 - 600_00 - 84_00  # gross reduced by net+vat
    assert general_ledger("2100").closing_balance == 210_00 - 84_00  # VAT net of reversal
    assert trial_balance().is_balanced

    vr = vat_return(YEAR_START, YEAR_END)
    assert vr.output_vat == 210_00
    assert vr.reversals == 84_00
    assert vr.net_payable == 126_00


def test_no_tax_code_path_unchanged():
    customer, wh = _setup()
    order = _order(customer, wh, tax_code="")  # untaxed
    confirm_order(order)
    deliver_order(order)
    invoice_order(order)
    order.refresh_from_db()
    assert order.tax_minor == 0
    assert order.invoiced_minor == 1500_00
    assert general_ledger("2100").closing_balance == 0
    assert trial_balance().is_balanced


def test_unknown_tax_code_rejected():
    customer, wh = _setup()
    with pytest.raises(UnknownTaxCodeError):
        _order(customer, wh, tax_code="NOPE")
