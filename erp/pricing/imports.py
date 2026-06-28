"""Price-list-line CSV import spec.

The import is scoped to a specific PriceList (resolved from the URL). Each row adds one line with
an item SKU, a unit price (human major units → minor via the ``money`` kind), an optional minimum
quantity (qty break), and an optional UOM. Lines with the same SKU+qty within the same file are
reported as duplicates; lines for different qty breaks of the same SKU are all created.

Factory function ``make_price_list_line_import`` returns a per-request ImportSpec that captures the
target PriceList so the engine's ``to_kwargs`` can attach it without needing a CSV column.
"""
from __future__ import annotations

from erp.core.imports import ImportField, ImportSpec

from .api.serializers import PriceListLineSerializer
from .domain.models import PriceList, PriceListLine


def make_price_list_line_import(price_list: PriceList) -> ImportSpec:
    """Return an ImportSpec for bulk-adding lines to *price_list*."""

    def to_kwargs(data: dict, _errors: list[dict]) -> dict:
        kwargs = dict(data)
        kwargs["price_list"] = price_list
        return kwargs

    return ImportSpec(
        key="item_sku",
        model=PriceListLine,
        serializer=PriceListLineSerializer,
        to_kwargs=to_kwargs,
        skip_existence_check=True,
        composite_dedup_fields=("item_sku", "min_quantity"),
        fields=(
            ImportField(
                name="item_sku",
                label_en="SKU",
                label_ar="رمز الصنف",
                required=True,
                aliases=("sku", "item code", "كود", "رمز"),
                example="WIDGET",
            ),
            ImportField(
                name="unit_price",
                label_en="Unit price",
                label_ar="سعر الوحدة",
                required=True,
                kind="money",
                target="unit_price_minor",
                aliases=("price", "سعر", "السعر", "unit_price_minor"),
                example="100.00",
            ),
            ImportField(
                name="min_quantity",
                label_en="Min qty",
                label_ar="الحد الأدنى للكمية",
                kind="decimal",
                aliases=("min qty", "min_qty", "quantity break", "الكمية الدنيا"),
                example="0",
            ),
            ImportField(
                name="uom",
                label_en="Unit",
                label_ar="الوحدة",
                aliases=("unit", "وحدة", "uom"),
                example="unit",
            ),
        ),
    )
