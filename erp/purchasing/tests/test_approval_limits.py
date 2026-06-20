"""Approval-limit enforcement (Increment 6) — purchasing approve gates honour the role's ApprovalLimit.

An authenticated, non-admin approver may only sign off up to their role's ApprovalLimit for the
document type; a system/no-actor call and superuser/System Admin are unrestricted.
"""
from __future__ import annotations

import pytest
from django.contrib.auth.models import Group

from erp.identity.models import ApprovalLimit, User
from erp.identity.roles import BRANCH_MANAGER
from erp.purchasing import services
from erp.purchasing.domain.models import Supplier
from erp.purchasing.errors import ApprovalLimitExceededError

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


def _supplier() -> Supplier:
    return Supplier.objects.get_or_create(code="SUP1", defaults={"name": "Globex"})[0]


def _po(cost_minor: int):
    supplier = _supplier()
    return services.create_order(
        supplier=supplier, warehouse_code="MAIN", currency="EGP",
        lines=[services.POLineInput(item_sku="WIDGET", quantity=1, unit_cost_minor=cost_minor)],
    )


def test_within_limit_approves():
    _setup()
    mgr = _manager("buy", doc="purchase_order", limit=500_00)
    po = _po(100_00)
    services.approve_order(po, actor=mgr)
    po.refresh_from_db()
    assert po.approved is True


def test_over_limit_blocked():
    _setup()
    mgr = _manager("buy", doc="purchase_order", limit=500_00)
    po = _po(1000_00)
    with pytest.raises(ApprovalLimitExceededError):
        services.approve_order(po, actor=mgr)
    po.refresh_from_db()
    assert po.approved is False


def test_no_actor_and_superuser_unrestricted():
    _setup()
    o1 = _po(1000_00)
    services.approve_order(o1, actor=None)
    o1.refresh_from_db()
    assert o1.approved is True
    su = User.objects.create_user(username="root", email="root@erp.local", password="pw")
    su.is_superuser = True
    su.save(update_fields=["is_superuser"])
    o2 = _po(1000_00)
    services.approve_order(o2, actor=su)
    o2.refresh_from_db()
    assert o2.approved is True


def test_request_approve_is_limit_checked():
    _setup()
    mgr = _manager("buy", doc="purchase_request", limit=1_500_000)  # 15,000.00 EGP ceiling
    supplier = _supplier()
    # Above the auto-approve threshold (1,000,000 minor) so it lands in SUBMITTED awaiting approval.
    req = services.create_request(
        supplier=supplier, warehouse_code="MAIN", currency="EGP",
        lines=[services.RequestLineInput(item_sku="WIDGET", quantity=1, unit_cost_minor=20_000_00)],
    )
    services.submit_request(req)
    with pytest.raises(ApprovalLimitExceededError):
        services.approve_request(req, actor=mgr)
