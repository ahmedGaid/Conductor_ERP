"""Sales DRF API — order flow endpoints, RBAC, auth."""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from erp.identity.models import User

from .factories import make_books, make_item, make_vat, make_warehouse, stocked

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


def test_partial_deliver_and_return_via_api():
    _setup_books_and_stock()
    client = _admin_client()
    client.post("/api/sales/customers", {"code": "CUST1", "name": "Acme"}, format="json")
    created = client.post(
        "/api/sales/orders",
        {"customer_code": "CUST1", "warehouse_code": "MAIN",
         "lines": [{"item_sku": "WIDGET", "quantity": "10", "unit_price": 150_00}]},
        format="json",
    )
    order_id = created.data["data"]["id"]
    client.post(f"/api/sales/orders/{order_id}/confirm")

    partial = client.post(
        f"/api/sales/orders/{order_id}/deliver",
        {"lines": [{"line_no": 1, "quantity": "4"}]}, format="json",
    ).data["data"]
    assert partial["status"] == "partially_delivered"
    assert partial["lines"][0]["delivered_qty"] == "4.0000"

    full = client.post(f"/api/sales/orders/{order_id}/deliver").data["data"]
    assert full["status"] == "delivered"

    client.post(f"/api/sales/orders/{order_id}/invoice")
    returned = client.post(
        f"/api/sales/orders/{order_id}/return",
        {"lines": [{"line_no": 1, "quantity": "3"}]}, format="json",
    ).data["data"]
    assert returned["returned_minor"] == 450_00  # 3 @ 150.00
    assert returned["credit_note_number"]
    assert returned["outstanding_minor"] == 1050_00


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


def test_vat_order_via_api():
    _setup_books_and_stock()
    make_vat()
    client = _admin_client()
    client.post("/api/sales/customers", {"code": "CUST1", "name": "Acme"}, format="json")
    created = client.post(
        "/api/sales/orders",
        {"customer_code": "CUST1", "warehouse_code": "MAIN", "tax_code": "VAT14",
         "lines": [{"item_sku": "WIDGET", "quantity": "10", "unit_price": 150_00}]},
        format="json",
    )
    assert created.status_code == 201, created.data
    order_id = created.data["data"]["id"]
    assert created.data["data"]["tax_code"] == "VAT14"

    client.post(f"/api/sales/orders/{order_id}/confirm")
    client.post(f"/api/sales/orders/{order_id}/deliver")
    inv = client.post(f"/api/sales/orders/{order_id}/invoice").data["data"]
    assert inv["tax_minor"] == 210_00
    assert inv["invoiced_minor"] == 1710_00

    # Tax-code list + VAT return endpoints are reachable.
    codes = client.get("/api/accounting/tax-codes").data["data"]
    assert any(c["code"] == "VAT14" for c in codes)
    vr = client.get("/api/accounting/reports/vat-return?from=2026-01-01&to=2026-12-31").data["data"]
    assert vr["output_vat"] == 210_00


def test_line_discount_and_approval_via_api():
    _setup_books_and_stock()
    client = _admin_client()
    client.post("/api/sales/customers", {"code": "CUST1", "name": "Acme"}, format="json")

    # Large discounted order: 100 @ 150.00 less 4,000.00 = 11,000.00 (still > 10,000 threshold).
    created = client.post(
        "/api/sales/orders",
        {"customer_code": "CUST1", "warehouse_code": "MAIN",
         "lines": [{"item_sku": "WIDGET", "quantity": "100", "unit_price": 150_00, "discount": 4000_00}]},
        format="json",
    )
    assert created.status_code == 201, created.data
    order_id = created.data["data"]["id"]
    assert created.data["data"]["subtotal_minor"] == 11000_00  # 15,000 - 4,000
    assert created.data["data"]["lines"][0]["discount_minor"] == 4000_00
    assert created.data["data"]["requires_approval"] is True
    assert created.data["data"]["approved"] is False

    # Confirm is blocked until approval.
    blocked = client.post(f"/api/sales/orders/{order_id}/confirm")
    assert blocked.status_code == 422
    assert blocked.data["error"]["code"] == "SAL-009"

    approved = client.post(f"/api/sales/orders/{order_id}/approve").data["data"]
    assert approved["approved"] is True
    assert client.post(f"/api/sales/orders/{order_id}/confirm").data["data"]["status"] == "confirmed"


def test_quotation_approval_and_convert_via_api():
    _setup_books_and_stock()
    client = _admin_client()
    client.post("/api/sales/customers", {"code": "CUST1", "name": "Acme"}, format="json")

    # Large quote (> threshold) → needs approval.
    created = client.post(
        "/api/sales/quotations",
        {"customer_code": "CUST1", "warehouse_code": "MAIN",
         "lines": [{"item_sku": "WIDGET", "quantity": "100", "unit_price": 150_00}]},
        format="json",
    )
    assert created.status_code == 201, created.data
    qid = created.data["data"]["id"]
    assert created.data["data"]["requires_approval"] is True

    submitted = client.post(f"/api/sales/quotations/{qid}/submit").data["data"]
    assert submitted["status"] == "submitted"
    approved = client.post(f"/api/sales/quotations/{qid}/approve").data["data"]
    assert approved["status"] == "approved"

    conv = client.post(f"/api/sales/quotations/{qid}/convert")
    assert conv.status_code == 201, conv.data
    assert conv.data["data"]["order_number"].startswith("SO-")
    # The created order is retrievable and in draft.
    oid = conv.data["data"]["order_id"]
    assert client.get(f"/api/sales/orders/{oid}").data["data"]["status"] == "draft"


def test_small_quotation_auto_approves_via_api():
    _setup_books_and_stock()
    client = _admin_client()
    client.post("/api/sales/customers", {"code": "CUST1", "name": "Acme"}, format="json")
    created = client.post(
        "/api/sales/quotations",
        {"customer_code": "CUST1", "warehouse_code": "MAIN",
         "lines": [{"item_sku": "WIDGET", "quantity": "5", "unit_price": 150_00}]},
        format="json",
    )
    qid = created.data["data"]["id"]
    assert created.data["data"]["requires_approval"] is False
    submitted = client.post(f"/api/sales/quotations/{qid}/submit").data["data"]
    assert submitted["status"] == "approved"  # auto-approved below threshold


def test_sales_requires_role():
    plain = User.objects.create_user(username="nobody_sales", password="Dev12345!")
    client = APIClient()
    client.force_authenticate(user=plain)
    assert client.get("/api/sales/orders").status_code == 403


def test_requires_authentication():
    assert APIClient().get("/api/sales/orders").status_code == 401
