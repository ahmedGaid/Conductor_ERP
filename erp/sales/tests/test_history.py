"""Order lifecycle history + the generic business-key resolver."""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from erp.identity.models import User

from .factories import make_books, make_item, make_warehouse, stocked

pytestmark = pytest.mark.django_db


def _admin_client() -> APIClient:
    user = User.objects.create_user(username="hist_admin", password="Dev12345!")
    user.is_superuser = True
    user.save(update_fields=["is_superuser"])
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _order(client) -> str:
    make_books()
    stocked(make_item(), make_warehouse())
    client.post("/api/sales/customers", {"code": "CUST1", "name": "Acme"}, format="json")
    created = client.post(
        "/api/sales/orders",
        {"customer_code": "CUST1", "warehouse_code": "MAIN",
         "lines": [{"item_sku": "WIDGET", "quantity": "10", "unit_price": 150_00}]},
        format="json",
    )
    return created.data["data"]["id"]


def test_history_records_every_stage_with_snapshot_and_actor():
    client = _admin_client()
    order_id = _order(client)
    client.post(f"/api/sales/orders/{order_id}/confirm")
    client.post(f"/api/sales/orders/{order_id}/deliver")

    history = client.get(f"/api/sales/orders/{order_id}/history")
    assert history.status_code == 200, history.data
    rows = history.data["data"]
    # create → confirm → deliver, oldest first.
    assert [r["stage"] for r in rows] == ["create", "confirm", "deliver"]
    assert all(r["actor_name"] == "hist_admin" for r in rows)
    # Each entry carries a full point-in-time snapshot.
    deliver = rows[-1]
    assert deliver["snapshot"]["status"] == "delivered"
    assert deliver["snapshot"]["lines"][0]["item_sku"] == "WIDGET"
    assert deliver["snapshot"]["lines"][0]["delivered_qty"] == "10.0000"
    # The confirm snapshot predates delivery, so its line shows nothing delivered yet.
    confirm = rows[1]
    assert confirm["snapshot"]["status"] == "confirmed"
    assert confirm["snapshot"]["lines"][0]["delivered_qty"] == "0.0000"


def test_resolve_sales_order_by_number():
    client = _admin_client()
    order_id = _order(client)
    number = client.get(f"/api/sales/orders/{order_id}").data["data"]["number"]

    res = client.get(f"/api/core/resolve?type=sales_order&key={number}")
    assert res.status_code == 200, res.data
    assert res.data["data"]["id"] == order_id


def test_resolve_unknown_type_or_missing_key_is_404():
    client = _admin_client()
    assert client.get("/api/core/resolve?type=nope&key=x").status_code == 404
    assert client.get("/api/core/resolve?type=sales_order&key=SO-NOPE").status_code == 404


def test_history_requires_authentication():
    assert APIClient().get("/api/sales/orders/00000000-0000-0000-0000-000000000000/history").status_code == 401
