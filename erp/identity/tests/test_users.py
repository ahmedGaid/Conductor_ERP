"""User management (Increment 3) — admin CRUD, lifecycle, bulk actions, RBAC gating, detail shape.
Runs under gate01 (erp/identity/tests).
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from erp.identity import users as user_svc
from erp.identity.models import USER_SUSPENDED, Department
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

def test_create_user_is_invited_with_temp_password(db):
    user, temp = user_svc.create_user(username="newbie", email="n@erp.local", role=None)
    assert user.status == "invited"
    assert user.is_active is True
    assert temp and user.check_password(temp)


def test_status_sync_blocks_authentication(db):
    user, _ = user_svc.create_user(username="x", email="x@erp.local")
    user_svc.set_status(user, USER_SUSPENDED)
    user.refresh_from_db()
    assert user.status == USER_SUSPENDED
    assert user.is_active is False


def test_bulk_suspend(db):
    a, _ = user_svc.create_user(username="a", email="a@erp.local")
    b, _ = user_svc.create_user(username="b", email="b@erp.local")
    n = user_svc.bulk("suspend", [a.id, b.id])
    assert n == 2
    assert not User.objects.get(pk=a.id).is_active


# --- API + RBAC ---

def test_users_api_requires_admin_permission(admin, accountant):
    # System Admin can list users.
    assert _auth(admin).get("/api/identity/users").status_code == 200
    # An accountant (no administration.* permissions) is forbidden.
    assert _auth(accountant).get("/api/identity/users").status_code == 403


def test_create_and_fetch_detail_via_api(admin):
    Group.objects.get_or_create(name=ACCOUNTANT)
    c = _auth(admin)
    resp = c.post("/api/identity/users", {"username": "carol", "email": "carol@erp.local",
                                          "role": ACCOUNTANT}, format="json")
    assert resp.status_code == 201, resp.content
    body = resp.json()["data"]
    assert body["temp_password"]
    uid = body["id"]

    detail = c.get(f"/api/identity/users/{uid}").json()["data"]
    assert detail["role"] == ACCOUNTANT
    assert "modules" in detail and "permissions" in detail and "sessions" in detail


def test_patch_status_and_department(admin, db):
    Department.objects.create(code="FIN", name="Finance")
    target, _ = user_svc.create_user(username="dee", email="dee@erp.local")
    c = _auth(admin)
    resp = c.patch(f"/api/identity/users/{target.id}",
                   {"status": "suspended", "department": "FIN"}, format="json")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "suspended"
    assert data["department"] == "FIN"


def test_patch_profile_text_fields(admin, db):
    target, _ = user_svc.create_user(username="fay", email="fay@erp.local")
    c = _auth(admin)
    # Set free-text profile fields (these live on UserPreferences).
    resp = c.patch(f"/api/identity/users/{target.id}",
                   {"job_title": "Controller", "phone": "+20 100 000 0000"}, format="json")
    assert resp.status_code == 200, resp.content
    data = resp.json()["data"]
    assert data["job_title"] == "Controller"
    assert data["phone"] == "+20 100 000 0000"
    # A blank value clears the field.
    resp = c.patch(f"/api/identity/users/{target.id}", {"job_title": ""}, format="json")
    assert resp.status_code == 200
    assert resp.json()["data"]["job_title"] == ""
    # Untouched field is preserved.
    assert resp.json()["data"]["phone"] == "+20 100 000 0000"


def test_reset_password_returns_new_temp(admin):
    target, old = user_svc.create_user(username="ed", email="ed@erp.local")
    resp = _auth(admin).post(f"/api/identity/users/{target.id}/reset-password")
    assert resp.status_code == 200
    new = resp.json()["data"]["temp_password"]
    assert new and new != old
    assert User.objects.get(pk=target.id).check_password(new)
