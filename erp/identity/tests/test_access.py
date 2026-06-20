"""Granular RBAC (Increment 2) — registry, permission/scope resolution, approval limits, the new
DRF permission class, and the seeded default role sets. Runs under gate01 (erp/identity/tests).
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command

from erp.identity import access, rbac
from erp.identity.models import ApprovalLimit, RolePermission
from erp.identity.permissions import HasModulePermission
from erp.identity.roles import ACCOUNTANT, AUDITOR, SYSTEM_ADMIN

User = get_user_model()


# --- Registry ----------------------------------------------------------------------------------

def test_registry_codes_are_well_formed_and_valid():
    codes = rbac.all_permission_codes()
    assert "sales.order.approve" in codes
    assert all(rbac.is_valid_code(c) for c in codes)
    assert not rbac.is_valid_code("sales.order.frobnicate")
    assert not rbac.is_valid_code("nope.order.view")
    assert rbac.module_of("accounting.journal.approve") == "accounting"


def test_scope_breadth_ordering():
    assert rbac.broadest(rbac.DataScope.BRANCH, rbac.DataScope.ALL) == rbac.DataScope.ALL
    assert rbac.broadest(rbac.DataScope.OWN, rbac.DataScope.TEAM) == rbac.DataScope.TEAM


# --- Permission & scope resolution -------------------------------------------------------------

@pytest.fixture
def user(db):
    return User.objects.create_user(username="u", email="u@erp.local", password="pw12345!")


def _grant(group_name, code, scope=rbac.DataScope.ALL):
    g, _ = Group.objects.get_or_create(name=group_name)
    RolePermission.objects.update_or_create(role=g, code=code, defaults={"scope": scope})
    return g


def test_has_permission_and_broadest_scope_across_roles(user):
    # Two roles grant the same code at different scopes; the broader one wins.
    g1 = _grant("RoleA", "sales.order.view", rbac.DataScope.BRANCH)
    g2 = _grant("RoleB", "sales.order.view", rbac.DataScope.ALL)
    _grant("RoleA", "sales.order.edit", rbac.DataScope.OWN)
    user.groups.add(g1, g2)

    assert access.has_permission(user, "sales.order.view") is True
    assert access.has_permission(user, "sales.order.delete") is False
    assert access.scope_for(user, "sales.order.view") == rbac.DataScope.ALL
    assert access.scope_for(user, "sales.order.edit") == rbac.DataScope.OWN


def test_accessible_modules(user):
    user.groups.add(_grant("Ops", "inventory.item.view"))
    mods = access.accessible_modules(user)
    assert "inventory" in mods
    assert "accounting" not in mods


def test_system_admin_bypasses_everything(db):
    g, _ = Group.objects.get_or_create(name=SYSTEM_ADMIN)
    admin = User.objects.create_user(username="root", email="root@erp.local", password="pw12345!")
    admin.groups.add(g)
    assert access.has_permission(admin, "accounting.journal.delete") is True
    assert access.scope_for(admin, "anything.at.all") == rbac.DataScope.ALL
    assert set(access.accessible_modules(admin)) == set(rbac.MODULE_NAMES)
    assert access.approval_limit(admin, "payment") is None
    assert access.can_approve(admin, "payment", 999_999_999) is True


# --- Approval limits ---------------------------------------------------------------------------

def test_approval_limit_threshold_unlimited_and_none(user):
    capped = _grant("Mgr", "purchasing.order.approve")
    ApprovalLimit.objects.create(role=capped, document_type="purchase_order", limit_minor=5_000_000)
    user.groups.add(capped)

    assert access.approval_limit(user, "purchase_order") == 5_000_000
    assert access.can_approve(user, "purchase_order", 5_000_000) is True
    assert access.can_approve(user, "purchase_order", 5_000_001) is False
    # No limit row for this doc type → cannot approve any positive amount.
    assert access.approval_limit(user, "invoice") == 0
    assert access.can_approve(user, "invoice", 1) is False

    # A second role granting an unlimited (null) limit wins.
    unlimited = Group.objects.create(name="Director")
    ApprovalLimit.objects.create(role=unlimited, document_type="purchase_order", limit_minor=None)
    user.groups.add(unlimited)
    assert access.approval_limit(user, "purchase_order") is None
    assert access.can_approve(user, "purchase_order", 10_000_000) is True


# --- DRF permission class (superset of HasAnyRole) ---------------------------------------------

def test_has_module_permission_class(user):
    user.groups.add(_grant("Viewer", "crm.lead.view"))
    perm = HasModulePermission.require("crm.lead.view")()
    assert perm.has_permission(SimpleNamespace(user=user), None) is True

    denied = HasModulePermission.require("crm.lead.delete")()
    assert denied.has_permission(SimpleNamespace(user=user), None) is False

    anon = SimpleNamespace(user=SimpleNamespace(is_authenticated=False))
    assert perm.has_permission(anon, None) is False


# --- Seed assigns default role permission sets -------------------------------------------------

def test_seed_assigns_default_role_permissions(db):
    call_command("seed_identity", verbosity=0)
    accountant = Group.objects.get(name=ACCOUNTANT)
    auditor = Group.objects.get(name=AUDITOR)

    assert RolePermission.objects.filter(role=accountant, code="accounting.journal.create").exists()
    # Auditor is view-only — it never gets a non-view action.
    assert auditor.role_permissions.exists()
    assert not auditor.role_permissions.exclude(code__endswith=".view").exists()
    # Accountant can approve invoices and has an unlimited journal approval limit.
    assert ApprovalLimit.objects.filter(
        role=accountant, document_type="journal", limit_minor__isnull=True
    ).exists()
