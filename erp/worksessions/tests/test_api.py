import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()
pytestmark = pytest.mark.django_db


def _client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def test_requires_authentication():
    resp = APIClient().get("/api/worksessions/active?workflow_key=k")
    assert resp.status_code in (401, 403)


def test_upsert_then_fetch_active_roundtrips():
    user = User.objects.create_user(username="u", password="x", email="u@t.co")
    c = _client(user)
    resp = c.post("/api/worksessions/", {
        "workflow_key": "sales.customer.create",
        "payload": {"name": "Acme"},
        "schema_version": 1,
        "client_version": 1,
    }, format="json")
    assert resp.status_code == 201
    body = resp.json()["data"]
    assert body["conflict"] is False
    assert body["session"]["payload"] == {"name": "Acme"}

    active = c.get("/api/worksessions/active?workflow_key=sales.customer.create").json()["data"]
    assert active is not None
    assert active["payload"] == {"name": "Acme"}


def test_user_cannot_access_another_users_draft():
    a = User.objects.create_user(username="a", password="x", email="a@t.co")
    b = User.objects.create_user(username="b", password="x", email="b@t.co")
    session_id = _client(a).post("/api/worksessions/", {
        "workflow_key": "k", "payload": {"v": 1}, "schema_version": 1, "client_version": 1,
    }, format="json").json()["data"]["session"]["id"]

    resp = _client(b).post(f"/api/worksessions/{session_id}/discard", {}, format="json")
    assert resp.status_code == 403  # owner-scoped: PermissionError -> 403


def test_complete_marks_the_draft_completed():
    user = User.objects.create_user(username="u", password="x", email="u@t.co")
    c = _client(user)
    session_id = c.post("/api/worksessions/", {
        "workflow_key": "k", "payload": {"v": 1}, "schema_version": 1, "client_version": 1,
    }, format="json").json()["data"]["session"]["id"]

    done = c.post(f"/api/worksessions/{session_id}/complete", {"related_entity_id": "C-9"}, format="json")
    assert done.status_code == 200
    assert done.json()["data"]["status"] == "completed"
    # No longer offered as an active draft.
    assert c.get("/api/worksessions/active?workflow_key=k").json()["data"] is None
