"""Item CSV import spec — exercises FK resolution (category_code) and choice/decimal fields."""
from __future__ import annotations

from erp.core.imports import ImportField, ImportSpec

from .api.serializers import ItemSerializer
from .domain.models import Category, Item


def _to_item_kwargs(data: dict, errors: list[dict]) -> dict:
    """Resolve category_code -> Category. A code that matches nothing is a row error, not a silent
    null (the single-create path nulls it; at import scale that would quietly lose categorisation)."""
    kwargs = dict(data)
    code = str(kwargs.pop("category_code", "") or "").strip()
    category = None
    if code:
        category = Category.objects.filter(code=code).first()
        if category is None:
            errors.append({"field": "category_code", "message": f"category '{code}' not found"})
    kwargs["category"] = category
    return kwargs


ITEM_IMPORT = ImportSpec(
    key="sku",
    model=Item,
    serializer=ItemSerializer,
    to_kwargs=_to_item_kwargs,
    fields=(
        ImportField(
            name="sku", label_en="SKU", label_ar="رمز الصنف", required=True,
            aliases=("كود", "رمز الصنف", "item code"), example="ITM-1001",
        ),
        ImportField(
            name="name", label_en="Name", label_ar="الاسم", required=True,
            aliases=("اسم الصنف", "item name", "اسم"), example="أسمنت بورتلاندي",
        ),
        ImportField(
            name="category_code", label_en="Category", label_ar="الفئة",
            aliases=("category", "فئة", "التصنيف", "category code"), example="RAW",
        ),
        ImportField(
            name="uom", label_en="Unit", label_ar="الوحدة",
            aliases=("unit", "وحدة"), example="unit",
        ),
        ImportField(
            name="type", label_en="Type", label_ar="النوع",
            aliases=("نوع",), example="stock",
        ),
        ImportField(
            name="reorder_point", label_en="Reorder point", label_ar="حد إعادة الطلب",
            kind="decimal", aliases=("reorder", "نقطة إعادة الطلب"), example="10",
        ),
        ImportField(
            name="is_active", label_en="Active", label_ar="نشط", kind="bool",
            aliases=("active", "الحالة", "مفعل"), example="yes",
        ),
    ),
)
