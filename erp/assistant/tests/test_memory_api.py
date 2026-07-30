"""Memory API (ai-reliability T4.4): actor-scoped list, slot edit, delete, proposal decisions.

RBAC first, as the plan asks: user A can never see or delete user B's memory, and organization
memory is admin-only to change (visible to everyone, since it explains the assistant's behaviour).
"""
from __future__ import annotations

import pytest
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from erp.assistant.models import OrgMemory, UserMemory
from erp.assistant.services import memory as memory_service
from erp.identity.models import RolePermission, User
from erp.identity.roles import SYSTEM_ADMIN

pytestmark = pytest.mark.django_db

URL = "/api/assistant/memory"


@pytest.fixture(autouse=True)
def _no_embeddings(monkeypatch):
    monkeypatch.setattr(memory_service.gateway, "embed_text", lambda text: None)


def _user(username: str) -> User:
    return User.objects.create_user(username=username, email=f"{username}@example.test",
                                    password="Dev12345!")


def _admin(username: str = "mem_api_admin") -> User:
    user = _user(username)
    group, _ = Group.objects.get_or_create(name=SYSTEM_ADMIN)
    RolePermission.objects.update_or_create(role=group, code="assistant.memory.manage",
                                            defaults={"scope": "all"})
    user.groups.add(group)
    return user


def _client(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def test_list_returns_only_the_callers_personal_memories():
    alice, bob = _user("mem_api_alice"), _user("mem_api_bob")
    memory_service.remember(alice, scope="user", kind="fact", value="Alice ships on Thursdays.")
    memory_service.remember(bob, scope="user", kind="fact", value="Bob prefers cartons.")

    body = _client(alice).get(URL).json()["data"]

    values = [row["value"] for row in body["personal"]]
    assert values == ["Alice ships on Thursdays."]
    assert body["org"] == []
    assert "language" in body["slot_keys"]


def test_another_users_memory_cannot_be_deleted():
    alice, bob = _user("mem_api_alice2"), _user("mem_api_bob2")
    row = memory_service.remember(bob, scope="user", kind="fact", value="Bob's own note.")

    response = _client(alice).delete(f"{URL}/{row.pk}")

    assert response.status_code == 404
    assert UserMemory.objects.filter(pk=row.pk).exists()


def test_own_memory_delete_hard_deletes():
    alice = _user("mem_api_alice3")
    row = memory_service.remember(alice, scope="user", kind="fact", value="Alice's own note.")

    assert _client(alice).delete(f"{URL}/{row.pk}").status_code == 204
    assert not UserMemory.objects.filter(pk=row.pk).exists()


def test_slot_edit_from_the_page_records_the_settings_source():
    alice = _user("mem_api_alice4")

    response = _client(alice).put(URL, {"key": "language", "value": "ar"}, format="json")

    assert response.status_code == 201
    row = UserMemory.objects.get(pk=response.json()["data"]["id"])
    assert (row.key, row.value, row.source) == ("language", "ar", "settings")


def test_invalid_slot_value_is_refused_with_a_calm_error():
    alice = _user("mem_api_alice5")
    response = _client(alice).put(URL, {"key": "language", "value": "fr"}, format="json")
    assert response.status_code == 400
    assert not UserMemory.objects.filter(kind="slot").exists()


def test_org_memory_write_and_delete_need_an_admin():
    plain, admin = _user("mem_api_plain"), _admin()

    assert _client(plain).put(URL, {"key": "default_warehouse", "value": "WH-1", "scope": "org"},
                              format="json").status_code == 403

    created = _client(admin).put(URL, {"key": "default_warehouse", "value": "WH-1",
                                       "scope": "org"}, format="json")
    assert created.status_code == 201
    org_id = created.json()["data"]["id"]

    assert _client(plain).delete(f"{URL}/{org_id}?scope=org").status_code == 403
    assert OrgMemory.objects.filter(pk=org_id).exists()
    assert _client(admin).delete(f"{URL}/{org_id}?scope=org").status_code == 204


def test_org_memory_is_visible_to_every_member():
    admin, plain = _admin("mem_api_admin2"), _user("mem_api_plain2")
    memory_service.remember(admin, scope="org", kind="fact", value="The fiscal year starts in July.")

    body = _client(plain).get(URL).json()["data"]
    assert [row["value"] for row in body["org"]] == ["The fiscal year starts in July."]


def test_proposal_confirm_writes_with_the_pattern_source_and_dismiss_suppresses():
    alice = _user("mem_api_alice6")

    confirmed = _client(alice).post(f"{URL}/proposals",
                                    {"decision": "confirm", "slot": "default_warehouse",
                                     "value": "WH-22"}, format="json")
    assert confirmed.status_code == 200
    assert UserMemory.objects.get(pk=confirmed.json()["data"]["id"]).source == "pattern"

    dismissed = _client(alice).post(f"{URL}/proposals",
                                     {"decision": "dismiss", "slot": "language"}, format="json")
    assert dismissed.status_code == 200
    assert memory_service._control_row(alice, "_suppress:language") is not None


def test_memory_endpoints_require_authentication():
    assert APIClient().get(URL).status_code in (401, 403)
