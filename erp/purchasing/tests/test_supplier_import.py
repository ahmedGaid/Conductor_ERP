"""Supplier CSV import — the generic engine reused for a second list (Growth 2.3)."""
from __future__ import annotations

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from erp.identity.models import User
from erp.purchasing.domain.models import Supplier

pytestmark = pytest.mark.django_db

IMPORT_URL = "/api/purchasing/suppliers/import"
TEMPLATE_URL = "/api/purchasing/suppliers/import/template"


def _client() -> APIClient:
    user = User.objects.create_user(username="sup_admin", password="Dev12345!")
    user.is_superuser = True
    user.save(update_fields=["is_superuser"])
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _post(client: APIClient, raw: bytes, **fields):
    data = {"file": SimpleUploadedFile("suppliers.csv", raw, content_type="text/csv"), **fields}
    return client.post(IMPORT_URL, data, format="multipart")


def test_preview_then_commit_creates():
    client = _client()
    csv = "code,name\nS-1,Delta Mills\nS-2,Cairo Supply\n".encode("utf-8")

    preview = _post(client, csv).json()["data"]
    assert preview["committed"] is False
    assert preview["summary"]["created"] == 2
    assert Supplier.objects.count() == 0

    _post(client, csv, commit="true")
    assert Supplier.objects.count() == 2
    assert Supplier.objects.get(code="S-1").name == "Delta Mills"


def test_cp1256_arabic_decodes():
    client = _client()
    arabic = "مصنع الدلتا"
    raw = ("code,name\nS-AR," + arabic + "\n").encode("cp1256")
    assert _post(client, raw, commit="true").status_code == 200
    assert Supplier.objects.get(code="S-AR").name == arabic


def test_existing_skipped_then_upsert_updates():
    client = _client()
    Supplier.objects.create(code="S-1", name="Old")
    skip = _post(client, "code,name\nS-1,New\n".encode("utf-8"), commit="true").json()["data"]
    assert skip["summary"]["skipped"] == 1
    assert Supplier.objects.get(code="S-1").name == "Old"

    up = _post(client, "code,name\nS-1,New\n".encode("utf-8"), commit="true", mode="upsert").json()["data"]
    assert up["summary"]["updated"] == 1
    assert Supplier.objects.get(code="S-1").name == "New"


def test_partial_success_and_idempotent_reupload():
    client = _client()
    csv = "code,name\nS-1,Good\nS-2,\nS-3,Fine\n".encode("utf-8")  # row 3 missing name
    first = _post(client, csv, commit="true").json()["data"]
    assert first["summary"] == {"total": 3, "created": 2, "updated": 0, "skipped": 0, "failed": 1}
    assert Supplier.objects.count() == 2

    second = _post(client, csv, commit="true").json()["data"]
    assert second["summary"]["created"] == 0
    assert second["summary"]["skipped"] == 2
    assert Supplier.objects.count() == 2  # idempotent


def test_template_download():
    client = _client()
    resp = client.get(TEMPLATE_URL)
    assert resp.status_code == 200
    assert resp.content.decode("utf-8-sig").splitlines()[0].split(",")[:2] == ["code", "name"]
