"""Customer CSV import spec — the canonical columns and the serializer the engine reuses."""
from __future__ import annotations

from erp.core.imports import ImportField, ImportSpec

from .api.serializers import CustomerSerializer
from .domain.models import Customer

CUSTOMER_IMPORT = ImportSpec(
    key="code",
    model=Customer,
    serializer=CustomerSerializer,
    fields=(
        ImportField(
            name="code", label_en="Code", label_ar="الكود", required=True,
            aliases=("كود", "رقم العميل", "customer code"), example="C-1001",
        ),
        ImportField(
            name="name", label_en="Name", label_ar="الاسم", required=True,
            aliases=("اسم العميل", "customer name", "اسم"), example="شركة النيل للتجارة",
        ),
        ImportField(
            name="credit_limit", label_en="Credit limit", label_ar="حد الائتمان",
            kind="money", target="credit_limit_minor",
            aliases=("credit", "الحد الائتماني"), example="50000",
        ),
        ImportField(
            name="is_active", label_en="Active", label_ar="نشط", kind="bool",
            aliases=("active", "الحالة", "مفعل"), example="yes",
        ),
    ),
)
