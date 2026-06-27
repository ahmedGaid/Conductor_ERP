"""Supplier CSV import spec — the canonical columns and the serializer the engine reuses."""
from __future__ import annotations

from erp.core.imports import ImportField, ImportSpec

from .api.serializers import SupplierSerializer
from .domain.models import Supplier

SUPPLIER_IMPORT = ImportSpec(
    key="code",
    model=Supplier,
    serializer=SupplierSerializer,
    fields=(
        ImportField(
            name="code", label_en="Code", label_ar="الكود", required=True,
            aliases=("كود", "رقم المورد", "supplier code"), example="S-1001",
        ),
        ImportField(
            name="name", label_en="Name", label_ar="الاسم", required=True,
            aliases=("اسم المورد", "supplier name", "اسم"), example="مصنع الدلتا",
        ),
        ImportField(
            name="is_active", label_en="Active", label_ar="نشط", kind="bool",
            aliases=("active", "الحالة", "مفعل"), example="yes",
        ),
    ),
)
