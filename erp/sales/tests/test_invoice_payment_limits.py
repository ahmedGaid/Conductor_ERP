"""Admin-configured approval ceilings on invoice + payment (opt-in).

A role is unrestricted unless an admin sets an 'invoice'/'payment' limit for it (in the role editor);
a configured ceiling below the amount blocks the action. Runs under gate07 (erp/sales/tests).
"""
from __future__ import annotations

import pytest
from django.contrib.auth.models import Group

from erp.identity.models import ApprovalLimit, User
from erp.identity.roles import BRANCH_MANAGER
from erp.sales import services
from erp.sales.errors import ApprovalLimitExceededError

from .factories import make_books, make_customer, make_item, make_warehouse, stocked

pytestmark = pytest.mark.django_db


def _bm(username: str) -> User:
    g, _ = Group.objects.get_or_create(name=BRANCH_MANAGER)
    u = User.objects.create_user(username=username, email=f"{username}@erp.local", password="pw12345!")
    u.groups.add(g)
    return u


def _set_limit(document_type: str, limit_minor) -> None:
    g, _ = Group.objects.get_or_create(name=BRANCH_MANAGER)
    ApprovalLimit.objects.update_or_create(
        role=g, document_type=document_type, defaults={"limit_minor": limit_minor}
    )


def _delivered_order(actor):
    item = make_item()
    wh = make_warehouse()
    stocked(item, wh)
    cust = make_customer()
    order = services.create_order(
        customer=cust, warehouse_code="MAIN", currency="EGP",
        lines=[services.OrderLineInput(item_sku="WIDGET", quantity=10, unit_price_minor=100_00)],
        actor=actor,
    )  # subtotal 1,000.00 (below the confirm-approval threshold, so confirm needs no sign-off)
    services.confirm_order(order, actor=actor)
    services.deliver_order(order, actor=actor)
    return order


def test_invoice_unrestricted_without_a_configured_limit():
    make_books()
    bm = _bm("bm_free")
    order = _delivered_order(bm)
    services.invoice_order(order, actor=bm)  # no invoice limit set → allowed
    assert order.status == "invoiced"


def test_invoice_blocked_when_over_configured_limit():
    make_books()
    bm = _bm("bm_capped")
    order = _delivered_order(bm)
    _set_limit("invoice", 50_000)  # 500.00 ceiling; this invoice is 1,000.00
    with pytest.raises(ApprovalLimitExceededError):
        services.invoice_order(order, actor=bm)


def test_payment_blocked_over_limit_then_within_ok():
    make_books()
    bm = _bm("bm_pay")
    order = _delivered_order(bm)
    services.invoice_order(order, actor=bm)  # invoiced unrestricted
    _set_limit("payment", 40_000)  # 400.00 ceiling
    with pytest.raises(ApprovalLimitExceededError):
        services.receive_payment(order, 100_000, actor=bm)  # 1,000.00 payment over the ceiling
    services.receive_payment(order, 30_000, actor=bm)  # within the ceiling
    assert order.paid_minor == 30_000
