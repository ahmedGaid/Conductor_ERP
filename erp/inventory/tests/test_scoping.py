"""Data-scope enforcement (Increment 5) — inventory.

receive_stock stamps the actor's branch on the StockMovement; scope_queryset isolates a
BRANCH-scoped manager to their own branch while leaving unstamped/NULL movements visible.
"""
from __future__ import annotations

import pytest
from django.contrib.auth.models import Group

from erp.core.models import Branch
from erp.identity.models import RolePermission, User
from erp.identity.roles import BRANCH_MANAGER
from erp.identity.scoping import scope_queryset
from erp.inventory import services
from erp.inventory.domain.models import StockMovement

from .factories import make_gl, make_item, make_warehouse

pytestmark = pytest.mark.django_db

VIEW = "inventory.stock_movement.view"


def _manager(username: str, branch: Branch) -> User:
    bm, _ = Group.objects.get_or_create(name=BRANCH_MANAGER)
    RolePermission.objects.update_or_create(role=bm, code=VIEW, defaults={"scope": "branch"})
    u = User.objects.create_user(username=username, email=f"{username}@erp.local", password="pw12345!")
    u.branch = branch
    u.save(update_fields=["branch"])
    u.groups.add(bm)
    return u


def test_branch_scope_isolates_stock_movements():
    make_gl()
    item = make_item()
    wh = make_warehouse()
    a = Branch.objects.create(code="BR-A", name="Alpha")
    b = Branch.objects.create(code="BR-B", name="Beta")
    mgr_a = _manager("stock_a", a)
    mgr_b = _manager("stock_b", b)

    move_a = services.receive_stock(item=item, warehouse=wh, quantity=5, unit_cost_minor=100_00, actor=mgr_a)
    move_b = services.receive_stock(item=item, warehouse=wh, quantity=5, unit_cost_minor=100_00, actor=mgr_b)

    assert move_a.branch_id == a.id
    seen = set(scope_queryset(mgr_a, StockMovement.objects.all(), VIEW).values_list("id", flat=True))
    assert move_a.id in seen
    assert move_b.id not in seen
