"""Item CSV import (Growth 2.4) — the engine's FK resolution + choice/decimal fields.

Items are the interesting list: a category_code that matches nothing must be a row error (not the
silent null the single-create path produces), and type is a constrained choice.
"""
from __future__ import annotations

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from erp.identity.models import User
from erp.inventory.domain.models import Category, Item

pytestmark = pytest.mark.django_db

IMPORT_URL = "/api/inventory/items/import"
TEMPLATE_URL = "/api/inventory/items/import/template"


def _client() -> APIClient:
    user = User.objects.create_user(username="inv_admin", password="Dev12345!")
    user.is_superuser = True
    user.save(update_fields=["is_superuser"])
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _post(client: APIClient, raw: bytes, **fields):
    data = {"file": SimpleUploadedFile("items.csv", raw, content_type="text/csv"), **fields}
    return client.post(IMPORT_URL, data, format="multipart")


def test_preview_then_commit_creates_with_defaults():
    client = _client()
    csv = "sku,name\nITM-1,Cement\nITM-2,Sand\n".encode("utf-8")

    preview = _post(client, csv).json()["data"]
    assert preview["summary"]["created"] == 2
    assert Item.objects.count() == 0

    _post(client, csv, commit="true")
    assert Item.objects.count() == 2
    item = Item.objects.get(sku="ITM-1")
    assert item.name == "Cement"
    assert item.uom == "unit"      # serializer default
    assert item.type == "stock"    # serializer default
    assert item.category_id is None


def test_known_category_links_unknown_is_a_row_error():
    client = _client()
    Category.objects.create(code="RAW", name="Raw materials")

    ok = _post(client, "sku,name,category_code\nITM-1,Cement,RAW\n".encode("utf-8"), commit="true")
    assert ok.json()["data"]["summary"]["created"] == 1
    assert Item.objects.get(sku="ITM-1").category.code == "RAW"

    bad = _post(client, "sku,name,category_code\nITM-2,Steel,NOPE\n".encode("utf-8"), commit="true")
    body = bad.json()["data"]
    assert body["summary"]["failed"] == 1
    assert body["rows"][0]["errors"][0]["field"] == "category_code"
    assert not Item.objects.filter(sku="ITM-2").exists()  # not created as a silent null


def test_invalid_type_choice_is_a_row_error():
    client = _client()
    body = _post(client, "sku,name,type\nITM-1,Widget,gadget\n".encode("utf-8"), commit="true").json()["data"]
    assert body["summary"]["failed"] == 1
    assert Item.objects.count() == 0


def test_reorder_point_accepts_arabic_indic_digits():
    client = _client()
    # "١٢" is Arabic-Indic 12; the engine folds digits before the serializer parses.
    _post(client, "sku,name,reorder_point\nITM-9,Bolt,١٢\n".encode("utf-8"), commit="true")
    assert int(Item.objects.get(sku="ITM-9").reorder_point) == 12


def test_partial_success_and_idempotent_reupload():
    client = _client()
    csv = "sku,name\nITM-1,A\nITM-2,\nITM-3,C\n".encode("utf-8")  # row 3 missing name
    first = _post(client, csv, commit="true").json()["data"]
    assert first["summary"] == {"total": 3, "created": 2, "updated": 0, "skipped": 0, "failed": 1}

    second = _post(client, csv, commit="true").json()["data"]
    assert second["summary"]["skipped"] == 2
    assert Item.objects.count() == 2  # idempotent


def test_template_download():
    client = _client()
    resp = client.get(TEMPLATE_URL)
    assert resp.status_code == 200
    headers = resp.content.decode("utf-8-sig").splitlines()[0].split(",")
    assert headers[:2] == ["sku", "name"]
    assert "category_code" in headers
