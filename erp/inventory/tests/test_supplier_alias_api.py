"""Supplier-item alias management API — list, filter, re-point, delete, RBAC.

These aliases are the import learning loop's memory (see ``inventory.contracts.record_alias``); this
screen lets a human see what was learned and correct a mis-learned mapping.
"""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from erp.identity.models import User
from erp.inventory import contracts as inventory
from erp.inventory.domain.models import Item, SupplierItemAlias

pytestmark = pytest.mark.django_db


def _admin_client() -> APIClient:
    user = User.objects.create_user(username="alias_admin", password="Dev12345!")
    user.is_superuser = True
    user.save(update_fields=["is_superuser"])
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _seed_items():
    bearing = Item.objects.create(sku="B-6205", name="Bearing 6205 ZZ")
    belt = Item.objects.create(sku="V-BELT", name="V-belt A-42")
    return bearing, belt


def test_list_returns_learned_aliases():
    client = _admin_client()
    bearing, _ = _seed_items()
    inventory.record_alias(supplier_code="ACME", item_sku="B-6205", supplier_item_code="7788",
                           supplier_item_name="رولمان بلي 6205")

    res = client.get("/api/inventory/supplier-aliases")
    assert res.status_code == 200, res.data
    rows = res.data["data"]
    assert len(rows) == 1
    row = rows[0]
    assert row["supplier_code"] == "ACME"
    assert row["supplier_item_code"] == "7788"
    assert row["supplier_item_name"] == "رولمان بلي 6205"
    assert row["item_sku"] == "B-6205"
    assert row["item_name"] == bearing.name
    assert row["source"] == "confirmed"


def test_list_filters_by_supplier_and_item():
    client = _admin_client()
    _seed_items()
    inventory.record_alias(supplier_code="ACME", item_sku="B-6205", supplier_item_code="7788")
    inventory.record_alias(supplier_code="GLOBEX", item_sku="V-BELT", supplier_item_code="X1")

    by_supplier = client.get("/api/inventory/supplier-aliases?supplier_code=ACME").data["data"]
    assert [r["supplier_code"] for r in by_supplier] == ["ACME"]

    by_item = client.get("/api/inventory/supplier-aliases?item_sku=V-BELT").data["data"]
    assert [r["item_sku"] for r in by_item] == ["V-BELT"]


def test_repoint_moves_alias_to_correct_item():
    client = _admin_client()
    _seed_items()
    inventory.record_alias(supplier_code="ACME", item_sku="B-6205", supplier_item_code="7788")
    alias = SupplierItemAlias.objects.get(supplier_code="ACME", supplier_item_code="7788")

    res = client.patch(
        f"/api/inventory/supplier-aliases/{alias.id}", {"item_sku": "V-BELT"}, format="json"
    )
    assert res.status_code == 200, res.data
    assert res.data["data"]["item_sku"] == "V-BELT"

    alias.refresh_from_db()
    assert alias.item.sku == "V-BELT"
    assert alias.source == SupplierItemAlias.Source.MANUAL


def test_repoint_rejects_unknown_item():
    client = _admin_client()
    _seed_items()
    inventory.record_alias(supplier_code="ACME", item_sku="B-6205", supplier_item_code="7788")
    alias = SupplierItemAlias.objects.get(supplier_code="ACME", supplier_item_code="7788")

    res = client.patch(
        f"/api/inventory/supplier-aliases/{alias.id}", {"item_sku": "NOPE"}, format="json"
    )
    assert res.status_code == 400
    alias.refresh_from_db()
    assert alias.item.sku == "B-6205"  # unchanged


def test_delete_forgets_alias():
    client = _admin_client()
    _seed_items()
    inventory.record_alias(supplier_code="ACME", item_sku="B-6205", supplier_item_code="7788")
    alias = SupplierItemAlias.objects.get(supplier_code="ACME", supplier_item_code="7788")

    res = client.delete(f"/api/inventory/supplier-aliases/{alias.id}")
    assert res.status_code == 204
    assert not SupplierItemAlias.objects.filter(id=alias.id).exists()


def test_alias_management_requires_role():
    plain = User.objects.create_user(username="nobody_alias", password="Dev12345!")
    client = APIClient()
    client.force_authenticate(user=plain)
    assert client.get("/api/inventory/supplier-aliases").status_code == 403
