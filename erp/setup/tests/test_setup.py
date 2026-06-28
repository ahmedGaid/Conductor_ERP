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
    # A fresh org has no chart of accounts yet.
    assert data["chart_of_accounts"] == {"seeded": False, "accounts": 0}


def test_admin_seeds_chart_of_accounts(admin):
    c = _auth(admin)
    resp = c.post("/api/setup/chart-of-accounts")
    assert resp.status_code == 200
    coa = resp.json()["data"]
    assert coa["seeded"] is True
    assert coa["accounts"] > 0
    # Reflected in status, and idempotent (count is stable on a second run).
    after = c.get("/api/setup/status").json()["data"]["chart_of_accounts"]
    assert after == coa
    again = c.post("/api/setup/chart-of-accounts").json()["data"]
    assert again["accounts"] == coa["accounts"]


def test_seed_chart_of_accounts_requires_system_admin(accountant):
    c = _auth(accountant)
    assert c.post("/api/setup/chart-of-accounts").status_code == 403


def test_tax_defaults_and_update(admin):
    c = _auth(admin)
    # Egypt default before anything is set.
    tax = c.get("/api/setup/status").json()["data"]["tax"]
    assert tax == {"vat_rate_bps": 1400, "einvoice_enabled": True}
    # Set a new rate + disable e-invoicing.
    resp = c.post("/api/setup/tax", {"vat_rate_bps": 1500, "einvoice_enabled": False}, format="json")
    assert resp.status_code == 200
    assert resp.json()["data"] == {"vat_rate_bps": 1500, "einvoice_enabled": False}
    # Reflected in status, and the e-invoice flag reaches effective preferences (the nav reads it).
    after = c.get("/api/setup/status").json()["data"]["tax"]
    assert after == {"vat_rate_bps": 1500, "einvoice_enabled": False}
    eff = c.get("/api/identity/preferences/effective").json()["data"]
    assert eff["einvoice_enabled"] is False


def test_tax_requires_system_admin(accountant):
    c = _auth(accountant)
    assert c.post("/api/setup/tax", {"vat_rate_bps": 1500}, format="json").status_code == 403


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


def test_status_exposes_available_roles(admin):
    # The invite step's role picker reads this list off the status payload.
    roles = _auth(admin).get("/api/setup/status").json()["data"]["available_roles"]
    assert SYSTEM_ADMIN in roles


def test_admin_invites_user_with_role(admin):
    # The role must exist as a group (the picker only ever offers status.available_roles).
    Group.objects.get_or_create(name=ACCOUNTANT)
    c = _auth(admin)
    resp = c.post(
        "/api/setup/users",
        {"username": "sara", "email": "sara@erp.local", "role": ACCOUNTANT},
        format="json",
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["username"] == "sara"
    assert data["role"] == ACCOUNTANT
    # The one-time temp password comes back so the admin can hand it over.
    assert data["temp_password"]
    # The user was really created with the role and the invited status.
    sara = User.objects.get(username="sara")
    assert sara.status == "invited"
    assert sara.groups.filter(name=ACCOUNTANT).exists()


def test_invite_requires_system_admin(accountant):
    c = _auth(accountant)
    resp = c.post(
        "/api/setup/users", {"username": "x", "email": "x@erp.local"}, format="json"
    )
    assert resp.status_code == 403
