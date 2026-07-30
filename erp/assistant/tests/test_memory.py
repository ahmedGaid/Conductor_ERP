"""Memory service (ai-reliability Phase 4): the governed write path, recall, and the pattern
detectors. Leakage/injection lives in ``test_memory_leakage.py`` (blocking); the write-path
invariant in ``test_memory_write_path.py``.
"""
from __future__ import annotations

import datetime

import pytest
from django.contrib.auth.models import Group
from django.utils import timezone

from erp.assistant.models import (
    Conversation,
    Message,
    MemoryKind,
    OrgMemory,
    SemanticCache,
    UserMemory,
)
from erp.assistant.services import context, memory as memory_service, suggestions
from erp.audit.models import AuditEntry
from erp.identity.models import RolePermission, User
from erp.identity.roles import SYSTEM_ADMIN

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _no_embeddings(monkeypatch):
    """Facts embed through the gateway; the suite never calls a provider. ``None`` is the same
    fail-open path a deployment without embeddings takes."""
    monkeypatch.setattr(memory_service.gateway, "embed_text", lambda text: None)


def _user(username: str = "mem_user") -> User:
    return User.objects.create_user(username=username, email=f"{username}@example.test",
                                    password="Dev12345!")


def _admin(username: str = "mem_admin") -> User:
    user = _user(username)
    group, _ = Group.objects.get_or_create(name=SYSTEM_ADMIN)
    RolePermission.objects.update_or_create(role=group, code="assistant.memory.manage",
                                            defaults={"scope": "all"})
    user.groups.add(group)
    return user


def _confirmed_proposal(user: User, payload: dict, *, created_at=None) -> Message:
    conversation = Conversation.objects.create(user=user)
    message = Message.objects.create(
        conversation=conversation, role=Message.Role.ASSISTANT, content="",
        meta={"proposal": {"action": "create_purchase_order_draft", "status": "confirmed",
                           "payload": payload}},
    )
    if created_at is not None:
        Message.objects.filter(pk=message.pk).update(created_at=created_at)
    return message


# --- T4.1 write path ----------------------------------------------------------------------------

def test_slot_write_supersedes_the_previous_value_and_keeps_the_chain():
    user = _user()
    first = memory_service.remember(user, scope="user", kind="slot", key="default_warehouse",
                                    value="WH-01")
    second = memory_service.remember(user, scope="user", kind="slot", key="default_warehouse",
                                     value="WH-02")

    first.refresh_from_db()
    assert first.superseded_by_id == second.pk
    assert memory_service.slots_for(user)["default_warehouse"] == "WH-02"
    # History survives: both rows still exist, only one is active.
    assert UserMemory.objects.filter(key="default_warehouse").count() == 2


def test_unknown_slot_key_and_bad_slot_value_are_refused():
    user = _user()
    with pytest.raises(Exception):
        memory_service.remember(user, scope="user", kind="slot", key="favourite_colour",
                                value="blue")
    with pytest.raises(Exception):
        memory_service.remember(user, scope="user", kind="slot", key="language", value="fr")


def test_expired_fact_is_not_recalled():
    user = _user()
    live = memory_service.remember(user, scope="user", kind="fact",
                                   value="The user reconciles the bank on Sundays.")
    stale = memory_service.remember(user, scope="user", kind="fact",
                                    value="The user is on leave this week.")
    UserMemory.objects.filter(pk=stale.pk).update(
        expires_at=timezone.now() - datetime.timedelta(hours=1))

    block = memory_service.recall(user)
    assert live.value in block
    assert stale.value not in block


def test_forget_removes_the_content_but_keeps_the_audit_event():
    user = _user()
    row = memory_service.remember(user, scope="user", kind="fact",
                                  value="The user prefers weekly digests.")

    memory_service.forget(user, row.pk)

    assert not UserMemory.objects.filter(pk=row.pk).exists()
    event = AuditEntry.objects.filter(action="forget_memory").latest("id")
    assert event.before["kind"] == MemoryKind.FACT
    assert "prefers weekly digests" not in (event.before or {}).get("key", "")
    assert "prefers weekly digests" not in str(event.after or "")


def test_every_write_is_audited_with_the_confirmed_sentence():
    user = _user()
    memory_service.remember(user, scope="user", kind="fact", value="The user works from Alexandria.")
    event = AuditEntry.objects.filter(action="remember_memory").latest("id")
    assert event.after["value"] == "The user works from Alexandria."
    assert event.after["source"] == "explicit"
    assert event.actor_id == user.pk


def test_forgetting_drops_the_users_semantic_cache_rows():
    user = _user()
    other = _user("mem_other")
    row = memory_service.remember(user, scope="user", kind="fact", value="The user prefers cartons.")
    SemanticCache.objects.create(user=user, question_text="q", question_embedding=[0.1],
                                 answer="stale answer")
    SemanticCache.objects.create(user=other, question_text="q", question_embedding=[0.1],
                                 answer="other user's answer")

    memory_service.forget(user, row.pk)

    assert not SemanticCache.objects.filter(user=user).exists()
    assert SemanticCache.objects.filter(user=other).exists()


def test_org_memory_needs_an_admin():
    plain = _user("mem_plain")
    with pytest.raises(PermissionError):
        memory_service.remember(plain, scope="org", kind="fact",
                                value="The fiscal year starts in July.")

    admin = _admin()
    row = memory_service.remember(admin, scope="org", kind="fact",
                                  value="The fiscal year starts in July.")
    assert OrgMemory.objects.filter(pk=row.pk).exists()
    assert row.written_by_id == admin.pk


def test_recall_puts_slots_first_and_org_slots_are_overridden_by_personal_ones():
    admin = _admin()
    memory_service.remember(admin, scope="org", kind="slot", key="default_warehouse", value="WH-ORG")
    memory_service.remember(admin, scope="user", kind="slot", key="default_warehouse", value="WH-ME")

    block = memory_service.recall(admin)
    assert "- default_warehouse: WH-ME" in block
    assert "WH-ORG" not in block


def test_recall_ranks_by_similarity_only_past_the_threshold(monkeypatch):
    user = _user()
    for i in range(memory_service.SIMILARITY_THRESHOLD + 2):
        memory_service.remember(user, scope="user", kind="fact", value=f"Fact number {i}.")
    target = UserMemory.objects.filter(value="Fact number 3.").get()
    UserMemory.objects.filter(pk=target.pk).update(embedding=[1.0, 0.0])
    monkeypatch.setattr(memory_service.gateway, "embed_text", lambda text: [1.0, 0.0])

    block = memory_service.recall(user, "which fact matters")

    assert "Fact number 3." in block
    # Capped, never "every fact I ever kept".
    assert block.count("\n- ") <= memory_service.MAX_RECALLED_FACTS


def test_recall_is_empty_when_nothing_is_remembered():
    assert memory_service.recall(_user()) == ""


def test_budget_trims_facts_before_giving_up():
    user = _user()
    memory_service.remember(user, scope="user", kind="slot", key="language", value="ar")
    memory_service.remember(user, scope="user", kind="fact", value="A" * 200)

    tight = memory_service.recall(user, budget_tokens=40)
    assert "- language: ar" in tight
    assert "A" * 200 not in tight


def test_degrade_block_drops_facts_and_keeps_slots():
    user = _user()
    memory_service.remember(user, scope="user", kind="slot", key="language", value="en")
    memory_service.remember(user, scope="user", kind="fact", value="The user audits stock weekly.")
    block = memory_service.recall(user)

    shorter = memory_service.degrade_block(block)
    assert "- language: en" in shorter
    assert "audits stock weekly" not in shorter
    # Nothing left to drop the second time.
    assert memory_service.degrade_block(shorter) is None


# --- T4.5 envelope integration ------------------------------------------------------------------

def test_memory_reaches_the_system_prompt_as_its_own_section():
    user = _user()
    memory_service.remember(user, scope="user", kind="slot", key="default_warehouse", value="WH-07")

    prompt, meta = context.build_system_prompt_with_meta(user, page=None, message="draft a PO")

    assert "- default_warehouse: WH-07" in prompt
    assert meta["memory"]["dropped"] is False
    assert meta["memory"]["tokens"] > 0


def test_no_memory_section_when_the_user_has_none():
    _, meta = context.build_system_prompt_with_meta(_user(), page=None, message="draft a PO")
    assert "memory" not in meta


# --- T4.3 pattern detectors ---------------------------------------------------------------------

def test_repeated_choice_needs_three_occurrences():
    user = _user()
    for _ in range(2):
        _confirmed_proposal(user, {"warehouse_code": "WH-09"})
    assert memory_service.detect_repeated_slot_choice(user) is None

    _confirmed_proposal(user, {"warehouse_code": "WH-09"})
    proposal = memory_service.detect_repeated_slot_choice(user)
    assert proposal == {"slot": "default_warehouse", "value": "WH-09", "occurrences": 3,
                        "detector": "repeated_choice"}


def test_repeated_choice_ignores_old_confirmations_and_already_known_slots():
    user = _user()
    old = timezone.now() - datetime.timedelta(days=45)
    for _ in range(3):
        _confirmed_proposal(user, {"warehouse_code": "WH-OLD"}, created_at=old)
    assert memory_service.detect_repeated_slot_choice(user) is None

    for _ in range(3):
        _confirmed_proposal(user, {"warehouse_code": "WH-11"})
    memory_service.remember(user, scope="user", kind="slot", key="default_warehouse", value="WH-11")
    assert memory_service.detect_repeated_slot_choice(user) is None


def test_dismissed_proposals_are_never_confirmed_choices():
    user = _user()
    conversation = Conversation.objects.create(user=user)
    for _ in range(3):
        Message.objects.create(conversation=conversation, role=Message.Role.ASSISTANT,
                               meta={"proposal": {"status": "dismissed",
                                                  "payload": {"warehouse_code": "WH-12"}}})
    assert memory_service.detect_repeated_slot_choice(user) is None


def test_language_correction_detector_needs_two_corrections():
    user = _user()
    conversation = Conversation.objects.create(user=user)
    Message.objects.create(conversation=conversation, role=Message.Role.USER,
                           content="جاوب بالعربي من فضلك")
    assert memory_service.detect_language_correction(user) is None

    Message.objects.create(conversation=conversation, role=Message.Role.USER,
                           content="بالعربية دائمًا")
    proposal = memory_service.detect_language_correction(user)
    assert proposal["slot"] == "language" and proposal["value"] == "ar"


def test_one_proposal_per_user_per_day_and_dismissal_suppresses_it():
    user = _user()
    for _ in range(3):
        _confirmed_proposal(user, {"warehouse_code": "WH-13"})

    first = suggestions.build_memory_proposal(user)
    assert first["slot"] == "default_warehouse" and first["value"] == "WH-13"
    # A re-read the same day returns the SAME proposal — the cap is one proposal, not one read
    # (a remount or a second tab must not swallow the card).
    assert suggestions.build_memory_proposal(user) == first

    later = timezone.now() + datetime.timedelta(days=2)
    assert suggestions.build_memory_proposal(user, now=later) is not None

    memory_service.suppress_proposal(user, "default_warehouse", now=later)
    much_later = later + datetime.timedelta(days=2)
    assert memory_service.next_proposal(user, now=much_later) is None
    assert memory_service._control_row(user, "_suppress:default_warehouse",
                                       now=much_later) is not None
    # …and the suppression forgets itself after 90 days (the detector's own 30-day window has
    # moved on by then, so this asserts on the suppression row rather than a fresh proposal).
    after_expiry = later + datetime.timedelta(days=91)
    assert memory_service._control_row(user, "_suppress:default_warehouse",
                                       now=after_expiry) is None


def test_a_shown_proposal_stops_coming_back_once_it_is_answered():
    user = _user()
    for _ in range(3):
        _confirmed_proposal(user, {"warehouse_code": "WH-14"})
    shown = suggestions.build_memory_proposal(user)
    assert shown is not None

    # Confirming it (the API's confirm path) sets the slot — the stored proposal is answered.
    memory_service.remember(user, scope="user", kind="slot", key="default_warehouse",
                            value="WH-14", source="pattern")
    assert suggestions.build_memory_proposal(user) is None


def test_a_dismissed_proposal_stops_coming_back_the_same_day():
    user = _user()
    for _ in range(3):
        _confirmed_proposal(user, {"warehouse_code": "WH-15"})
    assert suggestions.build_memory_proposal(user) is not None

    memory_service.suppress_proposal(user, "default_warehouse")
    assert suggestions.build_memory_proposal(user) is None


def test_control_rows_are_never_recalled_or_listed():
    user = _user()
    memory_service.mark_proposal_shown(user)
    memory_service.suppress_proposal(user, "language")

    assert memory_service.recall(user) == ""
    assert memory_service.list_for_actor(user)["personal"] == []
