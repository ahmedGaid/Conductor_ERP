"""Import adapters: customers + sales invoices (``erp.sales``).

Customers write through ``erp.sales.contracts.create_customer`` — the exact same code-based,
no-ORM-leak entry point the AI assistant's import path already uses. Sales invoices (FILE_15 Task B)
write through ``erp.sales.contracts.create_order`` (re-exported straight from
``services.orders`` — the module's real write-path; ``contracts.place_order`` doesn't expose
``tax_code``, the one param this adapter needs that the thinner wrapper omits). Both adapters never
touch ``Customer``/``SalesOrder`` directly for WRITES; ``SalesInvoiceAdapter.delete`` is the one
exception (see its docstring) — a plain ORM delete of a still-DRAFT order, which has posted nothing
anywhere yet, so there is no other module write-path to route a reversal through.
"""
from __future__ import annotations

import datetime as _dt
from decimal import Decimal

from django.conf import settings

from erp.accounting.domain.models import TaxCode
from erp.identity.roles import BRANCH_MANAGER
from erp.identity.scoping import scope_queryset
from erp.inventory import contracts as inventory
from erp.sales import contracts
from erp.sales.domain.models import Customer, OrderStatus, SalesOrder
from erp.sales.services.orders import OrderLineInput

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

    def existing_labels(self, actor):
        qs = scope_queryset(actor, Customer.objects.all(), "sales.customer.view")
        return list(qs.values_list("pk", "name"))


register(CustomerAdapter())


# --- sales invoices (FILE_15 Task B) --------------------------------------------------------------
def _as_date(value) -> _dt.date | None:
    """``kind="date"`` fields round-trip through ``ImportRow.normalized`` (a JSONField) as ISO
    strings (``analyze._json_safe``) — never a live ``datetime.date`` by the time ``write`` sees
    them."""
    if isinstance(value, _dt.date):
        return value
    if isinstance(value, str) and value:
        return _dt.date.fromisoformat(value)
    return None


def _find_customer(actor, ref: str):
    ref = (ref or "").strip()
    if not ref:
        return None
    qs = scope_queryset(actor, Customer.objects.all(), "sales.customer.view")
    return qs.filter(code=ref).first() or qs.filter(name__iexact=ref).first()


def _resolve_tax_code(value) -> str | None:
    """A raw tax cell ("14%", "VAT", "معفى") → a configured ``TaxCode.code``, ``""`` for an
    explicitly untaxed line, or ``None`` when the token can't be matched to any configured rate —
    the ``missing_ref`` case ``lookup`` and ``write`` share."""
    from ..normalize import normalize_tax  # local import: avoids a normalize<->adapters import cycle

    if value in (None, ""):
        return ""
    token = normalize_tax(value)
    if token.kind == "exempt":
        return ""
    if token.kind == "vat" and token.rate is not None:
        tax_code = TaxCode.objects.filter(rate_bps=token.rate * 100, is_active=True).first()
        return tax_code.code if tax_code else None
    return None


class SalesInvoiceAdapter:
    """Flat-Excel invoice sheets: one row per LINE, header fields (customer/date/…) repeated or
    filled only on the group's first row. ``write`` creates a DRAFT ``SalesOrder`` — invoicing
    (the GL posting) stays a deliberate module-screen action (STRATEGY §3 mechanic 3), never
    something an import does on its own. There is no distinct "invoice" document in this codebase
    (invoicing is a status transition on a sales order — see ``services.orders.invoice_order``), so
    a sales-invoice import lands as a draft order the user walks through confirm → deliver → invoice
    like any other, exactly as spec'd.

    The source system's invoice number has nowhere to live on ``SalesOrder`` (``number`` is always
    server-assigned — ``SO-YYYY-NNNNNN``), so it's kept in ``notes`` as ``"import:<doc_number>"`` —
    the natural key ``exists``/rollback match against, without a schema change outside this file's
    stated scope.
    """

    entity = "sales_invoices"
    label_key = "imports.entity.salesInvoices"
    fields = [
        # --- header (one per document; blank on continuation rows of the same group) ---
        FieldSpec(
            name="doc_number", kind="text",
            synonyms_en=["invoice number", "invoice no", "invoice #"],
            synonyms_ar=["رقم الفاتورة", "رقم فاتورة"],
        ),
        FieldSpec(
            name="customer_ref", kind="ref", ref="customers",
            synonyms_en=["customer", "customer code", "customer name", "bill to"],
            synonyms_ar=["العميل", "كود العميل", "اسم العميل"],
        ),
        FieldSpec(
            name="date", kind="date",
            synonyms_en=["date", "invoice date"],
            synonyms_ar=["التاريخ", "تاريخ الفاتورة"],
        ),
        FieldSpec(
            name="currency", kind="text",
            synonyms_en=["currency"],
            synonyms_ar=["العملة"],
        ),
        FieldSpec(
            name="warehouse_ref", kind="text",
            synonyms_en=["warehouse", "warehouse code"],
            synonyms_ar=["المخزن", "كود المخزن"],
        ),
        FieldSpec(
            name="tax_token", kind="ref", ref="tax_codes",
            synonyms_en=["tax", "vat", "tax rate"],
            synonyms_ar=["الضريبة", "ضريبة القيمة المضافة"],
        ),
        FieldSpec(
            name="file_total_minor", kind="money",
            synonyms_en=["total", "grand total", "invoice total"],
            synonyms_ar=["الإجمالي", "إجمالي الفاتورة"],
        ),
        # --- line (every row) ---
        FieldSpec(
            name="item_ref", required=True, kind="ref", ref="items",
            synonyms_en=["item", "sku", "item code"],
            synonyms_ar=["الصنف", "كود الصنف"],
        ),
        FieldSpec(
            name="quantity", required=True, kind="number",
            synonyms_en=["qty", "quantity"],
            synonyms_ar=["الكمية"],
        ),
        FieldSpec(
            name="unit_price_minor", required=True, kind="money",
            synonyms_en=["unit price", "price"],
            synonyms_ar=["سعر الوحدة", "السعر"],
        ),
        FieldSpec(
            name="discount_minor", kind="money",
            synonyms_en=["discount"],
            synonyms_ar=["خصم"],
        ),
    ]
    natural_key = ["doc_number"]
    group_by = "doc_number"
    header_fields = [
        "doc_number", "customer_ref", "date", "currency", "warehouse_ref",
        "tax_token", "file_total_minor",
    ]

    @property
    def defaults(self) -> dict:
        return dict(getattr(settings, "IMPORTS_DEFAULTS", {}).get(self.entity, {}))

    def lookup(self, actor, field, value):
        if field == "customer_ref":
            return _find_customer(actor, value)
        if field == "item_ref":
            return inventory.find_item(value)
        if field == "tax_token":
            code = _resolve_tax_code(value)
            return code if code is not None else None
        return None

    def validate(self, actor, row: dict) -> list[Issue]:
        return []

    def write(self, actor, group: dict):
        require_role(actor, BRANCH_MANAGER)
        customer = _find_customer(actor, group.get("customer_ref"))
        if customer is None:
            raise ValueError(f"unknown customer: {group.get('customer_ref')!r}")

        warehouse_code = (
            (group.get("warehouse_ref") or "").strip()
            or self.defaults.get("warehouse_code")
            or inventory.default_warehouse_code()
            or ""
        )
        tax_code = _resolve_tax_code(group.get("tax_token")) or ""
        doc_number = (group.get("doc_number") or "").strip()

        lines = [
            OrderLineInput(
                item_sku=(line.get("item_ref") or "").strip(),
                quantity=Decimal(str(line["quantity"])),
                unit_price_minor=int(line["unit_price_minor"]),
                discount_minor=int(line.get("discount_minor") or 0),
            )
            for line in group["lines"]
        ]
        order = contracts.create_order(
            customer=customer,
            warehouse_code=warehouse_code,
            lines=lines,
            order_date=_as_date(group.get("date")) or _dt.date.today(),
            currency=group.get("currency") or self.defaults.get("currency", "EGP"),
            notes=f"import:{doc_number}",
            tax_code=tax_code,
            actor=actor,
        )

        warnings: list[Issue] = []
        file_total = group.get("file_total_minor")
        if file_total is not None and int(file_total) != order.subtotal_minor:
            warnings.append(Issue(
                field="file_total_minor", code="total_mismatch",
                message="imports.issues.totalMismatch",
                meta={"file_total_minor": int(file_total), "computed_total_minor": order.subtotal_minor},
            ))
        return order, warnings

    def exists(self, actor, group: dict):
        doc_number = (group.get("doc_number") or "").strip()
        if not doc_number:
            return None
        qs = scope_queryset(actor, SalesOrder.objects.all(), "sales.order.view")
        return qs.filter(notes=f"import:{doc_number}").first()

    def delete(self, actor, pk) -> None:
        """Rollback support: a DRAFT order created by this adapter has posted nothing anywhere
        (no journal entry, no stock movement — see ``services.orders.create_order``), so a plain
        delete is a true, side-effect-free reversal. Refuses (raises, reported ``cannot_revert`` by
        the engine) if the order has moved past DRAFT since import — never deletes a posted or
        part-fulfilled order out from under the business."""
        order = SalesOrder.objects.filter(pk=pk).first()
        if order is None:
            return  # already gone — rollback is idempotent
        if order.status != OrderStatus.DRAFT:
            raise ValueError(f"cannot delete order {order.number}: status is {order.status!r}, not draft")
        order.delete()

    def existing_labels(self, actor):
        qs = scope_queryset(
            actor, SalesOrder.objects.filter(notes__startswith="import:"), "sales.order.view",
        )
        return list(qs.values_list("pk", "number"))


register(SalesInvoiceAdapter())
