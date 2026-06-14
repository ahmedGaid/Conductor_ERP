"""Inventory DRF API — items, warehouses, movements, reports, guards, RBAC."""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from erp.identity.models import User

from .factories import make_gl

pytestmark = pytest.mark.django_db


def _admin_client() -> APIClient:
    user = User.objects.create_user(username="inv_admin", password="Dev12345!")
    user.is_superuser = True
    user.save(update_fields=["is_superuser"])
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _bootstrap(client):
    assert client.post("/api/inventory/items", {"sku": "WIDGET", "name": "Widget"}, format="json").status_code == 201
    assert client.post("/api/inventory/warehouses", {"code": "MAIN", "name": "Main"}, format="json").status_code == 201


def _receive(client, qty, cost, date="2026-06-15"):
    return client.post(
        "/api/inventory/movements/receive",
        {"item_sku": "WIDGET", "warehouse_code": "MAIN", "quantity": qty, "unit_cost": cost, "date": date},
        format="json",
    )


def test_receive_and_stock_on_hand_via_api():
    make_gl()
    client = _admin_client()
    _bootstrap(client)
    res = _receive(client, "10", 100_00)
    assert res.status_code == 201, res.data
    assert res.data["data"]["journal_number"]

    soh = client.get("/api/inventory/reports/stock-on-hand").data["data"]
    assert soh["total_value_minor"] == 1000_00
    assert soh["rows"][0]["sku"] == "WIDGET"


def test_issue_and_oversell_guard_via_api():
    make_gl()
    client = _admin_client()
    _bootstrap(client)
    _receive(client, "5", 100_00)

    ok = client.post(
        "/api/inventory/movements/issue",
        {"item_sku": "WIDGET", "warehouse_code": "MAIN", "quantity": "3", "date": "2026-06-15"},
        format="json",
    )
    assert ok.status_code == 201, ok.data

    over = client.post(
        "/api/inventory/movements/issue",
        {"item_sku": "WIDGET", "warehouse_code": "MAIN", "quantity": "10", "date": "2026-06-15"},
        format="json",
    )
    assert over.status_code == 422
    assert over.data["error"]["code"] == "INV-001"


def test_inventory_requires_role():
    plain = User.objects.create_user(username="nobody_inv", password="Dev12345!")
    client = APIClient()
    client.force_authenticate(user=plain)
    assert client.get("/api/inventory/items").status_code == 403


def test_requires_authentication():
    assert APIClient().get("/api/inventory/items").status_code == 401
