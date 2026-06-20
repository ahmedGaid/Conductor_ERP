"""Personalization (user + org preferences) tests — Increment 1.

These run under gate01 (erp/identity/tests). They prove the additive Settings surface:
defaults on first access, partial-update persistence, org⊕personal merge in the effective view,
self-only access to personal prefs, and System-Admin-gated org defaults.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from erp.identity.roles import ACCOUNTANT, SYSTEM_ADMIN

User = get_user_model()


@pytest.fixture
def client():
    return APIClient()


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


def test_preferences_default_on_first_access(accountant):
    c = _auth(accountant)
    data = c.get("/api/identity/preferences").json()["data"]
    # An absent row materializes with product defaults; inheritable fields are blank.
    assert data["density"] == "comfortable"
    assert data["font_size"] == "default"
    assert data["theme"] == ""  # inherits the org default
    assert data["accent_color"] == ""


def test_patch_preferences_persists(accountant):
    c = _auth(accountant)
    resp = c.patch(
        "/api/identity/preferences",
        {"accent_color": "green", "density": "compact", "high_contrast": True},
        format="json",
    )
    assert resp.status_code == 200
    again = c.get("/api/identity/preferences").json()["data"]
    assert again["accent_color"] == "green"
    assert again["density"] == "compact"
    assert again["high_contrast"] is True


def test_effective_merges_org_defaults_under_personal(accountant, admin):
    # Admin sets an org default accent; the accountant (no personal override) inherits it.
    admin_c = _auth(admin)
    assert admin_c.patch(
        "/api/identity/org-preferences", {"default_accent": "purple"}, format="json"
    ).status_code == 200

    c = _auth(accountant)
    eff = c.get("/api/identity/preferences/effective").json()["data"]
    assert eff["accent_color"] == "purple"  # inherited
    assert eff["default_landing"] == "/"  # falls back to root

    # A personal override wins over the org default.
    c.patch("/api/identity/preferences", {"accent_color": "red"}, format="json")
    eff2 = c.get("/api/identity/preferences/effective").json()["data"]
    assert eff2["accent_color"] == "red"


def test_org_preferences_patch_requires_system_admin(accountant, admin):
    # Non-admin can read but not change org defaults.
    c = _auth(accountant)
    assert c.get("/api/identity/org-preferences").status_code == 200
    assert c.patch(
        "/api/identity/org-preferences", {"default_accent": "orange"}, format="json"
    ).status_code == 403

    # System Admin can.
    assert _auth(admin).patch(
        "/api/identity/org-preferences", {"default_accent": "orange"}, format="json"
    ).status_code == 200


def test_preferences_require_authentication(client):
    assert client.get("/api/identity/preferences").status_code == 401
