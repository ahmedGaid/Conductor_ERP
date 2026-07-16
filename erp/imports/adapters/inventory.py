"""Import adapter: items (``erp.inventory``).

Writes go through ``erp.inventory.contracts.create_item`` — its docstring already says it "mirrors
``sales.create_customer`` / ``purchasing.create_supplier`` for the assistant's import path". Items
are company-wide (``low_stock``/``stock_on_hand`` are unscoped) — ``exists`` follows that convention.

Category is intentionally NOT a field here: ``create_item`` has no category parameter, and
``erp.inventory`` has no service create-path for ``Category`` (only an inline ORM create in the API
view) — item_categories, warehouses and price_lists are all out of scope for this session for the
same reason (Before-You-Start rule: STOP on a model-only entity, don't invent a second write-path).
See erp-status for the recorded blocker.
"""
from __future__ import annotations

from django.conf import settings

from erp.identity.roles import BRANCH_MANAGER
from erp.inventory import contracts
from erp.inventory.domain.models import Item

from ..registry import FieldSpec, Issue, register
from ._rbac import require_role


class ItemAdapter:
    entity = "items"
    label_key = "imports.entity.items"
    fields = [
        FieldSpec(
            name="sku", required=True, kind="text",
            synonyms_en=["sku", "item code", "code", "item"],
            synonyms_ar=["كود الصنف", "الصنف", "كود"],
        ),
        FieldSpec(
            name="name", required=True, kind="text",
            synonyms_en=["name", "item name", "description"],
            synonyms_ar=["الاسم", "اسم الصنف", "الوصف"],
        ),
        FieldSpec(
            name="uom", kind="text",
            synonyms_en=["uom", "unit", "unit of measure"],
            synonyms_ar=["الوحدة", "وحدة القياس"],
        ),
        FieldSpec(
            name="reorder_point", kind="number",
            synonyms_en=["reorder point", "reorder level"],
            synonyms_ar=["حد إعادة الطلب", "نقطة الطلب"],
        ),
    ]
    natural_key = ["sku"]
    group_by = None

    @property
    def defaults(self) -> dict:
        return dict(getattr(settings, "IMPORTS_DEFAULTS", {}).get(self.entity, {}))

    def lookup(self, actor, field, value):
        return None  # no ref fields wired into create_item yet (see module docstring)

    def validate(self, actor, row: dict) -> list[Issue]:
        return []

    def write(self, actor, row: dict):
        require_role(actor, BRANCH_MANAGER)
        info = contracts.create_item(
            sku=row["sku"], name=row["name"],
            uom=row.get("uom") or self.defaults.get("uom", "unit"),
            reorder_point=row.get("reorder_point") or 0,
            actor=actor,
        )
        return info

    def exists(self, actor, row: dict):
        return Item.objects.filter(sku=(row.get("sku") or "").strip()).first()

    def existing_labels(self, actor):
        return list(Item.objects.values_list("pk", "name"))


register(ItemAdapter())
