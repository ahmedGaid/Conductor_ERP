"""Custom fields wired into Supplier create (twenty-harvest FILE_12 follow-up — supplier added as
a third entity, mirroring sales.customer / inventory.item): validation on write, integer MONEY."""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from erp.core.custom_fields import create_custom_field_def
from erp.identity.models import User

pytestmark = pytest.mark.django_db


def _admin_client() -> APIClient:
    user = User.objects.create_user(username="supplier_admin", password="Dev12345!")
    user.is_superuser = True
    user.save(update_fields=["is_superuser"])
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def test_create_supplier_with_valid_custom_data():
    create_custom_field_def(
        entity_key="purchasing.supplier", key="lead_time_days", label_ar="مهلة التوريد بالأيام",
        label_en="Lead time (days)", type="NUMBER",
    )
    resp = _admin_client().post(
        "/api/purchasing/suppliers",
        {"code": "SUP-1", "name": "Acme Supplies", "custom_data": {"lead_time_days": "7"}},
        format="json",
    )
    assert resp.status_code == 201, resp.data
    assert resp.data["data"]["custom_data"] == {"lead_time_days": "7"}


def test_create_supplier_with_invalid_custom_data_is_a_human_blame_free_error():
    create_custom_field_def(
        entity_key="purchasing.supplier", key="tier", label_ar="الفئة", label_en="Tier",
        type="CHOICE", choices=["preferred", "backup"],
    )
    resp = _admin_client().post(
        "/api/purchasing/suppliers",
        {"code": "SUP-2", "name": "Acme Supplies", "custom_data": {"tier": "unknown"}},
        format="json",
    )
    assert resp.status_code == 400
    assert "tier" in resp.data["error"]["data"]["errors"]


def test_create_supplier_money_custom_field_kept_integer():
    create_custom_field_def(
        entity_key="purchasing.supplier", key="credit_terms_value", label_ar="قيمة شروط الائتمان",
        label_en="Credit terms value", type="MONEY",
    )
    resp = _admin_client().post(
        "/api/purchasing/suppliers",
        {"code": "SUP-3", "name": "Acme Supplies", "custom_data": {"credit_terms_value": "500000"}},
        format="json",
    )
    assert resp.status_code == 201, resp.data
    assert resp.data["data"]["custom_data"]["credit_terms_value"] == 500000
    assert isinstance(resp.data["data"]["custom_data"]["credit_terms_value"], int)
