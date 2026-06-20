"""Role editor (Increment 4) — role admin service + DRF surface, RBAC-gated.

Builds on the Increment 2 RBAC tables (RolePermission / ApprovalLimit) and the roles_admin service.
Runs under gate01 (erp/identity/tests).
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from erp.core.errors import ValidationError
from erp.identity import roles_admin
from erp.identity.models import ApprovalLimit, RolePermission
from erp.identity.roles import ACCOUNTANT, SYSTEM_ADMIN

User = get_user_model()


def _user(username, role):
    g, _ = Group.objects.get_or_create(name=role)
    u = User.objects.create_user(username=username, email=f"{username}@erp.local", password="pw12345!")
    u.groups.add(g)
    return u


@pytest.fixture
def admin(db):
    return _user("root", SYSTEM_ADMIN)


@pytest.fixture
def accountant(db):
    return _user("acct", ACCOUNTANT)


def _auth(user):
    c = APIClient()
    tok = APIClient().post(
        "/api/identity/login", {"username": user.username, "password": "pw12345!"}, format="json"
    ).json()["data"]["access"]
    c.credentials(HTTP_AUTHORIZATION="Bearer " + tok)
    return c


# --- Service layer ---

def test_list_marks_builtin_roles_protected(db):
    Group.objects.get_or_create(name=SYSTEM_ADMIN)
    Group.objects.get_or_create(name="Sales Rep")
    by_name = {r["name"]: r for r in roles_admin.list_roles()}
    assert by_name[SYSTEM_ADMIN]["protected"] is True
    assert by_name["Sales Rep"]["protected"] is False


def test_create_role_duplicating_copies_grants(db):
    src = Group.objects.create(name="Source")
    RolePermission.objects.create(role=src, code="sales.order.view", scope="branch")
    ApprovalLimit.objects.create(role=src, document_type="sales_order", limit_minor=5_000_000)

    detail = roles_admin.create_role("Sales Lite", copy_from="Source")
    assert detail["permissions"] == {"sales.order.view": "branch"}
    assert detail["approval_limits"] == {"sales_order": 5_000_000}
    assert detail["protected"] is False


def test_create_role_rejects_duplicate_name(db):
    Group.objects.create(name="Dup")
    with pytest.raises(ValidationError):
        roles_admin.create_role("Dup")


def test_set_permission_grants_then_revokes(db):
    Group.objects.create(name="Editor")
    roles_admin.set_permission("Editor", "inventory.item.edit", "branch", True)
    assert RolePermission.objects.filter(role__name="Editor", code="inventory.item.edit").exists()

    roles_admin.set_permission("Editor", "inventory.item.edit", "branch", False)
    assert not RolePermission.objects.filter(role__name="Editor", code="inventory.item.edit").exists()


def test_set_permission_rejects_unknown_code(db):
    Group.objects.create(name="Bad")
    with pytest.raises(ValidationError):
        roles_admin.set_permission("Bad", "sales.nonsense.view", "all", True)


def test_set_approval_limit_set_unlimited_remove(db):
    Group.objects.create(name="Approver")
    roles_admin.set_approval_limit("Approver", "invoice", None)  # unlimited
    assert ApprovalLimit.objects.get(role__name="Approver", document_type="invoice").limit_minor is None

    roles_admin.set_approval_limit("Approver", "invoice", 9_900_000)
    assert ApprovalLimit.objects.get(role__name="Approver", document_type="invoice").limit_minor == 9_900_000

    roles_admin.set_approval_limit("Approver", "invoice", "remove")
    assert not ApprovalLimit.objects.filter(role__name="Approver", document_type="invoice").exists()


def test_delete_protected_role_rejected(db):
    Group.objects.get_or_create(name=SYSTEM_ADMIN)
    with pytest.raises(ValidationError):
        roles_admin.delete_role(SYSTEM_ADMIN)


def test_delete_role_with_members_rejected(db):
    _user("member", "Temp")  # creates the group + a member
    with pytest.raises(ValidationError):
        roles_admin.delete_role("Temp")


def test_delete_empty_custom_role_succeeds(db):
    Group.objects.create(name="Throwaway")
    roles_admin.delete_role("Throwaway")
    assert not Group.objects.filter(name="Throwaway").exists()


# --- API + RBAC ---

def test_roles_api_requires_admin_permission(admin, accountant):
    # System Admin bypasses every check.
    assert _auth(admin).get("/api/identity/roles").status_code == 200
    # An accountant holds no administration.role.* permission.
    assert _auth(accountant).get("/api/identity/roles").status_code == 403


def test_registry_endpoint_lists_vocabulary(admin):
    data = _auth(admin).get("/api/identity/roles/registry").json()["data"]
    assert "administration" in data["modules"]
    assert "approve" in data["actions"]
    assert any(s["value"] == "branch" for s in data["scopes"])
    assert "sales_order" in data["document_types"]


def test_full_role_lifecycle_via_api(admin):
    c = _auth(admin)
    created = c.post("/api/identity/roles", {"name": "Regional Buyer"}, format="json")
    assert created.status_code == 201, created.content

    granted = c.post("/api/identity/roles/Regional Buyer/permission",
                     {"code": "purchasing.order.create", "scope": "branch", "granted": True},
                     format="json")
    assert granted.status_code == 200
    assert granted.json()["data"]["permissions"]["purchasing.order.create"] == "branch"

    limited = c.post("/api/identity/roles/Regional Buyer/approval-limit",
                     {"document_type": "purchase_order", "limit_minor": 2_500_000}, format="json")
    assert limited.json()["data"]["approval_limits"]["purchase_order"] == 2_500_000

    deleted = c.delete("/api/identity/roles/Regional Buyer")
    assert deleted.status_code == 200
    assert not Group.objects.filter(name="Regional Buyer").exists()
