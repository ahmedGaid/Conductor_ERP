"""Admin-configured approval ceilings on vendor bill + payment (opt-in).

A role is unrestricted unless an admin sets an 'invoice'/'payment' limit for it (in the role editor);
a configured ceiling below the amount blocks the action. Runs under gate08 (erp/purchasing/tests).
"""
from __future__ import annotations

import pytest
from django.contrib.auth.models import Group

from erp.identity.models import ApprovalLimit, User
from erp.identity.roles import BRANCH_MANAGER
from erp.purchasing import services
from erp.purchasing.errors import ApprovalLimitExceededError

from .factories import make_books, make_item, make_supplier, make_warehouse

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


def _received_order(actor):
    make_item()
    make_warehouse()
    sup = make_supplier()
    order = services.create_order(
        supplier=sup, warehouse_code="MAIN", currency="EGP",
        lines=[services.POLineInput(item_sku="WIDGET", quantity=10, unit_cost_minor=100_00)],
        actor=actor,
    )  # 1,000.00 (below confirm-approval threshold)
    services.confirm_order(order, actor=actor)
    services.receive_order(order, actor=actor)  # full receipt → 3-way match passes
    return order


def test_bill_unrestricted_without_a_configured_limit():
    make_books()
    bm = _bm("buy_free")
    order = _received_order(bm)
    services.bill_order(order, actor=bm)
    assert order.status == "billed"


def test_bill_blocked_when_over_configured_limit():
    make_books()
    bm = _bm("buy_capped")
    order = _received_order(bm)
    _set_limit("invoice", 50_000)  # 500.00 ceiling; this bill is 1,000.00
    with pytest.raises(ApprovalLimitExceededError):
        services.bill_order(order, actor=bm)


def test_payment_blocked_over_limit_then_within_ok():
    make_books()
    bm = _bm("buy_pay")
    order = _received_order(bm)
    services.bill_order(order, actor=bm)  # billed unrestricted
    _set_limit("payment", 40_000)  # 400.00 ceiling
    with pytest.raises(ApprovalLimitExceededError):
        services.pay_order(order, 100_000, actor=bm)
    services.pay_order(order, 30_000, actor=bm)
    assert order.paid_minor == 30_000
