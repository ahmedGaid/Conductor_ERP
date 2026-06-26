"""First-run setup endpoint tests — Growth Phase 1.0.

Prove the setup-state surface the post-login route guard depends on: a fresh org reads as
not-complete, any authenticated user may read status, and only a System Admin may finish setup
(which flips the flag and is reflected on the next read).
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from erp.identity.roles import ACCOUNTANT, SYSTEM_ADMIN

User = get_user_model()


def _user(username, role):
    Group.objects.get_or_create(name=role)
    u = User.objects.create_user(username=username, email=f"{username}@erp.local", password="pw12345!")
    u.groups.add(Group.objects.get(name=role))
    return u


@pytest.fixture
def accountant(db):
    return _user("acct", ACCOUNTANT)


@pytest.fixture
def admin(db):
    return _user("root", SYSTEM_ADMIN)


def _auth(user):
    c = APIClient()
    tokens = APIClient().post(
        "/api/identity/login", {"username": user.username, "password": "pw12345!"}, format="json"
    ).json()["data"]
    c.credentials(HTTP_AUTHORIZATION="Bearer " + tokens["access"])
    return c


def test_status_requires_authentication():
    assert APIClient().get("/api/setup/status").status_code == 401


def test_fresh_org_reads_not_complete(accountant):
    c = _auth(accountant)
    data = c.get("/api/setup/status").json()["data"]
    assert data["is_setup_complete"] is False


def test_complete_requires_system_admin(accountant):
    # A non-admin may read status but not finish setup.
    c = _auth(accountant)
    assert c.get("/api/setup/status").status_code == 200
    assert c.post("/api/setup/complete").status_code == 403


def test_admin_completes_and_flag_persists(admin):
    c = _auth(admin)
    resp = c.post("/api/setup/complete")
    assert resp.status_code == 200
    assert resp.json()["data"]["is_setup_complete"] is True
    # Reflected on the next read.
    assert c.get("/api/setup/status").json()["data"]["is_setup_complete"] is True
