"""Bounded structured-query tool ``query_data`` (session 08 Task E).

The registry is the security boundary, so the refusals are tested as carefully as the happy paths:
an off-registry entity, an off-registry filter/group field, and a scoped user proving branch-scope
still narrows the rows. Everything runs through ``TOOLS["query_data"].run`` exactly as the router
dispatches it — real ORM, real ``scope_queryset``, no model/network hop.
"""
from __future__ import annotations

import datetime

import pytest
from django.contrib.auth.models import Group

from erp.assistant.query_registry import (
    _BAD_FIELD,
    _BAD_METRIC,
    _DENIED,
    _OFF_REGISTRY,
)
from erp.assistant.tools import TOOLS
from erp.core.models import Branch
from erp.identity.models import RolePermission, User
from erp.identity.roles import BRANCH_MANAGER
from erp.inventory.domain.models import Item
from erp.purchasing.domain.models import PurchaseOrder, Supplier
from erp.sales.domain.models import Customer, SalesOrder

pytestmark = pytest.mark.django_db

TODAY = datetime.date.today()


def _q(actor, **kwargs) -> dict:
    return TOOLS["query_data"].run(actor, **kwargs)


def _admin() -> User:
    u = User.objects.create_user(username="q_admin", password="Dev12345!", email="qa@example.com")
    u.is_superuser = True
    u.save(update_fields=["is_superuser"])
    return u


def _nobody() -> User:
    return User.objects.create_user(username="q_nobody", password="Dev12345!", email="qn@example.com")


def _branch_manager(username: str, branch: Branch) -> User:
    """A user whose Branch-Manager role grants sales.order.view at BRANCH scope only."""
    bm, _ = Group.objects.get_or_create(name=BRANCH_MANAGER)
    RolePermission.objects.update_or_create(
        role=bm, code="sales.order.view", defaults={"scope": "branch"})
    u = User.objects.create_user(username=username, email=f"{username}@erp.local", password="pw12345!")
    u.branch = branch
    u.save(update_fields=["branch"])
    u.groups.add(bm)
    return u


def _items(*specs):
    for sku, name, item_type, active in specs:
        Item.objects.create(sku=sku, name=name, type=item_type, is_active=active)


def _order(number, customer, *, branch=None, status="invoiced", subtotal=0):
    return SalesOrder.objects.create(
        number=number, customer=customer, order_date=TODAY, warehouse_code="WH-1",
        status=status, subtotal_minor=subtotal, branch=branch)


# --- happy paths ---------------------------------------------------------------------------------

def test_count_answers_how_many_items():
    admin = _admin()
    _items(("A", "Widget", "stock", True), ("B", "Gizmo", "stock", True),
           ("C", "Service", "service", True))

    result = _q(admin, entity="item", aggregate="count")
    assert result["value"] == 3
    assert result["citations"] == []


def test_filter_narrows_the_count():
    admin = _admin()
    _items(("A", "Widget", "stock", True), ("B", "Gizmo", "stock", True),
           ("C", "Old", "service", False))

    active = _q(admin, entity="item", aggregate="count",
                filters=[{"field": "is_active", "op": "eq", "value": "true"}])
    assert active["value"] == 2
    stock = _q(admin, entity="item", aggregate="count",
               filters=[{"field": "type", "op": "eq", "value": "service"}])
    assert stock["value"] == 1


def test_group_by_with_sum_formats_money():
    admin = _admin()
    c = Customer.objects.create(code="C-1", name="Nile")
    _order("SO-1", c, status="invoiced", subtotal=1_000_00)
    _order("SO-2", c, status="invoiced", subtotal=500_00)
    _order("SO-3", c, status="draft", subtotal=200_00)

    result = _q(admin, entity="sales_order", group_by=["status"], aggregate="sum", metric="subtotal")
    by_status = {row["status"]: row for row in result["rows"]}
    assert by_status["invoiced"]["value"] == "1,500.00 EGP"
    assert by_status["invoiced"]["value_minor"] == 1_500_00
    assert by_status["draft"]["value"] == "200.00 EGP"


def test_group_by_customer_builds_citations():
    admin = _admin()
    c1 = Customer.objects.create(code="C-1", name="Nile Traders")
    c2 = Customer.objects.create(code="C-2", name="Delta Co")
    _order("SO-1", c1, subtotal=1_000_00)
    _order("SO-2", c2, subtotal=400_00)

    result = _q(admin, entity="sales_order", group_by=["customer"], aggregate="sum", metric="subtotal")
    types = {c["type"] for c in result["citations"]}
    assert types == {"customer"}
    top = result["rows"][0]
    assert top["customer"] == "C-1" and top["value"] == "1,000.00 EGP"
    assert {"type": "customer", "value": "C-1", "label": "Nile Traders"} in result["citations"]


def test_purchase_order_supplier_totals():
    admin = _admin()
    s = Supplier.objects.create(code="S-1", name="Cairo Supplies")
    PurchaseOrder.objects.create(number="PO-1", supplier=s, order_date=TODAY, warehouse_code="WH-1",
                                 status="billed", subtotal_minor=800_00, billed_minor=912_00)
    result = _q(admin, entity="purchase_order", group_by=["supplier"], aggregate="sum",
                metric="subtotal")
    assert result["rows"][0]["value"] == "800.00 EGP"
    assert result["citations"][0]["type"] == "supplier"


# --- refusals: the registry is the boundary ------------------------------------------------------

def test_off_registry_entity_refused():
    assert _q(_admin(), entity="secret_table", aggregate="count") == {"error": _OFF_REGISTRY}


def test_off_registry_filter_field_refused():
    admin = _admin()
    _items(("A", "Widget", "stock", True))
    result = _q(admin, entity="item", aggregate="count",
                filters=[{"field": "password", "op": "eq", "value": "x"}])
    assert result == {"error": _BAD_FIELD}


def test_off_registry_group_field_refused():
    admin = _admin()
    _items(("A", "Widget", "stock", True))
    assert _q(admin, entity="item", group_by=["password"], aggregate="count") == {"error": _BAD_FIELD}


def test_unknown_metric_refused():
    admin = _admin()
    _items(("A", "Widget", "stock", True))
    assert _q(admin, entity="item", aggregate="sum", metric="cost") == {"error": _BAD_METRIC}


def test_user_without_permission_refused_never_data():
    # Seed real rows so the ONLY reason for the refusal is the missing permission.
    c = Customer.objects.create(code="C-1", name="Nile")
    _order("SO-1", c, subtotal=1_000_00)
    result = _q(_nobody(), entity="sales_order", aggregate="count")
    assert result == {"error": _DENIED}


def test_branch_scope_still_filters_the_rows():
    """A BRANCH-scoped user's query only counts/totals their own branch (+ unstamped NULL rows)."""
    a = Branch.objects.create(code="BR-A", name="Alpha")
    b = Branch.objects.create(code="BR-B", name="Beta")
    mgr = _branch_manager("q_mgr", a)
    c = Customer.objects.create(code="C-1", name="Nile")
    _order("SO-A", c, branch=a, subtotal=1_000_00)
    _order("SO-B", c, branch=b, subtotal=9_000_00)  # other branch — must be invisible

    count = _q(mgr, entity="sales_order", aggregate="count")
    assert count["value"] == 1  # only branch A's order
    total = _q(mgr, entity="sales_order", aggregate="sum", metric="subtotal")
    assert total["value"] == "1,000.00 EGP"  # branch B's 9,000 is excluded
