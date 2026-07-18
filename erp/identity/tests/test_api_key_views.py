"""TH FILE_14 Task B/C — HTTP surface for the API keys settings page + docs reference.

Task A (model/service) and D (service-level tests) were built backend-only (test_api_keys.py);
this file covers the view layer this session added to make that service reachable from the UI.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from erp.identity.roles import SYSTEM_ADMIN

User = get_user_model()


@pytest.fixture
def admin_client(db):
    Group.objects.get_or_create(name=SYSTEM_ADMIN)
    u = User.objects.create_user(username="root", email="root@erp.local", password="pw12345!")
    u.groups.add(Group.objects.get(name=SYSTEM_ADMIN))
    c = APIClient()
    c.force_authenticate(user=u)
    return c


@pytest.fixture
def plain_client(db):
    u = User.objects.create_user(username="plain", email="plain@erp.local", password="pw12345!")
    c = APIClient()
    c.force_authenticate(user=u)
    return c


def test_non_admin_cannot_list_or_create(plain_client):
    assert plain_client.get("/api/identity/api-keys").status_code == 403
    assert plain_client.post("/api/identity/api-keys", {"name": "x", "role": SYSTEM_ADMIN}).status_code == 403


def test_admin_create_list_revoke_round_trip(admin_client):
    resp = admin_client.post("/api/identity/api-keys", {"name": "Reporting bot", "role": SYSTEM_ADMIN})
    assert resp.status_code == 201
    body = resp.json()["data"]
    assert body["secret"].startswith("ck_")
    assert body["is_active"] is True
    key_id = body["id"]

    listed = admin_client.get("/api/identity/api-keys").json()["data"]
    assert any(row["id"] == key_id for row in listed)
    assert "secret" not in listed[0]

    revoked = admin_client.post(f"/api/identity/api-keys/{key_id}/revoke")
    assert revoked.status_code == 200
    assert revoked.json()["data"]["is_active"] is False


def test_create_unknown_role_is_400(admin_client):
    resp = admin_client.post("/api/identity/api-keys", {"name": "Bot", "role": "NoSuchRole"})
    assert resp.status_code == 400


def test_revoke_unknown_key_is_404(admin_client):
    resp = admin_client.post("/api/identity/api-keys/999999/revoke")
    assert resp.status_code == 404


def test_api_docs_lists_routes_and_is_admin_only(admin_client, plain_client):
    resp = admin_client.get("/api/identity/api-docs")
    assert resp.status_code == 200
    routes = resp.json()["data"]["routes"]
    assert any(r["path"].startswith("api/identity/api-keys") for r in routes)

    assert plain_client.get("/api/identity/api-docs").status_code == 403
