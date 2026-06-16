"""Input (purchase) VAT — booked as recoverable at bill, reversed on a debit note, and netted
against output VAT in the VAT return."""
from __future__ import annotations

from decimal import Decimal

import pytest

from erp.accounting.services import (
    JournalInput,
    LineInput,
    general_ledger,
    post_journal,
    trial_balance,
    vat_return,
)
from erp.purchasing.domain.models import POStatus
from erp.purchasing.services import (
    POLineInput,
    bill_order,
    confirm_order,
    create_order,
    pay_order,
    receive_order,
    return_order,
)

from .factories import (
    DATE,
    YEAR_END,
    YEAR_START,
    make_books,
    make_item,
    make_supplier,
    make_warehouse,
)

pytestmark = pytest.mark.django_db


def _setup():
    make_books()
    make_item()
    return make_supplier(), make_warehouse()


def _taxed_po(supplier, wh, qty="10", cost=100_00):
    return create_order(
        supplier=supplier, warehouse_code=wh.code, order_date=DATE, tax_code="VAT14",
        lines=[POLineInput(item_sku="WIDGET", quantity=Decimal(qty), unit_cost_minor=cost)],
    )


def test_bill_books_recoverable_input_vat():
    supplier, wh = _setup()
    order = _taxed_po(supplier, wh)
    confirm_order(order)
    receive_order(order)
    bill_order(order)
    order.refresh_from_db()

    # Net 1,000.00 + 14% VAT 140.00 = gross 1,140.00.
    assert order.tax_minor == 140_00
    assert order.billed_minor == 1140_00
    assert order.outstanding_minor == 1140_00
    # Dr GRNI 1,000 / Dr VAT Input 140 / Cr AP 1,140.
    assert general_ledger("2150").closing_balance == 0          # GRNI cleared
    assert general_ledger("1190").closing_balance == 140_00     # recoverable input VAT (asset)
    assert general_ledger("2000").closing_balance == 1140_00    # AP owes gross
    assert trial_balance().is_balanced

    pay_order(order, 1140_00)
    order.refresh_from_db()
    assert order.status == POStatus.PAID
    assert general_ledger("2000").closing_balance == 0
    assert trial_balance().is_balanced


def test_untaxed_bill_books_no_input_vat():
    supplier, wh = _setup()
    order = create_order(
        supplier=supplier, warehouse_code=wh.code, order_date=DATE,
        lines=[POLineInput(item_sku="WIDGET", quantity=Decimal("10"), unit_cost_minor=100_00)],
    )
    confirm_order(order)
    receive_order(order)
    bill_order(order)
    order.refresh_from_db()
    assert order.tax_minor == 0
    assert order.billed_minor == 1000_00
    assert general_ledger("1190").closing_balance == 0


def test_debit_note_reverses_input_vat():
    supplier, wh = _setup()
    order = _taxed_po(supplier, wh)
    confirm_order(order)
    receive_order(order)
    bill_order(order)
    return_order(order)  # full supplier return
    order.refresh_from_db()

    assert order.status == POStatus.RETURNED
    # Input VAT, AP and GRNI all net back to zero after the debit note.
    assert general_ledger("1190").closing_balance == 0
    assert general_ledger("2000").closing_balance == 0
    assert general_ledger("2150").closing_balance == 0
    assert trial_balance().is_balanced


def test_vat_return_nets_output_minus_input():
    supplier, wh = _setup()
    # An output (sales) VAT posting: Cr VAT Payable 200.00 (Dr Cash).
    post_journal(JournalInput(
        date=DATE, source="sales", reference="INV1", memo="sale",
        lines=[LineInput(account_code="1000", debit=200_00),
               LineInput(account_code="2100", credit=200_00)],
    ))
    # A taxed purchase: input VAT 140.00 recoverable.
    order = _taxed_po(supplier, wh)
    confirm_order(order)
    receive_order(order)
    bill_order(order)

    vr = vat_return(YEAR_START, YEAR_END)
    assert vr.output_vat == 200_00
    assert vr.input_vat == 140_00
    assert vr.input_reversals == 0
    assert vr.net_payable == 60_00      # 200 collected − 140 recoverable
    assert vr.is_payable
