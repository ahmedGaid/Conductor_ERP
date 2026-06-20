"""Session management (per-device revoke) — outstanding refresh tokens are listed and revocable,
and suspending a user force-signs-out every device. Runs under gate01 (erp/identity/tests).
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from erp.identity import sessions, users as user_svc
from erp.identity.models import USER_SUSPENDED
from erp.identity.roles import SYSTEM_ADMIN

User = get_user_model()


def _make(username: str):
    return User.objects.create_user(username=username, email=f"{username}@erp.local", password="pw12345!")


def test_for_user_records_active_session(db):
    u = _make("alice")
    RefreshToken.for_user(u)
    assert len(sessions.active_sessions(u)) == 1


def test_revoke_all_empties_sessions(db):
    u = _make("bob")
    RefreshToken.for_user(u)
    RefreshToken.for_user(u)
    assert len(sessions.active_sessions(u)) == 2
    assert sessions.revoke_all_sessions(u) == 2
    assert sessions.active_sessions(u) == []


def test_revoke_single_session(db):
    u = _make("carol")
    RefreshToken.for_user(u)
    RefreshToken.for_user(u)
    sess = sessions.active_sessions(u)
    revoked_id = sess[0]["id"]
    assert sessions.revoke_session(u, revoked_id) is True
    remaining = [s["id"] for s in sessions.active_sessions(u)]
    assert revoked_id not in remaining
    assert len(remaining) == 1


def test_revoke_rejects_another_users_token(db):
    a, b = _make("dan"), _make("erin")
    RefreshToken.for_user(a)
    a_token_id = sessions.active_sessions(a)[0]["id"]
    assert sessions.revoke_session(b, a_token_id) is False  # not erin's
    assert len(sessions.active_sessions(a)) == 1  # untouched


def test_suspend_force_signs_out(db):
    u = _make("frank")
    RefreshToken.for_user(u)
    user_svc.set_status(u, USER_SUSPENDED)
    assert sessions.active_sessions(u) == []


def test_blacklisted_refresh_cannot_renew(db):
    u = _make("grace")
    refresh = RefreshToken.for_user(u)
    sessions.revoke_all_sessions(u)
    resp = APIClient().post("/api/identity/token/refresh", {"refresh": str(refresh)}, format="json")
    assert resp.status_code == 401


def _admin_client():
    g, _ = Group.objects.get_or_create(name=SYSTEM_ADMIN)
    admin = _make("root")
    admin.groups.add(g)
    c = APIClient()
    c.force_authenticate(user=admin)
    return c


def test_api_revoke_all_sessions(db):
    target = _make("heidi")
    RefreshToken.for_user(target)
    resp = _admin_client().post(f"/api/identity/users/{target.id}/revoke-sessions")
    assert resp.status_code == 200
    assert resp.json()["data"]["revoked"] == 1
    assert sessions.active_sessions(target) == []


def test_api_revoke_single_session_returns_detail(db):
    target = _make("ivan")
    RefreshToken.for_user(target)
    token_id = sessions.active_sessions(target)[0]["id"]
    resp = _admin_client().post(f"/api/identity/users/{target.id}/sessions/{token_id}/revoke")
    assert resp.status_code == 200
    assert resp.json()["data"]["active_sessions"] == []
