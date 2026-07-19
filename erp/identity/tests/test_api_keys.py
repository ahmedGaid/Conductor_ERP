"""TH FILE_14 Task D — API key auth, service, RBAC enforcement, audit, hashed storage.

Runs under gate01 (erp/identity/tests). No `apps/web` surface is exercised here (Task B/C, out of
scope for this backend-only session).
"""
from __future__ import annotations

import datetime as dt

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone
from rest_framework.test import APIClient

from erp.audit.models import AuditEntry
from erp.core.errors import PermissionError as AppPermissionError
from erp.core.errors import ValidationError
from erp.identity import access, api_keys, rbac
from erp.identity.authentication import hash_secret
from erp.identity.models import ApiKey
from erp.identity.roles import SYSTEM_ADMIN

User = get_user_model()


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def admin(db):
    Group.objects.get_or_create(name=SYSTEM_ADMIN)
    u = User.objects.create_user(username="root", email="root@erp.local", password="pw12345!")
    u.groups.add(Group.objects.get(name=SYSTEM_ADMIN))
    return u


@pytest.fixture
def non_admin(db):
    return User.objects.create_user(username="plain", email="plain@erp.local", password="pw12345!")


def _grant(group_name, code, scope=rbac.DataScope.ALL):
    from erp.identity.models import RolePermission

    g, _ = Group.objects.get_or_create(name=group_name)
    RolePermission.objects.update_or_create(role=g, code=code, defaults={"scope": scope})
    return g


# --- Service layer -------------------------------------------------------------------------------

def test_create_key_is_admin_only(non_admin):
    with pytest.raises(AppPermissionError):
        api_keys.create_key("Bad", SYSTEM_ADMIN, actor=non_admin)


def test_create_key_unknown_role_rejected(admin):
    with pytest.raises(ValidationError):
        api_keys.create_key("Bot", "NoSuchRole", actor=admin)


def test_create_key_stores_only_the_hash(admin):
    role = _grant("Viewer", "administration.user.view")
    api_key, raw_secret = api_keys.create_key("Reporting bot", role.name, actor=admin)

    assert raw_secret.startswith(f"ck_{api_key.prefix}_")
    assert api_key.hashed_key == hash_secret(raw_secret)
    assert api_key.hashed_key != raw_secret
    # The raw secret is nowhere in the persisted row.
    stored = ApiKey.objects.get(pk=api_key.pk)
    assert raw_secret not in vars(stored).values()


def test_create_key_principal_carries_the_bound_role_and_is_not_a_login(admin):
    role = _grant("Viewer", "administration.user.view")
    api_key, _raw = api_keys.create_key("Bot", role.name, actor=admin)

    assert role.name in api_key.principal.roles
    assert api_key.principal.has_usable_password() is False
    assert access.has_permission(api_key.principal, "administration.user.view") is True
    assert access.has_permission(api_key.principal, "administration.user.delete") is False


def test_revoke_and_list_are_admin_only(admin, non_admin):
    role = _grant("Viewer", "administration.user.view")
    api_key, _raw = api_keys.create_key("Bot", role.name, actor=admin)

    with pytest.raises(AppPermissionError):
        api_keys.revoke_key(api_key.pk, actor=non_admin)
    with pytest.raises(AppPermissionError):
        api_keys.list_keys(actor=non_admin)

    api_keys.revoke_key(api_key.pk, actor=admin)
    assert ApiKey.objects.get(pk=api_key.pk).is_active is False
    assert any(row["id"] == api_key.pk for row in api_keys.list_keys(actor=admin))


# --- Authentication + endpoint behaviour ----------------------------------------------------------

def _auth(client, raw_secret):
    client.credentials(HTTP_AUTHORIZATION="Api-Key " + raw_secret)


def test_valid_key_authenticates_and_is_scoped_to_its_role(client, admin):
    role = _grant("Viewer", "administration.user.view")
    _api_key, raw = api_keys.create_key("Bot", role.name, actor=admin)

    _auth(client, raw)
    resp = client.get("/api/identity/users")
    assert resp.status_code == 200


def test_key_with_read_only_role_rejected_on_write(client, admin):
    role = _grant("Viewer", "administration.user.view")
    _api_key, raw = api_keys.create_key("Bot", role.name, actor=admin)

    _auth(client, raw)
    resp = client.post("/api/identity/users", {"username": "x", "email": "x@erp.local"}, format="json")
    assert resp.status_code == 403


def test_revoked_key_is_401(client, admin):
    role = _grant("Viewer", "administration.user.view")
    api_key, raw = api_keys.create_key("Bot", role.name, actor=admin)
    api_keys.revoke_key(api_key.pk, actor=admin)

    _auth(client, raw)
    resp = client.get("/api/identity/users")
    assert resp.status_code == 401


def test_expired_key_is_401(client, admin):
    role = _grant("Viewer", "administration.user.view")
    api_key, raw = api_keys.create_key(
        "Bot", role.name, expires_at=timezone.now() - dt.timedelta(minutes=1), actor=admin
    )

    _auth(client, raw)
    resp = client.get("/api/identity/users")
    assert resp.status_code == 401


def test_unknown_or_malformed_key_is_401(client, db):
    _auth(client, "ck_deadbeef_not-a-real-secret")
    assert client.get("/api/identity/users").status_code == 401

    client.credentials(HTTP_AUTHORIZATION="Api-Key")
    assert client.get("/api/identity/users").status_code == 401


def test_key_updates_last_used_at(client, admin):
    role = _grant("Viewer", "administration.user.view")
    api_key, raw = api_keys.create_key("Bot", role.name, actor=admin)
    assert api_key.last_used_at is None

    _auth(client, raw)
    client.get("/api/identity/users")
    assert ApiKey.objects.get(pk=api_key.pk).last_used_at is not None


def test_key_traffic_is_absent_from_the_human_users_list(client, admin):
    role = _grant("Viewer", "administration.user.view")
    api_keys.create_key("Bot", role.name, actor=admin)

    client.credentials(HTTP_AUTHORIZATION="Bearer " + _access_token(admin))
    resp = client.get("/api/identity/users")
    usernames = [row["username"] for row in resp.json()["data"]]
    assert "root" in usernames
    assert not any(u.startswith("apikey:") for u in usernames)


# --- Audit ------------------------------------------------------------------------------------

def test_audit_records_the_key_principal_not_a_human(client, admin):
    _grant("Bot role", "administration.user.create")
    _grant("Bot role", "administration.user.view")
    api_key, raw = api_keys.create_key("Bot", "Bot role", actor=admin)

    _auth(client, raw)
    resp = client.post(
        "/api/identity/users", {"username": "created-by-bot", "email": "bot-made@erp.local"}, format="json"
    )
    assert resp.status_code == 201

    entry = AuditEntry.objects.filter(action="create_user", entity_type="User").latest("created_at")
    assert entry.actor_id == api_key.principal_id
    assert entry.actor_id != admin.pk


def _access_token(user) -> str:
    from rest_framework_simplejwt.tokens import RefreshToken

    return str(RefreshToken.for_user(user).access_token)
