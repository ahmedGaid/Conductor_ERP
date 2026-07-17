"""Custom field defs (twenty-harvest FILE_11): admin-only CRUD, active-only listing, the
validation rules a business module (sales/inventory) delegates to on write."""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from erp.core.custom_fields import (
    CustomFieldDef,
    create_custom_field_def,
    deactivate_custom_field_def,
    update_custom_field_def,
    validate_custom_data,
)
from erp.core.errors import ValidationError as AppValidationError
from erp.identity.models import User

pytestmark = pytest.mark.django_db


def _admin_client() -> APIClient:
    user = User.objects.create_user(username="cf_admin", password="Dev12345!")
    user.is_superuser = True
    user.save(update_fields=["is_superuser"])
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _plain_client() -> APIClient:
    user = User.objects.create_user(username="cf_plain", password="Dev12345!")
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def test_create_requires_both_labels():
    with pytest.raises(AppValidationError):
        create_custom_field_def(
            entity_key="sales.customer", key="zone", label_ar="", label_en="Delivery zone", type="TEXT",
        )


def test_deactivate_hides_from_active_but_never_hard_deletes():
    d = create_custom_field_def(
        entity_key="sales.customer", key="zone", label_ar="منطقة", label_en="Zone", type="TEXT",
    )
    deactivate_custom_field_def(d.pk)
    d.refresh_from_db()
    assert d.is_active is False
    assert CustomFieldDef.objects.filter(pk=d.pk).exists()


def test_update_ignores_key_and_entity_key():
    d = create_custom_field_def(
        entity_key="sales.customer", key="zone", label_ar="منطقة", label_en="Zone", type="TEXT",
    )
    updated = update_custom_field_def(
        d.pk, key="renamed", entity_key="inventory.item", label_en="Zone 2",
    )
    assert updated.key == "zone"
    assert updated.entity_key == "sales.customer"
    assert updated.label_en == "Zone 2"


def test_api_write_endpoints_are_admin_only():
    plain = _plain_client()
    payload = {
        "entity_key": "sales.customer", "key": "zone", "label_ar": "منطقة", "label_en": "Zone",
        "type": "TEXT",
    }
    assert plain.post("/api/core/custom-fields", payload, format="json").status_code == 403


def test_api_create_and_active_list_scoped_by_entity():
    admin = _admin_client()
    payload = {
        "entity_key": "sales.customer", "key": "zone", "label_ar": "منطقة", "label_en": "Zone",
        "type": "TEXT",
    }
    created = admin.post("/api/core/custom-fields", payload, format="json")
    assert created.status_code == 201, created.data

    listed = admin.get("/api/core/custom-fields", {"entity": "sales.customer"})
    assert [d["key"] for d in listed.data["data"]] == ["zone"]

    other_entity = admin.get("/api/core/custom-fields", {"entity": "inventory.item"})
    assert other_entity.data["data"] == []


def test_api_deactivate_removes_from_active_list():
    admin = _admin_client()
    payload = {
        "entity_key": "sales.customer", "key": "zone", "label_ar": "منطقة", "label_en": "Zone",
        "type": "TEXT",
    }
    created = admin.post("/api/core/custom-fields", payload, format="json").data["data"]
    admin.post(f"/api/core/custom-fields/{created['id']}/deactivate")
    listed = admin.get("/api/core/custom-fields", {"entity": "sales.customer"})
    assert listed.data["data"] == []


def test_validate_rejects_unknown_key():
    with pytest.raises(AppValidationError) as exc:
        validate_custom_data("sales.customer", {"ghost": "x"})
    assert "ghost" in exc.value.data["errors"]


def test_validate_enforces_required():
    create_custom_field_def(
        entity_key="sales.customer", key="zone", label_ar="منطقة", label_en="Zone", type="TEXT",
        required=True,
    )
    with pytest.raises(AppValidationError):
        validate_custom_data("sales.customer", {})


def test_validate_choice_membership():
    create_custom_field_def(
        entity_key="sales.customer", key="zone", label_ar="منطقة", label_en="Zone", type="CHOICE",
        choices=["cairo", "giza"],
    )
    assert validate_custom_data("sales.customer", {"zone": "cairo"}) == {"zone": "cairo"}
    with pytest.raises(AppValidationError):
        validate_custom_data("sales.customer", {"zone": "alexandria"})


def test_validate_money_kept_integer():
    create_custom_field_def(
        entity_key="sales.customer", key="deposit", label_ar="عربون", label_en="Deposit", type="MONEY",
    )
    cleaned = validate_custom_data("sales.customer", {"deposit": "15000"})
    assert cleaned == {"deposit": 15000}
    assert isinstance(cleaned["deposit"], int)


def test_validate_number_as_decimal_string():
    create_custom_field_def(
        entity_key="sales.customer", key="weight", label_ar="الوزن", label_en="Weight", type="NUMBER",
    )
    assert validate_custom_data("sales.customer", {"weight": "3.50"}) == {"weight": "3.50"}


def test_validate_date_must_be_iso():
    create_custom_field_def(
        entity_key="sales.customer", key="renewal", label_ar="التجديد", label_en="Renewal", type="DATE",
    )
    assert validate_custom_data("sales.customer", {"renewal": "2026-08-01"}) == {"renewal": "2026-08-01"}
    with pytest.raises(AppValidationError):
        validate_custom_data("sales.customer", {"renewal": "not-a-date"})


def test_deactivated_def_keeps_old_values_readable_but_rejects_new_writes():
    from erp.sales.domain.models import Customer

    d = create_custom_field_def(
        entity_key="sales.customer", key="zone", label_ar="منطقة", label_en="Zone", type="TEXT",
    )
    cleaned = validate_custom_data("sales.customer", {"zone": "cairo"})
    customer = Customer.objects.create(code="C-1", name="Acme", custom_data=cleaned)

    deactivate_custom_field_def(d.pk)

    customer.refresh_from_db()
    assert customer.custom_data == {"zone": "cairo"}  # reading never re-validates

    with pytest.raises(AppValidationError):  # a new write naming the inactive key is rejected
        validate_custom_data("sales.customer", {"zone": "giza"})
