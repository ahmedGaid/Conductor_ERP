"""Price-list-line CSV import — engine + API endpoint tests."""
from __future__ import annotations

import io

import pytest
from rest_framework.test import APIClient

from erp.identity.models import User

from ..domain.models import PriceList, PriceListLine
from ..imports import make_price_list_line_import
from erp.core.imports import run_import, auto_map, read_table

pytestmark = pytest.mark.django_db


def _admin_client() -> APIClient:
    user = User.objects.create_user(username="import_admin", password="Dev12345!")
    user.is_superuser = True
    user.save(update_fields=["is_superuser"])
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _make_list(code="TEST") -> PriceList:
    return PriceList.objects.create(code=code, name=code, currency="EGP")


def _csv(rows: list[str]) -> bytes:
    header = "item_sku,unit_price,min_quantity,uom"
    return ("\n".join([header] + rows)).encode("utf-8")


# ── Engine unit tests ──────────────────────────────────────────────────────────

def test_import_creates_lines():
    pl = _make_list()
    spec = make_price_list_line_import(pl)
    raw = _csv(["WIDGET,100.00,0,unit", "GADGET,200.00,0,unit"])
    headers, rows = read_table(raw)
    mapping = auto_map(headers, spec)
    result = run_import(spec, headers, rows, mapping, dry_run=False)
    assert result.summary["created"] == 2
    assert PriceListLine.objects.filter(price_list=pl).count() == 2


def test_qty_break_rows_are_both_created():
    pl = _make_list("BREAKS")
    spec = make_price_list_line_import(pl)
    raw = _csv(["WIDGET,100.00,0,unit", "WIDGET,90.00,10,unit"])
    headers, rows = read_table(raw)
    mapping = auto_map(headers, spec)
    result = run_import(spec, headers, rows, mapping, dry_run=False)
    assert result.summary["created"] == 2
    assert result.summary["failed"] == 0


def test_same_sku_same_qty_is_duplicate():
    pl = _make_list("DUPE")
    spec = make_price_list_line_import(pl)
    raw = _csv(["WIDGET,100.00,0,unit", "WIDGET,90.00,0,unit"])
    headers, rows = read_table(raw)
    mapping = auto_map(headers, spec)
    result = run_import(spec, headers, rows, mapping, dry_run=False)
    assert result.summary["created"] == 1
    assert result.summary["failed"] == 1


def test_dry_run_does_not_persist():
    pl = _make_list("DRY")
    spec = make_price_list_line_import(pl)
    raw = _csv(["WIDGET,100.00,0,unit"])
    headers, rows = read_table(raw)
    mapping = auto_map(headers, spec)
    run_import(spec, headers, rows, mapping, dry_run=True)
    assert PriceListLine.objects.filter(price_list=pl).count() == 0


# ── API endpoint tests ─────────────────────────────────────────────────────────

def test_api_import_preview():
    pl = _make_list("API-DRY")
    client = _admin_client()
    csv_bytes = _csv(["WIDGET,150.00,0,unit"])
    res = client.post(
        f"/api/pricing/price-lists/{pl.id}/lines/import",
        {"file": io.BytesIO(csv_bytes), "commit": "false"},
        format="multipart",
    )
    assert res.status_code == 200
    data = res.data["data"]
    assert data["summary"]["created"] == 1
    assert data["committed"] is False
    assert PriceListLine.objects.filter(price_list=pl).count() == 0


def test_api_import_commit():
    pl = _make_list("API-COMMIT")
    client = _admin_client()
    csv_bytes = _csv(["WIDGET,150.00,0,unit", "GADGET,300.00,0,unit"])
    res = client.post(
        f"/api/pricing/price-lists/{pl.id}/lines/import",
        {"file": io.BytesIO(csv_bytes), "commit": "true"},
        format="multipart",
    )
    assert res.status_code == 200
    assert res.data["data"]["summary"]["created"] == 2
    assert PriceListLine.objects.filter(price_list=pl).count() == 2


def test_api_template_download():
    pl = _make_list("TMPL")
    client = _admin_client()
    res = client.get(f"/api/pricing/price-lists/{pl.id}/lines/import/template")
    assert res.status_code == 200
    assert "item_sku" in res.content.decode("utf-8-sig")
