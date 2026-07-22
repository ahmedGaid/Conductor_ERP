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

import datetime as _dt
from decimal import Decimal

from django.conf import settings

from erp.identity.roles import BRANCH_MANAGER
from erp.inventory import contracts
from erp.inventory.domain.models import Item, PendingStockEntry, PendingStockEntryStatus, Warehouse
from erp.inventory.services.pending_stock import create_pending_stock_opening

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

    def resolve(self, actor, value, context):
        """Supplier-aware item resolution (duck-typed hook the masters engine calls when an item
        ``missing_ref`` needs a link proposal). Uses the incoming supplier's context so an alias for
        that supplier's own code/name resolves to the canonical SKU — the multi-supplier fix. Returns
        ``{sku, confidence, method}`` or ``None`` (the caller then proposes creating a new item)."""
        res = contracts.resolve_item(
            supplier_code=(context or {}).get("supplier_code", ""), code=value, name=value,
        )
        if res.item is None:
            return None
        return {"sku": res.item.sku, "confidence": res.confidence, "method": res.method}

    def capture(self, actor, value, context, sku):
        """Learning loop: record the human-confirmed supplier→canonical match so the next document
        from that supplier resolves deterministically. No supplier context ⇒ nothing to learn."""
        supplier_code = (context or {}).get("supplier_code", "")
        if not supplier_code or not sku:
            return
        contracts.record_alias(
            supplier_code=supplier_code, item_sku=sku,
            supplier_item_code=value, source="imported", actor=actor,
        )

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


# --- inventory_opening (session 16c — PendingStockEntry, drafts-only) -----------------------------
def _as_date(value) -> _dt.date | None:
    """Mirrors ``adapters.accounting._as_date`` — a ``kind="date"`` field round-trips through
    ``ImportRow.normalized`` (a JSONField) as an ISO string by the time ``write`` sees it."""
    if isinstance(value, _dt.date):
        return value
    if isinstance(value, str) and value:
        return _dt.date.fromisoformat(value)
    return None


class InventoryOpeningAdapter:
    """Item-level opening stock balances (go-live): always stages a ``PendingStockEntry`` — never
    calls ``receive_stock`` at import time (it posts Dr Inventory / Cr GRNI, wrong for an opening,
    and would double-count the Inventory control account ``account_opening`` already books from the
    trial balance — see ``adapters/accounting.py``'s ``inventory_double_booked`` guard). Applying is
    a human review-screen action (``erp.inventory.services.pending_stock``), out of scope here.

    No natural key: like ``receipts``/``payments``, a flat opening-quantities file rarely carries a
    stable per-row id, so ``exists`` always returns ``None`` — every import run creates new pending
    rows. True duplicates are a human's call on the (future) review screen.
    """

    entity = "inventory_opening"
    label_key = "imports.entity.inventoryOpening"
    fields = [
        FieldSpec(
            name="item_ref", required=True, kind="ref", ref="items",
            synonyms_en=["item", "sku", "item code"],
            synonyms_ar=["الصنف", "كود الصنف"],
        ),
        FieldSpec(
            name="warehouse_ref", required=True, kind="text",
            synonyms_en=["warehouse", "warehouse code", "location"],
            synonyms_ar=["المخزن", "كود المخزن"],
        ),
        FieldSpec(
            name="quantity", required=True, kind="number",
            synonyms_en=["quantity", "qty", "opening quantity"],
            synonyms_ar=["الكمية", "الكمية الافتتاحية"],
        ),
        FieldSpec(
            name="unit_cost_minor", required=True, kind="money",
            synonyms_en=["unit cost", "cost", "unit price"],
            synonyms_ar=["تكلفة الوحدة", "التكلفة"],
        ),
        FieldSpec(
            name="date", required=True, kind="date",
            synonyms_en=["date", "opening date", "as of"],
            synonyms_ar=["التاريخ", "تاريخ الرصيد الافتتاحي"],
        ),
    ]
    natural_key = []
    group_by = None

    @property
    def defaults(self) -> dict:
        return dict(getattr(settings, "IMPORTS_DEFAULTS", {}).get(self.entity, {}))

    def lookup(self, actor, field, value):
        if field == "item_ref":
            return contracts.find_item(value)
        return None

    def validate(self, actor, row: dict) -> list[Issue]:
        return []

    def write(self, actor, row: dict):
        require_role(actor, BRANCH_MANAGER)
        item = Item.objects.filter(sku=(row.get("item_ref") or "").strip()).first()
        if item is None:
            raise ValueError(f"unknown item: {row.get('item_ref')!r}")
        warehouse_code = (row.get("warehouse_ref") or "").strip()
        warehouse = Warehouse.objects.filter(code=warehouse_code).first()
        if warehouse is None:
            raise ValueError(f"unknown warehouse: {warehouse_code!r}")
        return create_pending_stock_opening(
            item=item, warehouse=warehouse,
            quantity=Decimal(str(row["quantity"])),
            unit_cost_minor=int(row["unit_cost_minor"]),
            date=_as_date(row.get("date")) or _dt.date.today(),
            suspense_account=self.defaults.get("suspense_account") or "3110",
            actor=actor,
        )

    def exists(self, actor, row: dict):
        return None

    def existing_labels(self, actor):
        return []

    def delete(self, actor, pk) -> None:
        """Rollback support: a still-PENDING entry has posted nothing anywhere, so a plain delete is
        a true reversal. Refuses once applied/discarded — never deletes a row a human already acted
        on."""
        pending = PendingStockEntry.objects.filter(pk=pk).first()
        if pending is None:
            return
        if pending.status != PendingStockEntryStatus.PENDING:
            raise ValueError(
                f"cannot delete pending stock entry {pending.pk}: status is {pending.status!r}, "
                "not pending"
            )
        pending.delete()


register(InventoryOpeningAdapter())
