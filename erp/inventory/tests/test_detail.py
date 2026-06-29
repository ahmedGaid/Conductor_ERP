"""Item / warehouse detail endpoints — master record + on-hand + movements."""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from erp.identity.models import User

from .factories import make_gl

pytestmark = pytest.mark.django_db


def _admin_client() -> APIClient:
    user = User.objects.create_user(username="det_admin", password="Dev12345!")
    user.is_superuser = True
    user.save(update_fields=["is_superuser"])
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _bootstrap(client):
    client.post("/api/inventory/items", {"sku": "WIDGET", "name": "Widget"}, format="json")
    client.post("/api/inventory/warehouses", {"code": "MAIN", "name": "Main"}, format="json")
    client.post(
        "/api/inventory/movements/receive",
        {"item_sku": "WIDGET", "warehouse_code": "MAIN", "quantity": "10", "unit_cost": 100_00,
         "date": "2026-06-15"},
        format="json",
    )


def test_item_detail_returns_master_stock_and_movements():
    make_gl()
    client = _admin_client()
    _bootstrap(client)
    res = client.get("/api/inventory/items/WIDGET")
    assert res.status_code == 200, res.data
    data = res.data["data"]
    assert data["item"]["sku"] == "WIDGET"
    assert data["stock"]["total_value_minor"] == 1000_00
    assert data["stock"]["rows"][0]["warehouse_code"] == "MAIN"
    assert len(data["movements"]) == 1
    assert data["movements"][0]["item_sku"] == "WIDGET"


def test_warehouse_detail_returns_master_stock_and_movements():
    make_gl()
    client = _admin_client()
    _bootstrap(client)
    res = client.get("/api/inventory/warehouses/MAIN")
    assert res.status_code == 200, res.data
    data = res.data["data"]
    assert data["warehouse"]["code"] == "MAIN"
    assert data["stock"]["rows"][0]["sku"] == "WIDGET"
    assert data["movements"][0]["warehouse_code"] == "MAIN"


def test_movements_filter_by_reference():
    """The movements list filters by source document reference — powers the workflow tracker's
    delivery/receipt stage snapshot, which looks up the stock moved under one order number."""
    make_gl()
    client = _admin_client()
    _bootstrap(client)  # receipt with no reference
    client.post(
        "/api/inventory/movements/issue",
        {"item_sku": "WIDGET", "warehouse_code": "MAIN", "quantity": "2", "reference": "SO-TEST-1"},
        format="json",
    )
    res = client.get("/api/inventory/movements?reference=SO-TEST-1")
    assert res.status_code == 200, res.data
    rows = res.data["data"]
    assert len(rows) == 1
    assert rows[0]["reference"] == "SO-TEST-1"
    assert rows[0]["type"] == "issue"


def test_item_detail_unknown_sku_is_404():
    make_gl()
    client = _admin_client()
    assert client.get("/api/inventory/items/NOPE").status_code == 404


def test_item_detail_requires_authentication():
    assert APIClient().get("/api/inventory/items/WIDGET").status_code == 401
