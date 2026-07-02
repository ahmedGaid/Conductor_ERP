"""Session-00 auth hardening — login throttle, refresh rotation, cookie-based refresh flow."""
from __future__ import annotations

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from erp.identity.models import User

pytestmark = pytest.mark.django_db


@pytest.fixture()
def user(db):
    return User.objects.create_user(username="kim", email="kim@erp.local", password="pw12345!")


def _login(client, password="pw12345!"):
    return client.post("/api/identity/login",
                       {"username": "kim", "password": password}, format="json")


def test_login_attempts_are_throttled_per_ip(user, monkeypatch):
    # Re-enable a tiny login rate (dev disables throttling). DRF snapshots THROTTLE_RATES on the
    # throttle class at import, so patch that dict directly (monkeypatch restores it) and clear the
    # shared throttle-history cache on both sides so no 429 state leaks (see gate12 pattern).
    from rest_framework.throttling import SimpleRateThrottle

    monkeypatch.setitem(SimpleRateThrottle.THROTTLE_RATES, "login", "3/min")
    client = APIClient()
    cache.clear()
    try:
        for _ in range(3):
            assert _login(client, password="wrong").status_code == 400
        assert _login(client, password="wrong").status_code == 429  # 4th attempt capped
    finally:
        cache.clear()


def test_rotated_out_refresh_token_is_rejected(user):
    old = RefreshToken.for_user(user)
    client = APIClient()
    # Rotation issues a new pair and blacklists the old token…
    first = client.post("/api/identity/token/refresh", {"refresh": str(old)}, format="json")
    assert first.status_code == 200 and first.json()["access"]
    # …so replaying the rotated-out token must fail.
    replay = client.post("/api/identity/token/refresh", {"refresh": str(old)}, format="json")
    assert replay.status_code == 401


def test_refresh_flows_through_httponly_cookie(user):
    client = APIClient()
    login = _login(client)
    assert login.status_code == 200
    cookie = login.cookies.get("erp_refresh")
    assert cookie is not None and cookie["httponly"]
    assert "refresh" not in login.json()["data"]

    # The client sends no body — the cookie alone renews the access token, and rotation puts the
    # NEW refresh token back into the cookie, never the body.
    refreshed = client.post("/api/identity/token/refresh", {}, format="json")
    assert refreshed.status_code == 200
    body = refreshed.json()
    assert body["access"]
    assert "refresh" not in body
    assert refreshed.cookies.get("erp_refresh") is not None


def test_logout_blacklists_the_cookie_refresh(user):
    client = APIClient()
    login = _login(client)
    raw = login.cookies["erp_refresh"].value
    out = client.post("/api/identity/logout")
    assert out.status_code == 200
    # The cookie is cleared client-side AND its token is blacklisted server-side — replaying the
    # captured value must fail.
    renewed = client.post("/api/identity/token/refresh", {"refresh": raw}, format="json")
    assert renewed.status_code == 401
