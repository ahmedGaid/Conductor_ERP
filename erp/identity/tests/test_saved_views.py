"""Saved-view tests — per-list filter presets (FILE_06).

Prove: owner-scoped CRUD, ownership isolation (one user never sees or touches another's views),
and at-most-one-default per (user, list_key).
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from erp.identity.models import SavedView
from erp.identity.roles import ACCOUNTANT

User = get_user_model()

SALES = "sales:orders"


def _user(username):
    Group.objects.get_or_create(name=ACCOUNTANT)
    u = User.objects.create_user(username=username, email=f"{username}@erp.local", password="pw12345!")
    u.groups.add(Group.objects.get(name=ACCOUNTANT))
    return u


def _auth(user):
    c = APIClient()
    tokens = APIClient().post(
        "/api/identity/login", {"username": user.username, "password": "pw12345!"}, format="json"
    ).json()["data"]
    c.credentials(HTTP_AUTHORIZATION="Bearer " + tokens["access"])
    return c


@pytest.fixture
def alice(db):
    return _user("alice")


@pytest.fixture
def bob(db):
    return _user("bob")


def _create(client, list_key=SALES, name="Open orders", query="status=confirmed", is_default=False):
    return client.post(
        "/api/identity/saved-views",
        {"list_key": list_key, "name": name, "query": query, "is_default": is_default},
        format="json",
    )


def test_create_then_list_returns_the_view(alice):
    c = _auth(alice)
    resp = _create(c, name="Confirmed", query="status=confirmed")
    assert resp.status_code == 201
    body = resp.json()["data"]
    assert body["name"] == "Confirmed"
    assert body["query"] == "status=confirmed"
    assert body["is_default"] is False

    listed = c.get("/api/identity/saved-views?list_key=sales:orders").json()["data"]
    assert [v["name"] for v in listed] == ["Confirmed"]


def test_list_is_scoped_by_list_key(alice):
    c = _auth(alice)
    _create(c, list_key="sales:orders", name="A")
    _create(c, list_key="inventory:items", name="B")
    sales = c.get("/api/identity/saved-views?list_key=sales:orders").json()["data"]
    inv = c.get("/api/identity/saved-views?list_key=inventory:items").json()["data"]
    assert [v["name"] for v in sales] == ["A"]
    assert [v["name"] for v in inv] == ["B"]


def test_duplicate_name_per_list_is_rejected(alice):
    c = _auth(alice)
    assert _create(c, name="Dupe").status_code == 201
    assert _create(c, name="Dupe").status_code == 409
    # Same name on a different list is fine.
    assert _create(c, list_key="inventory:items", name="Dupe").status_code == 201


def test_rename_view(alice):
    c = _auth(alice)
    vid = _create(c, name="Old").json()["data"]["id"]
    resp = c.patch(f"/api/identity/saved-views/{vid}", {"name": "New"}, format="json")
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "New"


def test_delete_view(alice):
    c = _auth(alice)
    vid = _create(c).json()["data"]["id"]
    assert c.delete(f"/api/identity/saved-views/{vid}").status_code == 204
    assert c.get("/api/identity/saved-views?list_key=sales:orders").json()["data"] == []


def test_set_default_is_unique_per_list(alice):
    c = _auth(alice)
    a = _create(c, name="A").json()["data"]["id"]
    b = _create(c, name="B").json()["data"]["id"]

    assert c.post(f"/api/identity/saved-views/{a}/default").status_code == 200
    assert SavedView.objects.get(pk=a).is_default is True

    # Making B the default unsets A.
    assert c.post(f"/api/identity/saved-views/{b}/default").status_code == 200
    assert SavedView.objects.get(pk=b).is_default is True
    assert SavedView.objects.get(pk=a).is_default is False

    # A default on another list is independent.
    other = _create(c, list_key="inventory:items", name="C").json()["data"]["id"]
    assert c.post(f"/api/identity/saved-views/{other}/default").status_code == 200
    assert SavedView.objects.get(pk=b).is_default is True  # unchanged
    assert SavedView.objects.get(pk=other).is_default is True


def test_created_default_unsets_prior_default(alice):
    c = _auth(alice)
    a = _create(c, name="A", is_default=True).json()["data"]["id"]
    b = _create(c, name="B", is_default=True).json()["data"]["id"]
    assert SavedView.objects.get(pk=a).is_default is False
    assert SavedView.objects.get(pk=b).is_default is True


# --- Ownership isolation ----------------------------------------------------------------------

def test_users_never_see_each_others_views(alice, bob):
    _create(_auth(alice), name="Alice view")
    listed = _auth(bob).get("/api/identity/saved-views?list_key=sales:orders").json()["data"]
    assert listed == []


def test_cannot_rename_another_users_view(alice, bob):
    vid = _create(_auth(alice), name="Alice view").json()["data"]["id"]
    # Bob's attempt is indistinguishable from an unknown id — 404, not 403.
    assert _auth(bob).patch(f"/api/identity/saved-views/{vid}", {"name": "Hijacked"}, format="json").status_code == 404
    assert SavedView.objects.get(pk=vid).name == "Alice view"


def test_cannot_delete_another_users_view(alice, bob):
    vid = _create(_auth(alice), name="Alice view").json()["data"]["id"]
    assert _auth(bob).delete(f"/api/identity/saved-views/{vid}").status_code == 404
    assert SavedView.objects.filter(pk=vid).exists()


def test_cannot_default_another_users_view(alice, bob):
    vid = _create(_auth(alice), name="Alice view").json()["data"]["id"]
    assert _auth(bob).post(f"/api/identity/saved-views/{vid}/default").status_code == 404
    assert SavedView.objects.get(pk=vid).is_default is False


def test_saved_views_require_authentication():
    assert APIClient().get("/api/identity/saved-views?list_key=sales:orders").status_code == 401
