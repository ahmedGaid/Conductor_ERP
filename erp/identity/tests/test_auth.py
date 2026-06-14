"""Stage 1 auth + RBAC + 2FA + audit-on-login tests."""
from __future__ import annotations

import pyotp
import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from erp.audit.models import AuditEntry
from erp.identity.roles import ACCOUNTANT, AUDITOR

User = get_user_model()


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def accountant(db):
    Group.objects.get_or_create(name=ACCOUNTANT)
    u = User.objects.create_user(username="acct", email="acct@erp.local", password="pw12345!")
    u.groups.add(Group.objects.get(name=ACCOUNTANT))
    return u


@pytest.fixture
def auditor(db):
    Group.objects.get_or_create(name=AUDITOR)
    u = User.objects.create_user(username="aud", email="aud@erp.local", password="pw12345!")
    u.groups.add(Group.objects.get(name=AUDITOR))
    return u


def _login(client, username, password, otp=None):
    body = {"username": username, "password": password}
    if otp is not None:
        body["otp_code"] = otp
    return client.post("/api/identity/login", body, format="json")


def test_login_success_returns_tokens_and_audits(client, accountant):
    resp = _login(client, "acct", "pw12345!")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "access" in data and "refresh" in data
    # An audit row was written for the login, carrying a correlation id.
    entry = AuditEntry.objects.filter(action="login", module="identity").latest("created_at")
    assert entry.result == "success"
    assert entry.correlation_id  # non-empty


def test_login_bad_credentials_rejected_and_audited(client, accountant):
    resp = _login(client, "acct", "wrong")
    assert resp.status_code == 400
    assert AuditEntry.objects.filter(action="login", result="failure").exists()


def test_rbac_allows_accountant_denies_auditor(client, accountant, auditor):
    # Accountant can reach the finance sample endpoint.
    a = APIClient()
    a.credentials(HTTP_AUTHORIZATION="Bearer " + _login(client, "acct", "pw12345!").json()["data"]["access"])
    assert a.get("/api/identity/sample/finance").status_code == 200

    # Auditor (wrong role) is forbidden.
    b = APIClient()
    b.credentials(HTTP_AUTHORIZATION="Bearer " + _login(client, "aud", "pw12345!").json()["data"]["access"])
    assert b.get("/api/identity/sample/finance").status_code == 403


def test_unauthenticated_denied(client):
    assert client.get("/api/identity/sample/finance").status_code == 401


def test_2fa_challenge_then_success(client, accountant):
    # Enable 2FA on the user with a known secret.
    secret = pyotp.random_base32()
    accountant.totp_secret = secret
    accountant.is_2fa_enabled = True
    accountant.save()

    # Without a code -> challenge, no tokens.
    challenge = _login(client, "acct", "pw12345!").json()["data"]
    assert challenge == {"twofa_required": True}

    # With a valid code -> tokens.
    code = pyotp.TOTP(secret).now()
    tokens = _login(client, "acct", "pw12345!", otp=code).json()["data"]
    assert "access" in tokens
