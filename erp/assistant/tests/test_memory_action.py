"""The ``remember_memory`` action (ai-reliability T4.2): the assistant proposes, the human confirms.

Same pattern as the other write actions — ``actions.build`` prepares a card and writes nothing;
``actions.execute`` performs the write only after a confirm. Refusals (secrets, another user's data,
non-admin org scope) live in the blocking ``test_memory_leakage.py``.
"""
from __future__ import annotations

import pytest
from django.contrib.auth.models import Group

from erp.assistant.models import OrgMemory, UserMemory
from erp.assistant.services import actions, memory as memory_service
from erp.audit.models import AuditEntry
from erp.identity.models import RolePermission, User
from erp.identity.roles import SYSTEM_ADMIN

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _no_embeddings(monkeypatch):
    monkeypatch.setattr(memory_service.gateway, "embed_text", lambda text: None)


def _user(username: str = "act_mem_user") -> User:
    return User.objects.create_user(username=username, email=f"{username}@example.test",
                                    password="Dev12345!")


def _admin(username: str = "act_mem_admin") -> User:
    user = _user(username)
    group, _ = Group.objects.get_or_create(name=SYSTEM_ADMIN)
    RolePermission.objects.update_or_create(role=group, code="assistant.memory.manage",
                                            defaults={"scope": "all"})
    user.groups.add(group)
    return user


def test_the_action_is_registered_and_always_confirmable():
    action = actions.ACTIONS["remember_memory"]
    assert action.requires_confirm is True
    assert "remember_memory" in actions.catalog_text()


def test_build_proposes_and_writes_nothing():
    user = _user()

    proposal = actions.build(user, "remember_memory",
                             {"value": "I always order from Nile Supplies first."})

    assert proposal["summary"] == ['Remember for you: "I always order from Nile Supplies first."']
    assert proposal["payload"] == {"scope": "user", "kind": "fact", "key": "",
                                   "value": "I always order from Nile Supplies first."}
    assert not UserMemory.objects.exists()


def test_confirm_executes_the_write_and_links_to_the_memory_page():
    user = _user()
    proposal = actions.build(user, "remember_memory", {"value": "I close the month on the 3rd."})

    result = actions.execute(user, "remember_memory", proposal["payload"])

    row = UserMemory.objects.get()
    assert (row.value, row.kind, row.source) == ("I close the month on the 3rd.", "fact", "explicit")
    assert result["links"][0]["type"] == "memory"
    assert AuditEntry.objects.filter(action="remember_memory").exists()


def test_a_known_setting_becomes_a_slot_not_a_note():
    user = _user()
    proposal = actions.build(user, "remember_memory",
                             {"value": "WH-05", "key": "default_warehouse", "type": "setting"})

    assert proposal["payload"]["kind"] == "slot"
    actions.execute(user, "remember_memory", proposal["payload"])
    assert memory_service.slots_for(user) == {"default_warehouse": "WH-05"}


def test_an_unknown_setting_name_is_offered_as_a_note_instead():
    user = _user()
    proposal = actions.build(user, "remember_memory",
                             {"value": "green", "key": "favourite_colour", "type": "setting"})
    assert "error" in proposal and "note" in proposal["error"]


def test_an_admin_can_remember_for_the_whole_organization_with_a_stated_risk():
    admin = _admin()
    proposal = actions.build(admin, "remember_memory",
                             {"value": "The fiscal year starts in July.", "scope": "org"})

    assert proposal["risks"]  # the card says who else will see it
    actions.execute(admin, "remember_memory", proposal["payload"])
    assert OrgMemory.objects.get().value == "The fiscal year starts in July."


def test_an_empty_or_over_long_sentence_is_refused_before_the_card():
    user = _user()
    assert "error" in actions.build(user, "remember_memory", {"value": "   "})
    too_long = "x" * (memory_service.MAX_VALUE_CHARS + 1)
    assert "error" in actions.build(user, "remember_memory", {"value": too_long})
