"""Customer CSV import — the friction decisions (DECISIONS.md Phase 2.0) proven end to end.

Covers: Arabic-from-Excel encodings (cp1256 / UTF-8 BOM), in-file + in-db duplicates, partial
success, idempotent re-upload, preview==commit, money major→minor, and the template download.
"""
from __future__ import annotations

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from erp.identity.models import User
from erp.sales.domain.models import Customer

pytestmark = pytest.mark.django_db

IMPORT_URL = "/api/sales/customers/import"
TEMPLATE_URL = "/api/sales/customers/import/template"


def _client() -> APIClient:
    user = User.objects.create_user(username="imp_admin", password="Dev12345!")
    user.is_superuser = True
    user.save(update_fields=["is_superuser"])
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _upload(raw: bytes, name: str = "customers.csv") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, raw, content_type="text/csv")


def _post(client: APIClient, raw: bytes, **fields):
    data = {"file": _upload(raw), **fields}
    return client.post(IMPORT_URL, data, format="multipart")


def test_preview_does_not_write_then_commit_creates():
    client = _client()
    csv = "code,name,credit_limit\nC-1,Nile Trading,50000\nC-2,Delta Co,0\n".encode("utf-8")

    preview = _post(client, csv)  # commit defaults to false
    assert preview.status_code == 200
    body = preview.json()["data"]
    assert body["committed"] is False
    assert body["summary"] == {"total": 2, "created": 2, "updated": 0, "skipped": 0, "failed": 0}
    assert Customer.objects.count() == 0  # preview wrote nothing

    commit = _post(client, csv, commit="true")
    assert commit.json()["data"]["summary"]["created"] == 2
    assert Customer.objects.count() == 2
    nile = Customer.objects.get(code="C-1")
    assert nile.name == "Nile Trading"
    assert nile.credit_limit_minor == 5_000_000  # 50000 major -> minor at the edge


def test_money_major_units_become_minor():
    client = _client()
    csv = "code,name,credit_limit\nC-9,Acme,\"1,000.50\"\n".encode("utf-8")
    _post(client, csv, commit="true")
    assert Customer.objects.get(code="C-9").credit_limit_minor == 100_050


def test_cp1256_arabic_and_utf8_bom_decode():
    client = _client()
    # Arabic name written by Arabic Excel "Save As CSV" = Windows-1256, no BOM.
    arabic = "شركة النيل"
    cp1256 = ("code,name\nC-AR," + arabic + "\n").encode("cp1256")
    assert _post(client, cp1256, commit="true").status_code == 200
    assert Customer.objects.get(code="C-AR").name == arabic

    # "CSV UTF-8" prepends a BOM; the first header must still be "code", not "﻿code".
    bom = ("code,name\nC-BOM,Beta\n").encode("utf-8-sig")
    body = _post(client, bom, commit="true").json()["data"]
    assert body["summary"]["created"] == 1
    assert Customer.objects.filter(code="C-BOM").exists()


def test_duplicate_within_file_first_wins_rest_fail():
    client = _client()
    csv = "code,name\nC-1,First\nC-1,Second\n".encode("utf-8")
    body = _post(client, csv, commit="true").json()["data"]
    assert body["summary"]["created"] == 1
    assert body["summary"]["failed"] == 1
    assert Customer.objects.get(code="C-1").name == "First"
    failed = [r for r in body["rows"] if r["outcome"] == "failed"][0]
    assert "duplicate" in failed["errors"][0]["message"].lower()


def test_existing_skipped_in_create_mode_updated_in_upsert():
    client = _client()
    Customer.objects.create(code="C-1", name="Old Name")

    skip = _post(client, "code,name\nC-1,New Name\n".encode("utf-8"), commit="true").json()["data"]
    assert skip["summary"]["skipped"] == 1
    assert Customer.objects.get(code="C-1").name == "Old Name"  # untouched

    up = _post(
        client, "code,name\nC-1,New Name\n".encode("utf-8"), commit="true", mode="upsert"
    ).json()["data"]
    assert up["summary"]["updated"] == 1
    assert Customer.objects.get(code="C-1").name == "New Name"


def test_partial_success_good_rows_commit_bad_row_reported():
    client = _client()
    csv = "code,name\nC-1,Good\nC-2,\nC-3,Also Good\n".encode("utf-8")  # row 3 missing name
    body = _post(client, csv, commit="true").json()["data"]
    assert body["summary"] == {"total": 3, "created": 2, "updated": 0, "skipped": 0, "failed": 1}
    assert Customer.objects.count() == 2
    failed = [r for r in body["rows"] if r["outcome"] == "failed"][0]
    assert failed["row"] == 3
    assert failed["errors"][0]["field"] == "name"


def test_reupload_is_idempotent():
    client = _client()
    csv = "code,name\nC-1,One\nC-2,Two\n".encode("utf-8")
    _post(client, csv, commit="true")
    second = _post(client, csv, commit="true").json()["data"]
    assert second["summary"]["created"] == 0
    assert second["summary"]["skipped"] == 2
    assert Customer.objects.count() == 2  # no duplicates created


def test_over_length_code_is_a_row_error():
    client = _client()
    long_code = "C-" + "X" * 40  # > 32 chars
    body = _post(client, f"code,name\n{long_code},Acme\n".encode("utf-8"), commit="true").json()["data"]
    assert body["summary"]["failed"] == 1
    assert Customer.objects.count() == 0


def test_missing_file_is_a_clean_400():
    client = _client()
    resp = client.post(IMPORT_URL, {"commit": "true"}, format="multipart")
    assert resp.status_code == 400
    assert "error" in resp.json()


def test_template_download():
    client = _client()
    resp = client.get(TEMPLATE_URL)
    assert resp.status_code == 200
    assert resp["Content-Type"].startswith("text/csv")
    text = resp.content.decode("utf-8-sig")
    assert text.splitlines()[0].split(",")[:2] == ["code", "name"]
