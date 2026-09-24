"""GET/POST /api/license/ (license-key FILE_02)."""
from __future__ import annotations

import datetime as dt

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from erp.identity.roles import SYSTEM_ADMIN
from erp.licensing import core
from erp.licensing.core import EDITIONS

pytestmark = pytest.mark.django_db

User = get_user_model()


@pytest.fixture
def admin_client():
    Group.objects.get_or_create(name=SYSTEM_ADMIN)
    u = User.objects.create_user(username="root", email="root@erp.local", password="pw12345!")
    u.groups.add(Group.objects.get(name=SYSTEM_ADMIN))
    c = APIClient()
    c.force_authenticate(user=u)
    return c


@pytest.fixture
def plain_client():
    u = User.objects.create_user(username="plain", email="plain@erp.local", password="pw12345!")
    c = APIClient()
    c.force_authenticate(user=u)
    return c


@pytest.fixture
def private_key():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    return Ed25519PrivateKey.generate()


@pytest.fixture
def signed_key(private_key, monkeypatch):
    from erp.licensing import verify as verify_mod

    monkeypatch.setattr(verify_mod, "configured_public_keys", lambda: [private_key.public_key()])
    info = core.LicenseInfo(
        license_id="LIC-API",
        company_name="Api Co",
        tax_id="555-666-777",
        edition="enterprise",
        modules=EDITIONS["enterprise"]["modules"],
        max_branches=None,
        issued_at=dt.date(2026, 1, 1),
        maintenance_until=dt.date(2099, 1, 1),
        ai_until=None,
    )
    return core.sign(info, private_key)


def test_get_requires_auth():
    resp = APIClient().get("/api/license/")
    assert resp.status_code in (401, 403)


def test_get_unmanaged_by_default(plain_client, settings):
    settings.LICENSE_MODE = "off"
    resp = plain_client.get("/api/license/")
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "unmanaged"


def test_get_trial_state_any_authenticated_user(plain_client, settings):
    settings.LICENSE_MODE = "enforce"
    resp = plain_client.get("/api/license/")
    body = resp.json()["data"]
    assert body["status"] == "trial"
    assert body["trial_days_left"] == 30
    assert "key_text" not in body


def test_post_by_non_admin_is_403(plain_client, settings, signed_key):
    settings.LICENSE_MODE = "enforce"
    resp = plain_client.post("/api/license/", {"key": signed_key})
    assert resp.status_code == 403


def test_post_invalid_key_is_400(admin_client, settings):
    settings.LICENSE_MODE = "enforce"
    resp = admin_client.post("/api/license/", {"key": "not-a-key"})
    assert resp.status_code == 400


def test_post_valid_key_by_admin_installs_it(admin_client, settings, signed_key):
    from erp.identity.services import get_org_preferences
    from erp.licensing.state import get_installed

    settings.LICENSE_MODE = "enforce"
    org = get_org_preferences()
    org.vat_number = "555-666-777"
    org.save(update_fields=["vat_number"])

    resp = admin_client.post("/api/license/", {"key": signed_key})
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["status"] == "active"
    assert body["edition"] == "enterprise"
    assert "key_text" not in body
    assert get_installed().key_text == signed_key
