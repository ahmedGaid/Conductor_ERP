"""Pending-payment review API (purchasing) -- mirrors erp/sales/tests/test_pending_payment_api.py."""
from __future__ import annotations

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from erp.identity.models import User
from erp.purchasing.services import POLineInput, bill_order, confirm_order, create_order, receive_order
from erp.purchasing.services.pending_payments import create_pending_payment

from .factories import DATE, make_books, make_item, make_supplier, make_warehouse

pytestmark = pytest.mark.django_db


def _admin_client() -> APIClient:
    user = User.objects.create_user(username="pp_pur_admin", password="Dev12345!")
    user.is_superuser = True
    user.save(update_fields=["is_superuser"])
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _billed_order():
    make_books()
    make_item()
    wh = make_warehouse()
    supplier = make_supplier(code="SUPX")
    order = create_order(
        supplier=supplier, warehouse_code=wh.code, order_date=DATE,
        lines=[POLineInput(item_sku="WIDGET", quantity=Decimal("10"), unit_cost_minor=100_00)],
    )
    confirm_order(order)
    receive_order(order)
    bill_order(order)
    return supplier, order


def test_list_shows_pending_payments():
    supplier, order = _billed_order()
    create_pending_payment(order=order, party_code=supplier.code, amount_minor=400_00, date=DATE)
    client = _admin_client()

    resp = client.get("/api/purchasing/pending-payments")

    assert resp.status_code == 200
    assert len(resp.data["data"]) == 1


def test_apply_via_api_posts_the_payment():
    supplier, order = _billed_order()
    pending = create_pending_payment(order=order, party_code=supplier.code, amount_minor=1000_00, date=DATE)
    client = _admin_client()

    resp = client.post(f"/api/purchasing/pending-payments/{pending.id}/apply")

    assert resp.status_code == 200
    assert resp.data["data"]["status"] == "applied"
    order.refresh_from_db()
    assert order.status == "paid"


def test_discard_via_api():
    supplier, order = _billed_order()
    pending = create_pending_payment(order=order, party_code=supplier.code, amount_minor=400_00, date=DATE)
    client = _admin_client()

    resp = client.post(f"/api/purchasing/pending-payments/{pending.id}/discard")

    assert resp.data["data"]["status"] == "discarded"


def test_match_via_api_then_apply():
    supplier, order = _billed_order()
    pending = create_pending_payment(order=None, party_code=supplier.code, amount_minor=1000_00, date=DATE)
    client = _admin_client()

    matched = client.post(f"/api/purchasing/pending-payments/{pending.id}/match", {"order_id": str(order.id)}, format="json")
    assert matched.status_code == 200

    applied = client.post(f"/api/purchasing/pending-payments/{pending.id}/apply")
    assert applied.data["data"]["status"] == "applied"
