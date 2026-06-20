"""Approval-limit enforcement (Increment 6) — sales approve gates honour the role's ApprovalLimit.

An authenticated, non-admin approver may only sign off up to their role's ApprovalLimit for the
document type; a system/no-actor call and superuser/System Admin are unrestricted.
"""
from __future__ import annotations

import pytest
from django.contrib.auth.models import Group

from erp.identity.models import ApprovalLimit, User
from erp.identity.roles import BRANCH_MANAGER
from erp.sales import services
from erp.sales.domain.models import Customer
from erp.sales.errors import ApprovalLimitExceededError

from .factories import make_books, make_item, make_warehouse

pytestmark = pytest.mark.django_db

UNSET = object()


def _manager(username: str, *, doc: str, limit=UNSET) -> User:
    bm, _ = Group.objects.get_or_create(name=BRANCH_MANAGER)
    if limit is not UNSET:
        ApprovalLimit.objects.update_or_create(role=bm, document_type=doc, defaults={"limit_minor": limit})
    u = User.objects.create_user(username=username, email=f"{username}@erp.local", password="pw12345!")
    u.groups.add(bm)
    return u


def _setup():
    make_books()
    make_item()
    make_warehouse()


def _order(price_minor: int):
    cust, _ = Customer.objects.get_or_create(code="C1", defaults={"name": "Acme"})
    return services.create_order(
        customer=cust, warehouse_code="MAIN", currency="EGP",
        lines=[services.OrderLineInput(item_sku="WIDGET", quantity=1, unit_price_minor=price_minor)],
    )


def test_within_limit_approves():
    _setup()
    mgr = _manager("mgr", doc="sales_order", limit=500_00)  # 50,000 minor ceiling
    order = _order(100_00)  # subtotal 10,000 minor <= ceiling
    services.approve_order(order, actor=mgr)
    order.refresh_from_db()
    assert order.approved is True


def test_over_limit_blocked():
    _setup()
    mgr = _manager("mgr", doc="sales_order", limit=500_00)
    order = _order(1000_00)  # subtotal 100,000 minor > ceiling
    with pytest.raises(ApprovalLimitExceededError):
        services.approve_order(order, actor=mgr)
    order.refresh_from_db()
    assert order.approved is False


def test_unlimited_role_approves_any():
    _setup()
    mgr = _manager("mgr", doc="sales_order", limit=None)  # explicit unlimited
    order = _order(1000_00)
    services.approve_order(order, actor=mgr)
    order.refresh_from_db()
    assert order.approved is True


def test_no_actor_and_superuser_unrestricted():
    _setup()
    # No actor (system/seed context) — never limit-checked, even with no role rows present.
    o1 = _order(1000_00)
    services.approve_order(o1, actor=None)
    o1.refresh_from_db()
    assert o1.approved is True
    # Superuser bypasses the limit.
    su = User.objects.create_user(username="root", email="root@erp.local", password="pw")
    su.is_superuser = True
    su.save(update_fields=["is_superuser"])
    o2 = _order(1000_00)
    services.approve_order(o2, actor=su)
    o2.refresh_from_db()
    assert o2.approved is True


def test_quotation_approve_is_limit_checked():
    _setup()
    mgr = _manager("mgr", doc="quotation", limit=1_500_000)  # 15,000.00 EGP ceiling
    cust, _ = Customer.objects.get_or_create(code="C1", defaults={"name": "Acme"})
    # Above the auto-approve threshold (1,000,000 minor) so it lands in SUBMITTED awaiting approval.
    quote = services.create_quotation(
        customer=cust, warehouse_code="MAIN", currency="EGP",
        lines=[services.QuoteLineInput(item_sku="WIDGET", quantity=1, unit_price_minor=20_000_00)],
    )
    services.submit_quotation(quote)
    with pytest.raises(ApprovalLimitExceededError):
        services.approve_quotation(quote, actor=mgr)
