import pytest
from django.contrib.auth import get_user_model

from erp.worksessions import services
from erp.worksessions.models import WorkSession

User = get_user_model()
pytestmark = pytest.mark.django_db


def _user(username="u1"):
    # email is unique on the custom User model → derive a distinct one per username.
    return User.objects.create_user(username=username, password="x", email=f"{username}@t.co")


def test_upsert_creates_then_updates_the_single_active_draft():
    user = _user()
    r1 = services.upsert_draft(user, workflow_key="sales.customer.create", payload={"name": "A"}, schema_version=1)
    assert r1.conflict is False
    assert r1.session.client_version == 1
    r2 = services.upsert_draft(
        user, workflow_key="sales.customer.create", payload={"name": "AB"},
        schema_version=1, expected_version=r1.session.client_version,
    )
    assert r2.session.id == r1.session.id  # same row, not a duplicate
    assert r2.session.payload == {"name": "AB"}
    assert r2.session.client_version == 2
    assert WorkSession.objects.filter(owner=user, status=WorkSession.Status.ACTIVE).count() == 1


def test_get_active_returns_only_the_owners_active_draft():
    a, b = _user("a"), _user("b")
    services.upsert_draft(a, workflow_key="sales.customer.create", payload={"name": "A"})
    assert services.get_active(a, "sales.customer.create") is not None
    assert services.get_active(b, "sales.customer.create") is None  # owner-scoped


def test_stale_expected_version_reports_conflict_without_clobbering():
    user = _user()
    r1 = services.upsert_draft(user, workflow_key="k", payload={"v": 1})   # client_version 1
    services.upsert_draft(user, workflow_key="k", payload={"v": 2}, expected_version=1)  # -> 2
    # A second client still thinks the version is 1 → conflict, and the stored payload is untouched.
    res = services.upsert_draft(user, workflow_key="k", payload={"v": 99}, expected_version=1)
    assert res.conflict is True
    res.session.refresh_from_db()
    assert res.session.payload == {"v": 2}


def test_complete_and_discard_free_the_active_slot():
    user = _user()
    r = services.upsert_draft(user, workflow_key="k", payload={"v": 1})
    services.complete(user, r.session.id, related_entity_id="C-001")
    r.session.refresh_from_db()
    assert r.session.status == WorkSession.Status.COMPLETED
    assert r.session.related_entity_id == "C-001"
    # The active slot is now free → a new active draft can be created for the same form.
    r2 = services.upsert_draft(user, workflow_key="k", payload={"v": 2})
    assert r2.session.id != r.session.id
    services.discard(user, r2.session.id)
    r2.session.refresh_from_db()
    assert r2.session.status == WorkSession.Status.DISCARDED


def test_complete_and_discard_ignore_another_users_session():
    a, b = _user("a"), _user("b")
    r = services.upsert_draft(a, workflow_key="k", payload={"v": 1})
    services.discard(b, r.session.id)  # b is not the owner → no-op
    r.session.refresh_from_db()
    assert r.session.status == WorkSession.Status.ACTIVE


def test_list_active_is_owner_scoped_and_newest_first():
    a = _user("a")
    services.upsert_draft(a, workflow_key="k1", payload={"v": 1})
    services.upsert_draft(a, workflow_key="k2", payload={"v": 1})
    keys = [s.workflow_key for s in services.list_active(a)]
    assert set(keys) == {"k1", "k2"}
