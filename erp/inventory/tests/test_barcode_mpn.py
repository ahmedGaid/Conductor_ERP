"""Slice B: barcode + mpn identity fields and their resolve_item tiers.

Extends slice A (``test_item_resolution.py``) — here the incoming supplier ``code`` is a world
identity key (GTIN/EAN/UPC or manufacturer part number) rather than our SKU or a learned alias.
"""
from __future__ import annotations

import pytest
from django.db import IntegrityError, transaction

from erp.inventory import contracts as inventory
from erp.inventory.domain.models import Item

from .factories import make_item

pytestmark = pytest.mark.django_db


def test_barcode_resolves_with_confidence_100():
    make_item(sku="COLA-24", name="Cola 330ml x24", barcode="6221000000024")
    res = inventory.resolve_item(code="6221000000024")
    assert res.item is not None
    assert (res.item.sku, res.method, res.confidence) == ("COLA-24", "barcode", 100)


def test_mpn_resolves_with_confidence_100():
    make_item(sku="BRG-6205", name="Bearing 6205 ZZ", mpn="6205-2Z")
    res = inventory.resolve_item(code="6205-2Z")
    assert res.item is not None
    assert (res.item.sku, res.method, res.confidence) == ("BRG-6205", "mpn", 100)


def test_sku_still_outranks_barcode_and_mpn():
    # An item whose SKU happens to equal another item's barcode: the exact-SKU tier wins.
    make_item(sku="SHARED", name="By SKU")
    make_item(sku="OTHER", name="By Barcode", barcode="SHARED")
    res = inventory.resolve_item(code="SHARED")
    assert res.item.sku == "SHARED" and res.method == "sku"


def test_blank_code_never_matches_blank_barcode_or_mpn():
    make_item(sku="PLAIN", name="Plain")  # barcode/mpn default ""
    assert inventory.resolve_item(code="").item is None
    assert inventory.resolve_item(name="").item is None


def test_barcode_beats_a_name_collision():
    # A different item's name equals the barcode string; barcode (100) must win over name (90).
    make_item(sku="REAL", name="Widget", barcode="999")
    make_item(sku="DECOY", name="999")
    res = inventory.resolve_item(code="999", name="999")
    assert res.item.sku == "REAL" and res.method == "barcode"


def test_barcode_uniqueness_enforced_for_nonblank():
    make_item(sku="A", name="A", barcode="123")
    with pytest.raises(IntegrityError):
        with transaction.atomic():  # keep the outer test transaction usable after the violation
            Item.objects.create(sku="B", name="B", barcode="123")
    # Two blank barcodes are fine (blank isn't an identity).
    make_item(sku="C", name="C")
    make_item(sku="D", name="D")


def test_mpn_uniqueness_enforced_for_nonblank():
    make_item(sku="A", name="A", mpn="P-1")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Item.objects.create(sku="B", name="B", mpn="P-1")
