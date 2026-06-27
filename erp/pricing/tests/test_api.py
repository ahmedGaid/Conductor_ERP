"""Pricing DRF API — price lists, lines, customer assignment, resolve (+ tax back-out), RBAC."""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from erp.accounting.domain.models import TaxCode
from erp.identity.models import User

pytestmark = pytest.mark.django_db


def _admin_client() -> APIClient:
    user = User.objects.create_user(username="price_admin", password="Dev12345!")
    user.is_superuser = True
    user.save(update_fields=["is_superuser"])
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _make_list(client, code="STD", is_default=True, **kw):
    res = client.post(
        "/api/pricing/price-lists",
        {"code": code, "name": kw.get("name", code), "is_default": is_default, **kw},
        format="json",
    )
    assert res.status_code == 201, res.data
    return res.data["data"]


def _add_line(client, list_id, sku="WIDGET", price=100_00, **kw):
    res = client.post(
        f"/api/pricing/price-lists/{list_id}/lines",
        {"item_sku": sku, "unit_price_minor": price, **kw},
        format="json",
    )
    assert res.status_code == 201, res.data
    return res.data["data"]


def test_create_list_and_line_then_resolve_default():
    client = _admin_client()
    pl = _make_list(client)
    _add_line(client, pl["id"])

    listing = client.get("/api/pricing/price-lists").data["data"]
    assert listing[0]["line_count"] == 1

    res = client.get("/api/pricing/resolve?customer=ACME&sku=WIDGET").data["data"]
    assert res["unit_price_minor"] == 100_00
    assert res["source"] == "default_list"


def test_resolve_returns_null_when_no_price():
    client = _admin_client()
    assert client.get("/api/pricing/resolve?customer=ACME&sku=NOPE").data["data"] is None


def test_tax_inclusive_price_is_backed_out_to_net():
    client = _admin_client()
    TaxCode.objects.create(code="V14", name="VAT 14%", rate_bps=1400)
    pl = _make_list(client, tax_inclusive=True)
    _add_line(client, pl["id"], price=114_00)  # gross, VAT-inclusive

    res = client.get("/api/pricing/resolve?customer=ACME&sku=WIDGET&tax_code=V14").data["data"]
    assert res["unit_price_minor"] == 100_00  # net = 11400 * 10000 / 11400
    assert res["tax_inclusive"] is True
    # Without a tax_code the gross is returned untouched.
    gross = client.get("/api/pricing/resolve?customer=ACME&sku=WIDGET").data["data"]
    assert gross["unit_price_minor"] == 114_00


def test_customer_assignment_overrides_default():
    client = _admin_client()
    base = _make_list(client, code="STD")
    _add_line(client, base["id"], price=100_00)
    wholesale = _make_list(client, code="WS", is_default=False)
    _add_line(client, wholesale["id"], price=80_00)

    assign = client.post(
        "/api/pricing/customer-assignments",
        {"customer_code": "ACME", "price_list_code": "WS"},
        format="json",
    )
    assert assign.status_code == 201, assign.data

    acme = client.get("/api/pricing/resolve?customer=ACME&sku=WIDGET").data["data"]
    assert acme["unit_price_minor"] == 80_00
    assert acme["source"] == "customer_list"
    other = client.get("/api/pricing/resolve?customer=NILE&sku=WIDGET").data["data"]
    assert other["unit_price_minor"] == 100_00


def test_setting_a_new_default_clears_the_old_one():
    client = _admin_client()
    first = _make_list(client, code="A")
    second = _make_list(client, code="B", is_default=False)
    client.patch(f"/api/pricing/price-lists/{second['id']}", {"is_default": True}, format="json")

    lists = {pl["code"]: pl for pl in client.get("/api/pricing/price-lists").data["data"]}
    assert lists["B"]["is_default"] is True
    assert lists["A"]["is_default"] is False


def test_management_requires_a_role_but_resolve_only_needs_auth():
    anon = APIClient()
    assert anon.get("/api/pricing/price-lists").status_code in (401, 403)
    assert anon.get("/api/pricing/resolve?customer=ACME&sku=WIDGET").status_code in (401, 403)

    plain = User.objects.create_user(username="plain", password="Dev12345!")
    client = APIClient()
    client.force_authenticate(user=plain)
    # No management role → cannot manage lists…
    assert client.get("/api/pricing/price-lists").status_code == 403
    # …but can resolve (returns null with no data, but is allowed through).
    assert client.get("/api/pricing/resolve?customer=ACME&sku=WIDGET").status_code == 200
