"""Import adapter: suppliers (``erp.purchasing``).

Writes go through ``erp.purchasing.contracts.create_supplier`` — mirrors ``sales.create_customer``.
Suppliers are company-wide, not actor-scoped (``list_suppliers``/``supplier_name_exists`` are
unscoped by the module's own design) — ``exists`` follows that same convention rather than
inventing a scope the module doesn't have.
"""
from __future__ import annotations

from django.conf import settings

from erp.identity.roles import BRANCH_MANAGER
from erp.purchasing import contracts
from erp.purchasing.domain.models import Supplier

from ..registry import FieldSpec, Issue, register
from ._rbac import require_role


class SupplierAdapter:
    entity = "suppliers"
    label_key = "imports.entity.suppliers"
    fields = [
        FieldSpec(
            name="code", kind="text",
            synonyms_en=["code", "supplier code", "id"],
            synonyms_ar=["كود", "كود المورد", "الرقم"],
        ),
        FieldSpec(
            name="name", required=True, kind="text",
            synonyms_en=["name", "supplier name", "supplier", "vendor"],
            synonyms_ar=["الاسم", "اسم المورد", "المورد"],
        ),
    ]
    natural_key = ["name"]
    group_by = None

    @property
    def defaults(self) -> dict:
        return dict(getattr(settings, "IMPORTS_DEFAULTS", {}).get(self.entity, {}))

    def lookup(self, actor, field, value):
        return None  # no ref fields on this entity

    def validate(self, actor, row: dict) -> list[Issue]:
        return []

    def write(self, actor, row: dict):
        require_role(actor, BRANCH_MANAGER)
        info = contracts.create_supplier(
            name=row["name"], code=row.get("code", "") or "", actor=actor,
        )
        return info

    def exists(self, actor, row: dict):
        code = (row.get("code") or "").strip()
        if code:
            return Supplier.objects.filter(code=code).first()
        return Supplier.objects.filter(name__iexact=(row.get("name") or "").strip()).first()


register(SupplierAdapter())
