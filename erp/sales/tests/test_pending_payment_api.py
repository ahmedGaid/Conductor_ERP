"""Pending-payment review API — list/apply/discard/match. Backend-only; no UI in this plan."""
from __future__ import annotations

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from erp.identity.models import User
from erp.sales.services import OrderLineInput, confirm_order, create_order, deliver_order, invoice_order
from erp.sales.services.pending_payments import create_pending_payment

from .factories import DATE, make_books, make_customer, make_item, make_warehouse, stocked

pytestmark = pytest.mark.django_db


def _admin_client() -> APIClient:
    user = User.objects.create_user(username="pp_admin", password="Dev12345!")
    user.is_superuser = True
    user.save(update_fields=["is_superuser"])
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _invoiced_order():
    make_books()
    item = make_item()
    wh = make_warehouse()
    stocked(item, wh)
    customer = make_customer(code="CUSTX")
    order = create_order(
        customer=customer, warehouse_code=wh.code, order_date=DATE,
        lines=[OrderLineInput(item_sku="WIDGET", quantity=Decimal("10"), unit_price_minor=150_00)],
    )
    confirm_order(order)
    deliver_order(order)
    invoice_order(order)
    return customer, order


def test_list_shows_pending_payments():
    customer, order = _invoiced_order()
    create_pending_payment(order=order, party_code=customer.code, amount_minor=500_00, date=DATE)
    client = _admin_client()

    resp = client.get("/api/sales/pending-payments")

    assert resp.status_code == 200
    assert len(resp.data["data"]) == 1
    assert resp.data["data"][0]["amount_minor"] == 500_00
    assert resp.data["data"][0]["order_number"] == order.number


def test_apply_via_api_posts_the_payment():
    customer, order = _invoiced_order()
    pending = create_pending_payment(order=order, party_code=customer.code, amount_minor=1500_00, date=DATE)
    client = _admin_client()

    resp = client.post(f"/api/sales/pending-payments/{pending.id}/apply")

    assert resp.status_code == 200
    assert resp.data["data"]["status"] == "applied"
    order.refresh_from_db()
    assert order.status == "paid"


def test_discard_via_api():
    customer, order = _invoiced_order()
    pending = create_pending_payment(order=order, party_code=customer.code, amount_minor=500_00, date=DATE)
    client = _admin_client()

    resp = client.post(f"/api/sales/pending-payments/{pending.id}/discard")

    assert resp.status_code == 200
    assert resp.data["data"]["status"] == "discarded"


def test_match_via_api_then_apply():
    customer, order = _invoiced_order()
    pending = create_pending_payment(order=None, party_code=customer.code, amount_minor=1500_00, date=DATE)
    client = _admin_client()

    matched = client.post(f"/api/sales/pending-payments/{pending.id}/match", {"order_id": str(order.id)}, format="json")
    assert matched.status_code == 200
    assert matched.data["data"]["order_number"] == order.number

    applied = client.post(f"/api/sales/pending-payments/{pending.id}/apply")
    assert applied.data["data"]["status"] == "applied"


def test_unauthenticated_is_rejected():
    client = APIClient()
    assert client.get("/api/sales/pending-payments").status_code in (401, 403)
