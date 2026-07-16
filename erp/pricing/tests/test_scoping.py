"""Data-scope invariant — pricing is org-wide **by design** (DECISIONS §Security 2026-07).

Unlike transactional modules (sales/purchasing/inventory/crm/accounting/einvoice), price lists and
per-customer overrides are shared reference data every branch prices against, so ``scope_queryset``
is deliberately NOT applied here — scoping them would make a list created in one branch invisible to
another and break cross-branch documents. This test pins that decision as an executable invariant:
a Branch Manager in branch A sees a price list created by a Branch Manager in branch B. RBAC still
gates *who may edit* (Branch Manager role) — this is only about visibility.
"""
from __future__ import annotations

import pytest
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from erp.core.models import Branch
from erp.identity.models import User
from erp.identity.roles import BRANCH_MANAGER

pytestmark = pytest.mark.django_db


def _branch_manager(username: str, branch: Branch) -> User:
    bm, _ = Group.objects.get_or_create(name=BRANCH_MANAGER)
    u = User.objects.create_user(username=username, email=f"{username}@erp.local", password="pw12345!")
    u.branch = branch
    u.save(update_fields=["branch"])
    u.groups.add(bm)
    return u


def _client(user: User) -> APIClient:
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def test_price_lists_are_org_wide_across_branches():
    a = Branch.objects.create(code="BR-A", name="Alpha")
    b = Branch.objects.create(code="BR-B", name="Beta")
    mgr_a = _branch_manager("price_mgr_a", a)
    mgr_b = _branch_manager("price_mgr_b", b)

    # Manager in branch B creates a price list.
    created = _client(mgr_b).post(
        "/api/pricing/price-lists",
        {"code": "STD-B", "name": "Standard (B)", "is_default": False},
        format="json",
    )
    assert created.status_code == 201, created.data

    # Manager in branch A sees it — pricing is NOT branch-scoped (org-wide reference data).
    listing = _client(mgr_a).get("/api/pricing/price-lists").data["data"]
    codes = {row["code"] for row in listing}
    assert "STD-B" in codes  # a scoped module would have hidden it; pricing must not.


def test_customer_item_overrides_are_org_wide_across_branches():
    a = Branch.objects.create(code="BR-A", name="Alpha")
    b = Branch.objects.create(code="BR-B", name="Beta")
    mgr_a = _branch_manager("ovr_mgr_a", a)
    mgr_b = _branch_manager("ovr_mgr_b", b)

    created = _client(mgr_b).post(
        "/api/pricing/customer-prices",
        {"customer_code": "ACME", "item_sku": "WIDGET", "unit_price_minor": 90_00},
        format="json",
    )
    assert created.status_code == 201, created.data

    rows = _client(mgr_a).get("/api/pricing/customer-prices").data["data"]
    assert any(r["customer_code"] == "ACME" and r["item_sku"] == "WIDGET" for r in rows)
