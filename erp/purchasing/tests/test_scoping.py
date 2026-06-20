"""Data-scope enforcement (Increment 5) — purchasing.

create_order stamps the actor's branch; scope_queryset isolates a BRANCH-scoped manager to their
own branch while leaving unstamped/NULL records visible.
"""
from __future__ import annotations

import pytest
from django.contrib.auth.models import Group

from erp.core.models import Branch
from erp.identity.models import RolePermission, User
from erp.identity.roles import BRANCH_MANAGER
from erp.identity.scoping import scope_queryset
from erp.purchasing import services
from erp.purchasing.domain.models import PurchaseOrder

from .factories import make_books, make_item, make_supplier, make_warehouse

pytestmark = pytest.mark.django_db

VIEW = "purchasing.order.view"


def _manager(username: str, branch: Branch) -> User:
    bm, _ = Group.objects.get_or_create(name=BRANCH_MANAGER)
    RolePermission.objects.update_or_create(role=bm, code=VIEW, defaults={"scope": "branch"})
    u = User.objects.create_user(username=username, email=f"{username}@erp.local", password="pw12345!")
    u.branch = branch
    u.save(update_fields=["branch"])
    u.groups.add(bm)
    return u


def _po(actor, supplier) -> PurchaseOrder:
    return services.create_order(
        supplier=supplier, warehouse_code="MAIN", currency="EGP",
        lines=[services.POLineInput(item_sku="WIDGET", quantity=1, unit_cost_minor=100_00)],
        actor=actor,
    )


def test_branch_scope_isolates_purchase_orders():
    make_books()
    make_item()
    make_warehouse()
    supplier = make_supplier()
    a = Branch.objects.create(code="BR-A", name="Alpha")
    b = Branch.objects.create(code="BR-B", name="Beta")
    mgr_a = _manager("buy_a", a)
    mgr_b = _manager("buy_b", b)

    po_a = _po(mgr_a, supplier)
    po_b = _po(mgr_b, supplier)
    po_null = PurchaseOrder.objects.create(number="PO-NULL", supplier=supplier,
                                           order_date=po_a.order_date, warehouse_code="MAIN")

    assert po_a.branch_id == a.id
    seen = set(scope_queryset(mgr_a, PurchaseOrder.objects.all(), VIEW).values_list("id", flat=True))
    assert seen == {po_a.id, po_null.id}
    assert po_b.id not in seen
