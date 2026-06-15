"""Purchasing DRF API — PO flow endpoints, RBAC, auth."""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from erp.identity.models import User

from .factories import make_books, make_item, make_warehouse

pytestmark = pytest.mark.django_db


def _admin_client() -> APIClient:
    user = User.objects.create_user(username="pur_admin", password="Dev12345!")
    user.is_superuser = True
    user.save(update_fields=["is_superuser"])
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def test_po_flow_via_api():
    make_books()
    make_item()
    make_warehouse()
    client = _admin_client()
    assert client.post("/api/purchasing/suppliers", {"code": "SUP1", "name": "Globex"}, format="json").status_code == 201

    created = client.post(
        "/api/purchasing/orders",
        {"supplier_code": "SUP1", "warehouse_code": "MAIN",
         "lines": [{"item_sku": "WIDGET", "quantity": "10", "unit_cost": 100_00}]},
        format="json",
    )
    assert created.status_code == 201, created.data
    oid = created.data["data"]["id"]

    assert client.post(f"/api/purchasing/orders/{oid}/confirm").data["data"]["status"] == "confirmed"
    assert client.post(f"/api/purchasing/orders/{oid}/receive").data["data"]["status"] == "received"
    billed = client.post(f"/api/purchasing/orders/{oid}/bill").data["data"]
    assert billed["status"] == "billed" and billed["bill_number"]
    paid = client.post(f"/api/purchasing/orders/{oid}/payment", {"amount": 1000_00}, format="json").data["data"]
    assert paid["status"] == "paid"
    assert paid["outstanding_minor"] == 0


def test_purchasing_requires_role():
    plain = User.objects.create_user(username="nobody_pur", password="Dev12345!")
    client = APIClient()
    client.force_authenticate(user=plain)
    assert client.get("/api/purchasing/orders").status_code == 403


def test_requires_authentication():
    assert APIClient().get("/api/purchasing/orders").status_code == 401
