"""Import adapter: customers (``erp.sales``).

Writes go through ``erp.sales.contracts.create_customer`` — the exact same code-based, no-ORM-leak
entry point the AI assistant's import path already uses (see that function's docstring). Adapters
never touch ``Customer`` directly for writes.
"""
from __future__ import annotations

from django.conf import settings

from erp.identity.roles import BRANCH_MANAGER
from erp.identity.scoping import scope_queryset
from erp.sales import contracts
from erp.sales.domain.models import Customer

from ..registry import FieldSpec, Issue, register
from ._rbac import require_role


class CustomerAdapter:
    entity = "customers"
    label_key = "imports.entity.customers"
    fields = [
        FieldSpec(
            name="code", kind="text",
            synonyms_en=["code", "customer code", "id"],
            synonyms_ar=["كود", "كود العميل", "الرقم"],
        ),
        FieldSpec(
            name="name", required=True, kind="text",
            synonyms_en=["name", "customer name", "customer", "company"],
            synonyms_ar=["الاسم", "اسم العميل", "العميل", "اسم الشركة"],
        ),
        FieldSpec(
            name="credit_limit_minor", kind="money",
            synonyms_en=["credit limit", "credit"],
            synonyms_ar=["حد الائتمان", "الحد الائتماني"],
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
        info = contracts.create_customer(
            name=row["name"],
            code=row.get("code", "") or "",
            credit_limit_minor=row.get("credit_limit_minor") or 0,
            actor=actor,
        )
        return info

    def exists(self, actor, row: dict):
        qs = scope_queryset(actor, Customer.objects.all(), "sales.customer.view")
        code = (row.get("code") or "").strip()
        if code:
            return qs.filter(code=code).first()
        return qs.filter(name__iexact=(row.get("name") or "").strip()).first()


register(CustomerAdapter())
