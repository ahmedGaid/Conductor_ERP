"""Item resolution + supplier-item alias — the multi-supplier duplicate-item fix.

The same physical item is bought from several suppliers, each using a different code and name (often
a different language). ``resolve_item`` maps an incoming supplier line to the canonical ``Item`` using
a signal hierarchy — supplier alias first, then exact SKU, then normalized name — so ingestion links
to the RIGHT item instead of creating a duplicate. ``record_alias`` captures a confirmed match so the
next document from that supplier resolves deterministically.
"""
from __future__ import annotations

import pytest

from erp.inventory import contracts
from erp.inventory.domain.models import SupplierItemAlias

from .factories import make_item

pytestmark = pytest.mark.django_db


# --- resolve_item: the signal hierarchy ---------------------------------------------------------
def test_alias_by_supplier_code_resolves_to_canonical_item():
    """Case 1/2/4: supplier B's own code (7788) maps to canonical RM-001, whatever the name says."""
    item = make_item(sku="RM-001", name="Bearing 6205 ZZ")
    SupplierItemAlias.objects.create(
        supplier_code="SUP-B", supplier_item_code="7788",
        supplier_item_name="رولمان بلي 6205", item=item,
    )

    res = contracts.resolve_item(supplier_code="SUP-B", code="7788", name="رولمان بلي 6205")

    assert res.item is not None
    assert res.item.sku == "RM-001"
    assert res.confidence == 100
    assert res.method == "alias_code"


def test_exact_sku_resolves_when_supplier_uses_our_sku():
    item = make_item(sku="RM-001", name="Bearing 6205 ZZ")

    res = contracts.resolve_item(supplier_code="SUP-A", code="RM-001", name="anything")

    assert res.item is not None and res.item.sku == "RM-001"
    assert res.confidence == 100
    assert res.method == "sku"


def test_alias_by_supplier_name_resolves_across_languages():
    """Case 3: a supplier that gives only a name (no stable code) still resolves via its name alias —
    Arabic incoming vs the Arabic alias stored against the English-named canonical item."""
    item = make_item(sku="RM-001", name="Bearing 6205 ZZ")
    SupplierItemAlias.objects.create(
        supplier_code="SUP-B", supplier_item_name="رولمان بلي 6205", item=item,
    )

    res = contracts.resolve_item(supplier_code="SUP-B", name="رولمان بلي  6205")  # extra space

    assert res.item is not None and res.item.sku == "RM-001"
    assert res.confidence == 95
    assert res.method == "alias_name"


def test_normalized_name_exact_match_same_language():
    """Case: no alias, but the incoming name equals an existing item name up to case/whitespace."""
    make_item(sku="RM-001", name="Bearing 6205 ZZ")

    res = contracts.resolve_item(supplier_code="SUP-C", name="bearing 6205 zz")

    assert res.item is not None and res.item.sku == "RM-001"
    assert res.confidence == 90
    assert res.method == "name"


def test_unknown_item_resolves_to_none():
    """Case 5: a genuinely new item resolves to nothing — the caller proposes creation."""
    make_item(sku="RM-001", name="Bearing 6205 ZZ")

    res = contracts.resolve_item(supplier_code="SUP-Z", code="ZZZ", name="Hydraulic Pump 3000")

    assert res.item is None
    assert res.confidence == 0
    assert res.method == "none"


def test_alias_is_supplier_scoped():
    """Case: the same supplier code means different things for different suppliers — an alias for
    SUP-B's 7788 must NOT resolve SUP-A's 7788."""
    item = make_item(sku="RM-001", name="Bearing 6205 ZZ")
    SupplierItemAlias.objects.create(supplier_code="SUP-B", supplier_item_code="7788", item=item)

    res = contracts.resolve_item(supplier_code="SUP-A", code="7788", name="Something else")

    assert res.item is None


def test_alias_wins_over_name_match():
    """A supplier alias is a stronger signal than a coincidental name match to a different item."""
    right = make_item(sku="RM-001", name="Bearing 6205 ZZ")
    make_item(sku="RM-999", name="Widget")
    SupplierItemAlias.objects.create(supplier_code="SUP-B", supplier_item_code="7788", item=right)

    res = contracts.resolve_item(supplier_code="SUP-B", code="7788", name="Widget")

    assert res.item is not None and res.item.sku == "RM-001"
    assert res.method == "alias_code"


# --- record_alias: the learning loop ------------------------------------------------------------
def test_record_alias_makes_next_resolution_deterministic():
    """Case 4: after a human confirms 7788 == RM-001 once, it resolves by code forever after."""
    item = make_item(sku="RM-001", name="Bearing 6205 ZZ")
    before = contracts.resolve_item(supplier_code="SUP-B", code="7788", name="رولمان بلي 6205")
    assert before.item is None

    contracts.record_alias(
        supplier_code="SUP-B", item_sku="RM-001",
        supplier_item_code="7788", supplier_item_name="رولمان بلي 6205",
    )

    after = contracts.resolve_item(supplier_code="SUP-B", code="7788", name="رولمان بلي 6205")
    assert after.item is not None and after.item.sku == "RM-001"
    assert after.method == "alias_code"


def test_record_alias_is_idempotent():
    """Recording the same match twice updates the one row, never a duplicate alias."""
    make_item(sku="RM-001", name="Bearing 6205 ZZ")
    contracts.record_alias(supplier_code="SUP-B", item_sku="RM-001", supplier_item_code="7788")
    contracts.record_alias(supplier_code="SUP-B", item_sku="RM-001", supplier_item_code="7788")

    assert SupplierItemAlias.objects.filter(supplier_code="SUP-B", supplier_item_code="7788").count() == 1


def test_record_alias_rejects_unknown_item():
    from erp.inventory.errors import UnknownItemError

    with pytest.raises(UnknownItemError):
        contracts.record_alias(supplier_code="SUP-B", item_sku="NOPE", supplier_item_code="7788")
