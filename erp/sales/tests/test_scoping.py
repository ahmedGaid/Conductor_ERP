"""Data-scope enforcement (Increment 5) — sales.

Proves the whole chain: create_order stamps the actor's branch; scope_queryset narrows a
BRANCH-scoped manager's queryset to their own branch (plus unstamped/NULL records); and the live
/api/sales/orders list applies it. Also exercises the helper's ALL / OWN / superadmin paths.
"""
from __future__ import annotations

import pytest
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from erp.core.models import Branch
from erp.identity.models import Department, RolePermission, User
from erp.identity.roles import BRANCH_MANAGER
from erp.identity.scoping import scope_queryset
from erp.sales import services
from erp.sales.domain.models import Customer, SalesOrder

from .factories import make_books, make_item, make_warehouse

pytestmark = pytest.mark.django_db

VIEW = "sales.order.view"


def _catalog():
    make_books()
    make_item()
    make_warehouse()


def _manager(username: str, branch: Branch | None, scope: str = "branch",
             department: Department | None = None) -> User:
    bm, _ = Group.objects.get_or_create(name=BRANCH_MANAGER)
    RolePermission.objects.update_or_create(role=bm, code=VIEW, defaults={"scope": scope})
    u = User.objects.create_user(username=username, email=f"{username}@erp.local", password="pw12345!")
    u.branch = branch
    u.department = department
    u.save(update_fields=["branch", "department"])
    u.groups.add(bm)
    return u


def _order(actor) -> SalesOrder:
    customer, _ = Customer.objects.get_or_create(code="CUST1", defaults={"name": "Acme"})
    return services.create_order(
        customer=customer, warehouse_code="MAIN", currency="EGP",
        lines=[services.OrderLineInput(item_sku="WIDGET", quantity=1, unit_price_minor=100_00)],
        actor=actor,
    )


def test_create_stamps_actor_branch():
    _catalog()
    branch = Branch.objects.create(code="BR-A", name="Alpha")
    mgr = _manager("mgr_a", branch)
    order = _order(mgr)
    assert order.branch_id == branch.id
    assert order.created_by_id == mgr.id


def test_branch_scope_isolates_other_branch_but_keeps_null():
    _catalog()
    a = Branch.objects.create(code="BR-A", name="Alpha")
    b = Branch.objects.create(code="BR-B", name="Beta")
    mgr_a = _manager("mgr_a", a)
    mgr_b = _manager("mgr_b", b)

    order_a = _order(mgr_a)
    order_b = _order(mgr_b)
    # An unstamped (legacy / system) order stays visible to every branch.
    order_null = SalesOrder.objects.create(number="SO-NULL", customer=order_a.customer,
                                           order_date=order_a.order_date, warehouse_code="MAIN")

    seen_by_a = set(scope_queryset(mgr_a, SalesOrder.objects.all(), VIEW).values_list("id", flat=True))
    assert seen_by_a == {order_a.id, order_null.id}
    assert order_b.id not in seen_by_a


def test_department_scope_narrows_within_a_branch():
    # Two managers in the SAME branch but different departments; DEPARTMENT scope must isolate them
    # from each other (proving it filters finer than branch).
    _catalog()
    branch = Branch.objects.create(code="BR-A", name="Alpha")
    dept_x = Department.objects.create(code="DX", name="Dept X", branch=branch)
    dept_y = Department.objects.create(code="DY", name="Dept Y", branch=branch)
    mgr_x = _manager("dx", branch, scope="department", department=dept_x)
    mgr_y = _manager("dy", branch, scope="department", department=dept_y)

    order_x = _order(mgr_x)
    order_y = _order(mgr_y)
    order_null = SalesOrder.objects.create(number="SO-NULL", customer=order_x.customer,
                                           order_date=order_x.order_date, warehouse_code="MAIN")

    assert order_x.department_id == dept_x.id
    seen = set(scope_queryset(mgr_x, SalesOrder.objects.all(), VIEW).values_list("id", flat=True))
    assert seen == {order_x.id, order_null.id}
    assert order_y.id not in seen  # same branch, different department — hidden


def test_all_and_own_and_superadmin_paths():
    # Scope is held on the role (Group), so set it on the shared Branch Manager group per assertion.
    _catalog()
    a = Branch.objects.create(code="BR-A", name="Alpha")
    u1 = _manager("u1", a)
    u2 = _manager("u2", a)
    o1 = _order(u1)
    _order(u2)
    bm = Group.objects.get(name=BRANCH_MANAGER)

    def set_scope(s: str) -> None:
        RolePermission.objects.update_or_create(role=bm, code=VIEW, defaults={"scope": s})

    set_scope("all")
    assert scope_queryset(u1, SalesOrder.objects.all(), VIEW).count() == 2

    set_scope("own")
    own_seen = set(scope_queryset(u1, SalesOrder.objects.all(), VIEW).values_list("id", flat=True))
    assert own_seen == {o1.id}

    su = User.objects.create_user(username="root", email="root@erp.local", password="pw")
    su.is_superuser = True
    su.save(update_fields=["is_superuser"])
    assert scope_queryset(su, SalesOrder.objects.all(), VIEW).count() == 2


def test_orders_list_endpoint_is_branch_scoped():
    _catalog()
    a = Branch.objects.create(code="BR-A", name="Alpha")
    b = Branch.objects.create(code="BR-B", name="Beta")
    mgr_a = _manager("mgr_a", a)
    mgr_b = _manager("mgr_b", b)
    order_a = _order(mgr_a)
    _order(mgr_b)

    client = APIClient()
    client.force_authenticate(user=mgr_a)
    rows = client.get("/api/sales/orders").data["data"]
    assert len(rows) == 1  # only branch A's order
    assert rows[0]["number"] == order_a.number
