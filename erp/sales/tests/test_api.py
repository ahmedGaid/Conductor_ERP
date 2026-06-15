"""Sales DRF API — order flow endpoints, RBAC, auth."""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from erp.identity.models import User

from .factories import make_books, make_item, make_warehouse, stocked

pytestmark = pytest.mark.django_db


def _admin_client() -> APIClient:
    user = User.objects.create_user(username="sales_admin", password="Dev12345!")
    user.is_superuser = True
    user.save(update_fields=["is_superuser"])
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _setup_books_and_stock():
    make_books()
    item = make_item()
    wh = make_warehouse()
    stocked(item, wh)


def test_order_flow_via_api():
    _setup_books_and_stock()
    client = _admin_client()
    assert client.post("/api/sales/customers", {"code": "CUST1", "name": "Acme"}, format="json").status_code == 201

    created = client.post(
        "/api/sales/orders",
        {
            "customer_code": "CUST1", "warehouse_code": "MAIN", "date": "2026-06-15",
            "lines": [{"item_sku": "WIDGET", "quantity": "10", "unit_price": 150_00}],
        },
        format="json",
    )
    assert created.status_code == 201, created.data
    order_id = created.data["data"]["id"]
    assert created.data["data"]["subtotal_minor"] == 1500_00

    assert client.post(f"/api/sales/orders/{order_id}/confirm").data["data"]["status"] == "confirmed"
    assert client.post(f"/api/sales/orders/{order_id}/deliver").data["data"]["status"] == "delivered"
    inv = client.post(f"/api/sales/orders/{order_id}/invoice").data["data"]
    assert inv["status"] == "invoiced" and inv["invoice_number"]

    paid = client.post(f"/api/sales/orders/{order_id}/payment", {"amount": 1500_00}, format="json").data["data"]
    assert paid["status"] == "paid"
    assert paid["outstanding_minor"] == 0


def test_credit_limit_via_api():
    _setup_books_and_stock()
    client = _admin_client()
    client.post("/api/sales/customers", {"code": "C2", "name": "Tight", "credit_limit_minor": 1000_00}, format="json")
    created = client.post(
        "/api/sales/orders",
        {"customer_code": "C2", "warehouse_code": "MAIN",
         "lines": [{"item_sku": "WIDGET", "quantity": "10", "unit_price": 150_00}]},
        format="json",
    )
    order_id = created.data["data"]["id"]
    res = client.post(f"/api/sales/orders/{order_id}/confirm")
    assert res.status_code == 422
    assert res.data["error"]["code"] == "SAL-002"


def test_sales_requires_role():
    plain = User.objects.create_user(username="nobody_sales", password="Dev12345!")
    client = APIClient()
    client.force_authenticate(user=plain)
    assert client.get("/api/sales/orders").status_code == 403


def test_requires_authentication():
    assert APIClient().get("/api/sales/orders").status_code == 401
