"""Sales order lifecycle — the cross-module order-to-cash flow."""
from __future__ import annotations

from decimal import Decimal

import pytest

from erp.accounting.services import general_ledger, trial_balance
from erp.inventory.errors import InsufficientStockError
from erp.inventory.repositories import balances as balance_repo
from erp.sales.domain.models import OrderStatus
from erp.sales.errors import CreditLimitExceededError, OverpaymentError
from erp.sales.services import (
    OrderLineInput,
    complete_sale,
    confirm_order,
    create_order,
    deliver_order,
    invoice_order,
    receive_payment,
)

from .factories import DATE, make_books, make_customer, make_item, make_warehouse, stocked

pytestmark = pytest.mark.django_db


def _order(customer, warehouse, qty="10", price=150_00):
    return create_order(
        customer=customer, warehouse_code=warehouse.code, order_date=DATE,
        lines=[OrderLineInput(item_sku="WIDGET", quantity=Decimal(qty), unit_price_minor=price)],
    )


def _setup(credit_limit_minor=0):
    make_books()
    item = make_item()
    wh = make_warehouse()
    stocked(item, wh)  # 20 @ 100.00
    return make_customer(credit_limit_minor=credit_limit_minor), wh


def test_full_order_to_cash_flow_keeps_books_balanced():
    customer, wh = _setup()
    order = _order(customer, wh)
    assert order.status == OrderStatus.DRAFT
    assert order.subtotal_minor == 1500_00

    confirm_order(order)
    assert order.status == OrderStatus.CONFIRMED

    deliver_order(order)
    assert order.status == OrderStatus.DELIVERED
    # Stock reduced 20 -> 10; COGS posted at avg cost (100.00 * 10 = 1000.00)
    assert balance_repo.total_value() == 1000_00
    assert general_ledger("5000").closing_balance == 1000_00

    invoice_order(order)
    assert order.status == OrderStatus.INVOICED
    assert order.invoice_number
    assert general_ledger("1100").closing_balance == 1500_00  # AR
    assert general_ledger("4000").closing_balance == 1500_00  # Revenue

    receive_payment(order, 1500_00)
    assert order.status == OrderStatus.PAID
    assert order.outstanding_minor == 0
    assert general_ledger("1100").closing_balance == 0  # AR settled

    assert trial_balance().is_balanced


def test_inventory_gl_matches_stock_value_after_delivery():
    customer, wh = _setup()
    order = _order(customer, wh)
    confirm_order(order)
    deliver_order(order)
    assert general_ledger("1200").closing_balance == balance_repo.total_value()


def test_credit_limit_blocks_confirm():
    customer, wh = _setup(credit_limit_minor=1000_00)  # order is 1500.00
    order = _order(customer, wh)
    with pytest.raises(CreditLimitExceededError):
        confirm_order(order)
    order.refresh_from_db()
    assert order.status == OrderStatus.DRAFT


def test_delivery_beyond_stock_is_rejected():
    customer, wh = _setup()
    order = _order(customer, wh, qty="50")  # only 20 on hand
    confirm_order(order)
    with pytest.raises(InsufficientStockError):
        deliver_order(order)
    order.refresh_from_db()
    assert order.status == OrderStatus.CONFIRMED
    assert balance_repo.total_value() == 2000_00  # untouched


def test_partial_payment_then_full():
    customer, wh = _setup()
    order = _order(customer, wh)
    confirm_order(order)
    deliver_order(order)
    invoice_order(order)

    receive_payment(order, 500_00)
    assert order.status == OrderStatus.INVOICED
    assert order.outstanding_minor == 1000_00

    receive_payment(order, 1000_00)
    assert order.status == OrderStatus.PAID


def test_overpayment_rejected():
    customer, wh = _setup()
    order = _order(customer, wh)
    confirm_order(order)
    deliver_order(order)
    invoice_order(order)
    with pytest.raises(OverpaymentError):
        receive_payment(order, 2000_00)


def test_unknown_item_rejected_on_create():
    from erp.sales.errors import UnknownItemError

    customer, wh = _setup()
    with pytest.raises(UnknownItemError):
        create_order(
            customer=customer, warehouse_code=wh.code, order_date=DATE,
            lines=[OrderLineInput(item_sku="NOPE", quantity=Decimal("1"), unit_price_minor=100)],
        )


def test_cancel_order_allowed_in_draft_and_confirmed_blocked_after():
    from erp.sales.errors import InvalidTransitionError
    from erp.sales.services import cancel_order

    customer, wh = _setup()

    # Draft is cancellable.
    o1 = _order(customer, wh)
    cancel_order(o1)
    assert o1.status == OrderStatus.CANCELLED

    # Confirmed is cancellable (default policy "confirmed").
    o2 = _order(customer, wh)
    confirm_order(o2)
    cancel_order(o2)
    assert o2.status == OrderStatus.CANCELLED

    # Past delivery (a side-effecting state) is never cancellable.
    o3 = _order(customer, wh)
    confirm_order(o3)
    deliver_order(o3)
    with pytest.raises(InvalidTransitionError):
        cancel_order(o3)


def test_complete_sale_drives_draft_to_invoiced_in_one_move():
    customer, wh = _setup()
    order = _order(customer, wh)

    complete_sale(order)
    assert order.status == OrderStatus.INVOICED
    assert order.invoice_number
    # Books posted exactly as the granular path would: stock issued, AR + Revenue booked.
    assert balance_repo.total_value() == 1000_00
    assert general_ledger("1100").closing_balance == 1500_00  # AR
    assert general_ledger("4000").closing_balance == 1500_00  # Revenue
    assert trial_balance().is_balanced
    # Stops short of payment — the money is recorded separately.
    assert order.outstanding_minor == 1500_00


def test_complete_sale_blocked_when_approval_required():
    from erp.sales.errors import ApprovalRequiredError

    customer, wh = _setup()
    order = _order(customer, wh, qty="100", price=150_00)  # 15,000.00 > 10,000.00 threshold
    with pytest.raises(ApprovalRequiredError):
        complete_sale(order)
    order.refresh_from_db()
    assert order.status == OrderStatus.DRAFT  # atomic rollback — nothing moved


def test_cancel_order_respects_org_policy():
    from erp.identity.models import OrgPreferences
    from erp.sales.errors import InvalidTransitionError
    from erp.sales.services import cancel_order

    OrgPreferences.objects.update_or_create(pk=1, defaults={"order_cancel_until": "draft"})
    customer, wh = _setup()

    # With "draft" policy, a confirmed order is no longer cancellable.
    o = _order(customer, wh)
    confirm_order(o)
    with pytest.raises(InvalidTransitionError):
        cancel_order(o)
