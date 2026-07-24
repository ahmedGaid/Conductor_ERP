"""Import adapters: suppliers + purchase invoices (``erp.purchasing``).

Suppliers write through ``erp.purchasing.contracts.create_supplier`` — mirrors
``sales.create_customer``. Suppliers are company-wide, not actor-scoped
(``list_suppliers``/``supplier_name_exists`` are unscoped by the module's own design) — ``exists``
follows that same convention rather than inventing a scope the module doesn't have.

Purchase orders + purchase invoices (FILE_15 Task B) both mirror ``sales.SalesInvoiceAdapter`` /
``sales.SalesOrderAdapter`` exactly — see those classes' docstrings for the "no distinct invoice
document, no user-settable order number" reasoning, which applies here unchanged (``PurchaseOrder``
has the identical shape). Writes go through ``erp.purchasing.contracts.create_order`` (re-exported
from ``services.orders`` — ``place_order`` doesn't expose ``tax_code``). The two adapters are
distinguished only by a ``notes`` tag prefix (``import-po:`` vs ``import:``) so their natural-key
matching never collides on the shared ``PurchaseOrder`` table.
"""
from __future__ import annotations

import datetime as _dt
from decimal import Decimal

from django.conf import settings

from erp.accounting.domain.models import TaxCode
from erp.identity.roles import BRANCH_MANAGER
from erp.identity.scoping import scope_queryset
from erp.inventory import contracts as inventory
from erp.purchasing import contracts
from erp.purchasing.domain.models import (
    PendingPayment,
    PendingPaymentStatus,
    POStatus,
    PurchaseOrder,
    Supplier,
)
from erp.purchasing.services.orders import POLineInput
from erp.purchasing.services.pending_payments import create_pending_payment

from .. import grouping
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

    def existing_labels(self, actor):
        return list(Supplier.objects.values_list("pk", "name"))


register(SupplierAdapter())


# --- purchase orders, purchase invoices (FILE_15 Task B) -----------------------------------------
def _as_date(value) -> _dt.date | None:
    if isinstance(value, _dt.date):
        return value
    if isinstance(value, str) and value:
        return _dt.date.fromisoformat(value)
    return None


def _find_supplier(ref: str):
    ref = (ref or "").strip()
    if not ref:
        return None
    return Supplier.objects.filter(code=ref).first() or Supplier.objects.filter(name__iexact=ref).first()


def _resolve_tax_code(value) -> str | None:
    from ..normalize import (
        normalize_tax,  # local import: avoids a normalize<->adapters import cycle
    )

    if value in (None, ""):
        return ""
    token = normalize_tax(value)
    if token.kind == "exempt":
        return ""
    if token.kind == "vat" and token.rate is not None:
        tax_code = TaxCode.objects.filter(rate_bps=token.rate * 100, is_active=True).first()
        return tax_code.code if tax_code else None
    return None


class PurchaseOrderAdapter:
    """Mirrors ``sales.SalesOrderAdapter`` for the purchasing side — see that class's docstring for
    the shared reasoning (this and ``PurchaseInvoiceAdapter`` both write a DRAFT ``PurchaseOrder``
    via the identical ``contracts.create_order`` write-path; only the ``notes`` tag prefix differs).
    """

    entity = "purchase_orders"
    label_key = "imports.entity.purchaseOrders"
    fields = [
        # --- header (one per document; blank on continuation rows of the same group) ---
        FieldSpec(
            name="doc_number", kind="text",
            synonyms_en=["order number", "PO number", "order no"],
            synonyms_ar=["رقم الطلب", "رقم أمر الشراء"],
        ),
        FieldSpec(
            name="supplier_ref", kind="ref", ref="suppliers",
            synonyms_en=["supplier", "supplier code", "supplier name", "vendor"],
            synonyms_ar=["المورد", "كود المورد", "اسم المورد"],
        ),
        FieldSpec(
            name="date", kind="date",
            synonyms_en=["date", "order date"],
            synonyms_ar=["التاريخ", "تاريخ الطلب"],
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
            synonyms_en=["total", "grand total", "order total"],
            synonyms_ar=["الإجمالي", "إجمالي الطلب"],
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
            synonyms_en=["unit cost", "unit price", "cost"],
            synonyms_ar=["سعر الوحدة", "التكلفة"],
        ),
    ]
    natural_key = ["doc_number"]
    group_by = "doc_number"
    header_fields = [
        "doc_number", "supplier_ref", "date", "currency", "warehouse_ref",
        "tax_token", "file_total_minor",
    ]

    @property
    def defaults(self) -> dict:
        return dict(getattr(settings, "IMPORTS_DEFAULTS", {}).get(self.entity, {}))

    def lookup(self, actor, field, value):
        if field == "supplier_ref":
            return _find_supplier(value)
        if field == "item_ref":
            return inventory.find_item(value)
        if field == "tax_token":
            code = _resolve_tax_code(value)
            return code if code is not None else None
        return None

    def ref_context(self, row: dict, field: str) -> dict:
        """Supplier context for an item ``missing_ref`` (duck-typed hook read in ``validate.py``), so
        the masters resolver can consult THIS supplier's aliases — the same supplier code/name can mean
        a different item for a different supplier. Only the item ref carries it; other refs get none."""
        if field != "item_ref":
            return {}
        supplier = _find_supplier(row.get("supplier_ref"))
        return {"supplier_code": supplier.code} if supplier else {}

    def validate(self, actor, row: dict) -> list[Issue]:
        return []

    def write(self, actor, group: dict):
        require_role(actor, BRANCH_MANAGER)
        supplier = _find_supplier(group.get("supplier_ref"))
        if supplier is None:
            raise ValueError(f"unknown supplier: {group.get('supplier_ref')!r}")

        warehouse_code = (
            (group.get("warehouse_ref") or "").strip()
            or self.defaults.get("warehouse_code")
            or inventory.default_warehouse_code()
            or ""
        )
        tax_code = _resolve_tax_code(group.get("tax_token")) or ""
        doc_number = (group.get("doc_number") or "").strip()

        lines = [
            POLineInput(
                item_sku=(line.get("item_ref") or "").strip(),
                quantity=Decimal(str(line["quantity"])),
                unit_cost_minor=int(line["unit_price_minor"]),
            )
            for line in group["lines"]
        ]
        order = contracts.create_order(
            supplier=supplier,
            warehouse_code=warehouse_code,
            lines=lines,
            order_date=_as_date(group.get("date")) or _dt.date.today(),
            currency=group.get("currency") or self.defaults.get("currency", "EGP"),
            notes=f"import-po:{doc_number}",
            tax_code=tax_code,
            actor=actor,
        )

        warnings: list[Issue] = []
        mismatch = grouping.total_mismatch_issue(group.get("file_total_minor"), order.subtotal_minor)
        if mismatch is not None:
            warnings.append(mismatch)
        return order, warnings

    def exists(self, actor, group: dict):
        doc_number = (group.get("doc_number") or "").strip()
        if not doc_number:
            return None
        qs = scope_queryset(actor, PurchaseOrder.objects.all(), "purchasing.order.view")
        return qs.filter(notes=f"import-po:{doc_number}").first()

    def delete(self, actor, pk) -> None:
        """Rollback support — see ``PurchaseInvoiceAdapter.delete``: a DRAFT purchase order has
        posted nothing anywhere yet, so a plain delete is a true, side-effect-free reversal."""
        order = PurchaseOrder.objects.filter(pk=pk).first()
        if order is None:
            return  # already gone — rollback is idempotent
        if order.status != POStatus.DRAFT:
            raise ValueError(f"cannot delete order {order.number}: status is {order.status!r}, not draft")
        order.delete()

    def existing_labels(self, actor):
        qs = scope_queryset(
            actor, PurchaseOrder.objects.filter(notes__startswith="import-po:"), "purchasing.order.view",
        )
        return list(qs.values_list("pk", "number"))


register(PurchaseOrderAdapter())


class PurchaseInvoiceAdapter:
    """Mirrors ``sales.SalesInvoiceAdapter`` for the purchasing side — see that class's docstring
    for the shared reasoning (no distinct invoice document; ``PurchaseOrder.number`` is always
    server-assigned so the source system's invoice/bill number lives in ``notes`` as
    ``"import:<doc_number>"``). ``write`` creates a DRAFT ``PurchaseOrder``; billing (the GL
    posting via ``bill_order``) stays a deliberate module-screen action.
    """

    entity = "purchase_invoices"
    label_key = "imports.entity.purchaseInvoices"
    fields = [
        # --- header (one per document; blank on continuation rows of the same group) ---
        FieldSpec(
            name="doc_number", kind="text",
            synonyms_en=["invoice number", "bill number", "invoice no"],
            synonyms_ar=["رقم الفاتورة", "رقم فاتورة المورد"],
        ),
        FieldSpec(
            name="supplier_ref", kind="ref", ref="suppliers",
            synonyms_en=["supplier", "supplier code", "supplier name", "vendor"],
            synonyms_ar=["المورد", "كود المورد", "اسم المورد"],
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
            synonyms_en=["unit cost", "unit price", "cost"],
            synonyms_ar=["سعر الوحدة", "التكلفة"],
        ),
    ]
    natural_key = ["doc_number"]
    group_by = "doc_number"
    header_fields = [
        "doc_number", "supplier_ref", "date", "currency", "warehouse_ref",
        "tax_token", "file_total_minor",
    ]

    @property
    def defaults(self) -> dict:
        return dict(getattr(settings, "IMPORTS_DEFAULTS", {}).get(self.entity, {}))

    def lookup(self, actor, field, value):
        if field == "supplier_ref":
            return _find_supplier(value)
        if field == "item_ref":
            return inventory.find_item(value)
        if field == "tax_token":
            code = _resolve_tax_code(value)
            return code if code is not None else None
        return None

    def ref_context(self, row: dict, field: str) -> dict:
        """Supplier context for an item ``missing_ref`` — see ``PurchaseOrderAdapter.ref_context``."""
        if field != "item_ref":
            return {}
        supplier = _find_supplier(row.get("supplier_ref"))
        return {"supplier_code": supplier.code} if supplier else {}

    def validate(self, actor, row: dict) -> list[Issue]:
        return []

    def write(self, actor, group: dict):
        require_role(actor, BRANCH_MANAGER)
        supplier = _find_supplier(group.get("supplier_ref"))
        if supplier is None:
            raise ValueError(f"unknown supplier: {group.get('supplier_ref')!r}")

        warehouse_code = (
            (group.get("warehouse_ref") or "").strip()
            or self.defaults.get("warehouse_code")
            or inventory.default_warehouse_code()
            or ""
        )
        tax_code = _resolve_tax_code(group.get("tax_token")) or ""
        doc_number = (group.get("doc_number") or "").strip()

        lines = [
            POLineInput(
                item_sku=(line.get("item_ref") or "").strip(),
                quantity=Decimal(str(line["quantity"])),
                unit_cost_minor=int(line["unit_price_minor"]),
            )
            for line in group["lines"]
        ]
        order = contracts.create_order(
            supplier=supplier,
            warehouse_code=warehouse_code,
            lines=lines,
            order_date=_as_date(group.get("date")) or _dt.date.today(),
            currency=group.get("currency") or self.defaults.get("currency", "EGP"),
            notes=f"import:{doc_number}",
            tax_code=tax_code,
            actor=actor,
        )

        warnings: list[Issue] = []
        mismatch = grouping.total_mismatch_issue(group.get("file_total_minor"), order.subtotal_minor)
        if mismatch is not None:
            warnings.append(mismatch)
        return order, warnings

    def exists(self, actor, group: dict):
        doc_number = (group.get("doc_number") or "").strip()
        if not doc_number:
            return None
        qs = scope_queryset(actor, PurchaseOrder.objects.all(), "purchasing.order.view")
        return qs.filter(notes=f"import:{doc_number}").first()

    def delete(self, actor, pk) -> None:
        """Rollback support — see ``sales.SalesInvoiceAdapter.delete``: a DRAFT purchase order has
        posted nothing anywhere yet, so a plain delete is a true, side-effect-free reversal."""
        order = PurchaseOrder.objects.filter(pk=pk).first()
        if order is None:
            return  # already gone — rollback is idempotent
        if order.status != POStatus.DRAFT:
            raise ValueError(f"cannot delete order {order.number}: status is {order.status!r}, not draft")
        order.delete()

    def existing_labels(self, actor):
        qs = scope_queryset(
            actor, PurchaseOrder.objects.filter(notes__startswith="import:"), "purchasing.order.view",
        )
        return list(qs.values_list("pk", "number"))


register(PurchaseInvoiceAdapter())


# --- payments (session 16b — PendingPayment, drafts-only) ------------------------------------------
def _find_order(actor, ref: str):
    """Mirrors ``adapters.sales._find_order`` — see that function's docstring."""
    ref = (ref or "").strip()
    if not ref:
        return None
    qs = scope_queryset(actor, PurchaseOrder.objects.all(), "purchasing.order.view")
    return qs.filter(number=ref).first() or qs.filter(notes__in=[f"import:{ref}", f"import-po:{ref}"]).first()


_METHOD_TOKENS = {
    "cash": "cash", "نقدي": "cash", "نقدا": "cash",
    "transfer": "transfer", "bank transfer": "transfer", "تحويل": "transfer", "تحويل بنكي": "transfer",
    "cheque": "cheque", "check": "cheque", "شيك": "cheque",
}


def _normalize_method(value) -> str:
    token = str(value or "").strip().casefold()
    return _METHOD_TOKENS.get(token, "")


class PaymentAdapter:
    """Supplier payments — mirrors ``adapters.sales.ReceiptAdapter`` exactly; see that class's
    docstring for the drafts-only reasoning and the no-natural-key decision."""

    entity = "payments"
    label_key = "imports.entity.payments"
    fields = [
        FieldSpec(
            name="supplier_ref", required=True, kind="ref", ref="suppliers",
            synonyms_en=["supplier", "supplier code", "supplier name", "vendor"],
            synonyms_ar=["المورد", "كود المورد", "اسم المورد"],
        ),
        FieldSpec(
            name="amount_minor", required=True, kind="money",
            synonyms_en=["amount", "payment amount", "paid"],
            synonyms_ar=["المبلغ", "مبلغ الدفعة", "المدفوع"],
        ),
        FieldSpec(
            name="date", required=True, kind="date",
            synonyms_en=["date", "payment date"],
            synonyms_ar=["التاريخ", "تاريخ الدفعة"],
        ),
        FieldSpec(
            name="method", kind="text",
            synonyms_en=["method", "payment method"],
            synonyms_ar=["طريقة الدفع", "الطريقة"],
        ),
        FieldSpec(
            name="order_ref", kind="text",
            synonyms_en=["bill number", "invoice number", "order number"],
            synonyms_ar=["رقم الفاتورة", "رقم الطلب"],
        ),
    ]
    natural_key = []
    group_by = None

    @property
    def defaults(self) -> dict:
        return dict(getattr(settings, "IMPORTS_DEFAULTS", {}).get(self.entity, {}))

    def lookup(self, actor, field, value):
        if field == "supplier_ref":
            return _find_supplier(value)
        return None

    def validate(self, actor, row: dict) -> list[Issue]:
        return []

    def write(self, actor, row: dict):
        require_role(actor, BRANCH_MANAGER)
        supplier = _find_supplier(row.get("supplier_ref"))
        order = _find_order(actor, row.get("order_ref"))
        pending = create_pending_payment(
            order=order,
            party_code=supplier.code if supplier else (row.get("supplier_ref") or "").strip(),
            amount_minor=int(row["amount_minor"]),
            date=_as_date(row.get("date")) or _dt.date.today(),
            method=_normalize_method(row.get("method")),
            source="import",
            actor=actor,
        )
        if order is None:
            return pending, [Issue(
                field="order_ref", code="payment_unmatched", message="imports.issues.paymentUnmatched",
                meta={"supplier_ref": row.get("supplier_ref"), "order_ref": row.get("order_ref")},
            )]
        return pending

    def exists(self, actor, row: dict):
        return None

    def existing_labels(self, actor):
        return []

    def delete(self, actor, pk) -> None:
        pending = PendingPayment.objects.filter(pk=pk).first()
        if pending is None:
            return
        if pending.status != PendingPaymentStatus.PENDING:
            raise ValueError(f"cannot delete pending payment {pending.pk}: status is {pending.status!r}, not pending")
        pending.delete()


register(PaymentAdapter())
