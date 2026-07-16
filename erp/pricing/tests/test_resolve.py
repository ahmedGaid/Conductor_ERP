"""Price resolution precedence, effective dating, quantity breaks, currency, tax-inclusive flag."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from erp.pricing.domain.models import (
    CustomerItemPrice,
    CustomerPriceList,
    PriceList,
    PriceListLine,
)
from erp.pricing.services.management import set_single_default
from erp.pricing.services.resolve import resolve_unit_price

pytestmark = pytest.mark.django_db

ON = date(2026, 6, 27)


def _default_list(**kw):
    return PriceList.objects.create(code="BASE", name="Base", is_default=True, **kw)


def test_returns_none_when_nothing_applies():
    assert resolve_unit_price("ACME", "WIDGET", on=ON) is None


def test_default_list_is_the_fallback():
    base = _default_list()
    PriceListLine.objects.create(price_list=base, item_sku="WIDGET", unit_price_minor=100_00)
    res = resolve_unit_price("ACME", "WIDGET", on=ON)
    assert res is not None
    assert res.unit_price_minor == 100_00
    assert res.source == "default_list"
    assert res.price_list_code == "BASE"


def test_customer_list_beats_default():
    base = _default_list()
    PriceListLine.objects.create(price_list=base, item_sku="WIDGET", unit_price_minor=100_00)
    wholesale = PriceList.objects.create(code="WHOLESALE", name="Wholesale")
    PriceListLine.objects.create(price_list=wholesale, item_sku="WIDGET", unit_price_minor=80_00)
    CustomerPriceList.objects.create(customer_code="ACME", price_list=wholesale)

    res = resolve_unit_price("ACME", "WIDGET", on=ON)
    assert res.unit_price_minor == 80_00
    assert res.source == "customer_list"
    # A different customer still gets the default.
    assert resolve_unit_price("NILE", "WIDGET", on=ON).unit_price_minor == 100_00


def test_customer_item_override_beats_everything():
    base = _default_list()
    PriceListLine.objects.create(price_list=base, item_sku="WIDGET", unit_price_minor=100_00)
    CustomerItemPrice.objects.create(customer_code="ACME", item_sku="WIDGET", unit_price_minor=55_00)
    res = resolve_unit_price("ACME", "WIDGET", on=ON)
    assert res.unit_price_minor == 55_00
    assert res.source == "customer_item"


def test_expired_line_is_ignored():
    base = _default_list()
    PriceListLine.objects.create(
        price_list=base, item_sku="WIDGET", unit_price_minor=100_00,
        valid_from=date(2026, 1, 1), valid_to=date(2026, 6, 1),
    )
    assert resolve_unit_price("ACME", "WIDGET", on=ON) is None  # window closed before ON


def test_future_dated_line_wins_once_effective():
    base = _default_list()
    PriceListLine.objects.create(price_list=base, item_sku="WIDGET", unit_price_minor=100_00)
    PriceListLine.objects.create(
        price_list=base, item_sku="WIDGET", unit_price_minor=120_00, valid_from=date(2026, 6, 1)
    )
    # Latest effective valid_from wins on a tie of qty-break.
    res = resolve_unit_price("ACME", "WIDGET", on=ON)
    assert res.unit_price_minor == 120_00


def test_quantity_break_picks_the_highest_reachable_tier():
    base = _default_list()
    PriceListLine.objects.create(price_list=base, item_sku="WIDGET", unit_price_minor=100_00, min_quantity=0)
    PriceListLine.objects.create(price_list=base, item_sku="WIDGET", unit_price_minor=90_00, min_quantity=10)
    PriceListLine.objects.create(price_list=base, item_sku="WIDGET", unit_price_minor=80_00, min_quantity=50)

    assert resolve_unit_price("ACME", "WIDGET", on=ON, quantity=Decimal(1)).unit_price_minor == 100_00
    assert resolve_unit_price("ACME", "WIDGET", on=ON, quantity=Decimal(10)).unit_price_minor == 90_00
    assert resolve_unit_price("ACME", "WIDGET", on=ON, quantity=Decimal(100)).unit_price_minor == 80_00


def test_currency_mismatch_skips_the_list():
    base = _default_list(currency="USD")
    PriceListLine.objects.create(price_list=base, item_sku="WIDGET", unit_price_minor=100_00)
    assert resolve_unit_price("ACME", "WIDGET", on=ON, currency="EGP") is None
    assert resolve_unit_price("ACME", "WIDGET", on=ON, currency="USD").unit_price_minor == 100_00


def test_tax_inclusive_flag_propagates():
    base = _default_list(tax_inclusive=True)
    PriceListLine.objects.create(price_list=base, item_sku="WIDGET", unit_price_minor=114_00)
    res = resolve_unit_price("ACME", "WIDGET", on=ON)
    assert res.tax_inclusive is True


def test_set_single_default_demotes_other_defaults():
    """Regression (Phase 1c): two lists both is_default=True made the resolver's default tier
    ambiguous (.first() picked one arbitrarily), so items only on the *other* default resolved to
    None. set_single_default must leave exactly one default. A raw save() (the old seed bug) did not.
    """
    retail = PriceList.objects.create(code="RETAIL", name="Retail", is_default=True)
    PriceListLine.objects.create(price_list=retail, item_sku="WIDGET", unit_price_minor=100_00)
    standard = PriceList.objects.create(code="STANDARD", name="Standard", is_default=True)
    PriceListLine.objects.create(price_list=standard, item_sku="GADGET", unit_price_minor=300_00)

    # Before: GADGET lives only on STANDARD; with two defaults it may be unreachable.
    set_single_default(standard)

    assert list(PriceList.objects.filter(is_default=True).values_list("code", flat=True)) == ["STANDARD"]
    # GADGET (STANDARD-only) now resolves deterministically via the single default.
    res = resolve_unit_price("ACME", "GADGET", on=ON)
    assert res is not None and res.price_list_code == "STANDARD" and res.unit_price_minor == 300_00
