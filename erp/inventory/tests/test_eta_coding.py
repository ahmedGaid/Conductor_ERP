"""FILE_06 — item ETA product-identity coding: PATCH + suggestion endpoint."""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from erp.identity.models import User

pytestmark = pytest.mark.django_db


def _admin_client() -> APIClient:
    user = User.objects.create_user(username="inv_eta_admin", password="Dev12345!")
    user.is_superuser = True
    user.save(update_fields=["is_superuser"])
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _create_item(client, sku="WIDGET"):
    res = client.post("/api/inventory/items", {"sku": sku, "name": "Widget"}, format="json")
    assert res.status_code == 201, res.data
    return res.data["data"]


def test_item_defaults_to_not_submitted():
    client = _admin_client()
    item = _create_item(client)
    assert item["gpc_code"] == ""
    assert item["eta_item_code"] == ""
    assert item["eta_code_status"] == "not_submitted"


def test_patch_updates_eta_coding_fields():
    client = _admin_client()
    _create_item(client)
    res = client.patch(
        "/api/inventory/items/WIDGET",
        {"gpc_code": "10006017", "eta_item_code": "WIDGET10006017123456789EGS", "eta_code_status": "accepted"},
        format="json",
    )
    assert res.status_code == 200, res.data
    data = res.data["data"]
    assert data["gpc_code"] == "10006017"
    assert data["eta_item_code"] == "WIDGET10006017123456789EGS"
    assert data["eta_code_status"] == "accepted"

    # persisted, not just echoed
    fetched = client.get("/api/inventory/items/WIDGET").data["data"]["item"]
    assert fetched["eta_code_status"] == "accepted"


def test_patch_partial_leaves_other_fields_untouched():
    client = _admin_client()
    _create_item(client)
    client.patch("/api/inventory/items/WIDGET", {"gpc_code": "10006017"}, format="json")
    res = client.patch("/api/inventory/items/WIDGET", {"eta_code_status": "pending"}, format="json")
    data = res.data["data"]
    assert data["gpc_code"] == "10006017"
    assert data["eta_code_status"] == "pending"


def test_suggestion_missing_gpc_and_rin():
    client = _admin_client()
    _create_item(client)
    res = client.get("/api/inventory/items/WIDGET/eta-code-suggestion")
    assert res.status_code == 200
    data = res.data["data"]
    assert data["suggestion"] == ""
    assert set(data["missing"]) == {"gpc_code", "rin"}


def test_suggestion_missing_rin_only():
    client = _admin_client()
    _create_item(client)
    client.patch("/api/inventory/items/WIDGET", {"gpc_code": "10006017"}, format="json")
    res = client.get("/api/inventory/items/WIDGET/eta-code-suggestion")
    data = res.data["data"]
    assert data["suggestion"] == ""
    assert data["missing"] == ["rin"]


def test_suggestion_composes_when_gpc_and_rin_present(monkeypatch):
    from erp.einvoice import contracts as einvoice_contracts

    monkeypatch.setattr(einvoice_contracts, "current_rin", lambda: "123456789")
    client = _admin_client()
    _create_item(client)
    client.patch("/api/inventory/items/WIDGET", {"gpc_code": "10006017"}, format="json")
    res = client.get("/api/inventory/items/WIDGET/eta-code-suggestion")
    data = res.data["data"]
    assert data["missing"] == []
    assert data["suggestion"] == "WIDGET10006017123456789EGS"
