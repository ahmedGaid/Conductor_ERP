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


def test_partial_receive_and_return_via_api():
    make_books()
    make_item()
    make_warehouse()
    client = _admin_client()
    client.post("/api/purchasing/suppliers", {"code": "SUP1", "name": "Globex"}, format="json")
    created = client.post(
        "/api/purchasing/orders",
        {"supplier_code": "SUP1", "warehouse_code": "MAIN",
         "lines": [{"item_sku": "WIDGET", "quantity": "10", "unit_cost": 100_00}]},
        format="json",
    )
    oid = created.data["data"]["id"]
    client.post(f"/api/purchasing/orders/{oid}/confirm")

    partial = client.post(
        f"/api/purchasing/orders/{oid}/receive",
        {"lines": [{"line_no": 1, "quantity": "6"}]}, format="json",
    ).data["data"]
    assert partial["status"] == "partially_received"
    assert partial["lines"][0]["received_qty"] == "6.0000"

    full = client.post(f"/api/purchasing/orders/{oid}/receive").data["data"]
    assert full["status"] == "received"
    client.post(f"/api/purchasing/orders/{oid}/bill")

    returned = client.post(
        f"/api/purchasing/orders/{oid}/return",
        {"lines": [{"line_no": 1, "quantity": "4"}]}, format="json",
    ).data["data"]
    assert returned["returned_minor"] == 400_00  # 4 @ 100.00
    assert returned["debit_note_number"]
    assert returned["outstanding_minor"] == 600_00


def test_po_approval_gate_via_api():
    make_books()
    make_item()
    make_warehouse()
    client = _admin_client()
    client.post("/api/purchasing/suppliers", {"code": "SUP1", "name": "Globex"}, format="json")
    created = client.post(
        "/api/purchasing/orders",
        {"supplier_code": "SUP1", "warehouse_code": "MAIN",
         "lines": [{"item_sku": "WIDGET", "quantity": "200", "unit_cost": 100_00}]},  # 20,000 > threshold
        format="json",
    )
    oid = created.data["data"]["id"]
    assert created.data["data"]["requires_approval"] is True
    blocked = client.post(f"/api/purchasing/orders/{oid}/confirm")
    assert blocked.status_code == 422
    assert blocked.data["error"]["code"] == "PUR-009"
    assert client.post(f"/api/purchasing/orders/{oid}/approve").data["data"]["approved"] is True
    assert client.post(f"/api/purchasing/orders/{oid}/confirm").data["data"]["status"] == "confirmed"


def test_request_approval_and_convert_via_api():
    make_books()
    make_item()
    make_warehouse()
    client = _admin_client()
    client.post("/api/purchasing/suppliers", {"code": "SUP1", "name": "Globex"}, format="json")

    created = client.post(
        "/api/purchasing/requests",
        {"supplier_code": "SUP1", "warehouse_code": "MAIN",
         "lines": [{"item_sku": "WIDGET", "quantity": "200", "unit_cost": 100_00}]},
        format="json",
    )
    assert created.status_code == 201, created.data
    rid = created.data["data"]["id"]
    assert created.data["data"]["requires_approval"] is True

    assert client.post(f"/api/purchasing/requests/{rid}/submit").data["data"]["status"] == "submitted"
    assert client.post(f"/api/purchasing/requests/{rid}/approve").data["data"]["status"] == "approved"

    conv = client.post(f"/api/purchasing/requests/{rid}/convert")
    assert conv.status_code == 201, conv.data
    assert conv.data["data"]["order_number"].startswith("PO-")
    oid = conv.data["data"]["order_id"]
    assert client.get(f"/api/purchasing/orders/{oid}").data["data"]["status"] == "draft"


def test_purchasing_requires_role():
    plain = User.objects.create_user(username="nobody_pur", password="Dev12345!")
    client = APIClient()
    client.force_authenticate(user=plain)
    assert client.get("/api/purchasing/orders").status_code == 403


def test_requires_authentication():
    assert APIClient().get("/api/purchasing/orders").status_code == 401
