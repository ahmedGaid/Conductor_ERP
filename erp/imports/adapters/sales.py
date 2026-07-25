"""Import adapters: customers + sales documents (``erp.sales``).

Customers write through ``erp.sales.contracts.create_customer`` — the exact same code-based,
no-ORM-leak entry point the AI assistant's import path already uses. The three document adapters
(FILE_15 Task B) never touch ``Quotation``/``SalesOrder`` directly for WRITES; each adapter's
``delete`` is the one exception (see its docstring) — a plain ORM delete of a still-DRAFT
document, which has posted nothing anywhere yet, so there is no other module write-path to route
a reversal through.

``sales_orders`` and ``sales_invoices`` both create a **DRAFT ``SalesOrder``** — this codebase has
no separate "order" vs "invoice" model; invoicing is a status transition
(``services.orders.invoice_order``) that imports deliberately never trigger (STRATEGY §3 mechanic
3: imports create DRAFTS, posting stays on module screens). The two adapters are distinguished only
by a ``notes`` tag prefix (``import-so:`` vs ``import:``) so their natural-key matching (``exists``/
rollback) never collides on the shared ``SalesOrder`` table. ``sales_quotations`` is the one genuinely distinct
document — it targets the real ``Quotation`` model/service, which carries no tax fields at all.
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
from erp.sales.domain.models import (
    Customer,
    OrderStatus,
    PendingPayment,
    PendingPaymentStatus,
    Quotation,
    QuotationStatus,
    SalesOrder,
)
from erp.sales.services.orders import OrderLineInput
from erp.sales.services.pending_payments import create_pending_payment
from erp.sales.services.quotations import QuoteLineInput

from .. import grouping
from ..registry import (
    FieldSpec,
    Issue,
    batch_lookup_by_tagged_field,
    batch_lookup_code_or_name,
    register,
)
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

    def exists_many(self, actor, rows: list[dict]) -> list[Customer | None]:
        return batch_lookup_code_or_name(
            scope_queryset(actor, Customer.objects.all(), "sales.customer.view"), rows,
        )

    def existing_labels(self, actor):
        qs = scope_queryset(actor, Customer.objects.all(), "sales.customer.view")
        return list(qs.values_list("pk", "name"))


register(CustomerAdapter())


# --- sales quotations, sales orders, sales invoices (FILE_15 Task B) ------------------------------
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


class SalesQuotationAdapter:
    """Flat-Excel quotation sheets: one row per LINE, header fields repeated or filled only on the
    group's first row — same shape as ``SalesInvoiceAdapter``. Writes a DRAFT ``Quotation`` via
    ``contracts.create_quotation``; the model carries no tax fields, so unlike the order/invoice
    adapters there is no ``tax_token`` here. The quotation number is server-assigned
    (``QUO-YYYY-NNNNNN``), so the source file's number is kept in ``notes`` as
    ``"import:<doc_number>"`` — a different table than ``SalesOrder``, so no prefix clash with the
    other two sales adapters is possible.
    """

    entity = "sales_quotations"
    label_key = "imports.entity.salesQuotations"
    fields = [
        # --- header (one per document; blank on continuation rows of the same group) ---
        FieldSpec(
            name="doc_number", kind="text",
            synonyms_en=["quotation number", "quote number", "quote no"],
            synonyms_ar=["رقم عرض السعر", "رقم العرض"],
        ),
        FieldSpec(
            name="customer_ref", kind="ref", ref="customers",
            synonyms_en=["customer", "customer code", "customer name", "bill to"],
            synonyms_ar=["العميل", "كود العميل", "اسم العميل"],
        ),
        FieldSpec(
            name="date", kind="date",
            synonyms_en=["date", "quote date", "quotation date"],
            synonyms_ar=["التاريخ", "تاريخ العرض"],
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
            name="file_total_minor", kind="money",
            synonyms_en=["total", "grand total", "quote total"],
            synonyms_ar=["الإجمالي", "إجمالي العرض"],
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
    ]
    natural_key = ["doc_number"]
    group_by = "doc_number"
    header_fields = ["doc_number", "customer_ref", "date", "currency", "warehouse_ref", "file_total_minor"]

    @property
    def defaults(self) -> dict:
        return dict(getattr(settings, "IMPORTS_DEFAULTS", {}).get(self.entity, {}))

    def lookup(self, actor, field, value):
        if field == "customer_ref":
            return _find_customer(actor, value)
        if field == "item_ref":
            return inventory.find_item(value)
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
        doc_number = (group.get("doc_number") or "").strip()

        lines = [
            QuoteLineInput(
                item_sku=(line.get("item_ref") or "").strip(),
                quantity=Decimal(str(line["quantity"])),
                unit_price_minor=int(line["unit_price_minor"]),
            )
            for line in group["lines"]
        ]
        quote = contracts.create_quotation(
            customer=customer,
            warehouse_code=warehouse_code,
            lines=lines,
            quote_date=_as_date(group.get("date")) or _dt.date.today(),
            currency=group.get("currency") or self.defaults.get("currency", "EGP"),
            notes=f"import:{doc_number}",
            actor=actor,
        )

        warnings: list[Issue] = []
        mismatch = grouping.total_mismatch_issue(group.get("file_total_minor"), quote.subtotal_minor)
        if mismatch is not None:
            warnings.append(mismatch)
        return quote, warnings

    def exists(self, actor, group: dict):
        doc_number = (group.get("doc_number") or "").strip()
        if not doc_number:
            return None
        qs = scope_queryset(actor, Quotation.objects.all(), "sales.quotation.view")
        return qs.filter(notes=f"import:{doc_number}").first()

    def exists_many(self, actor, rows: list[dict]) -> list[Quotation | None]:
        qs = scope_queryset(actor, Quotation.objects.all(), "sales.quotation.view")
        return batch_lookup_by_tagged_field(qs, rows, prefix="import:")

    def delete(self, actor, pk) -> None:
        """Rollback support — see ``SalesInvoiceAdapter.delete``: a DRAFT quotation has posted
        nothing anywhere yet, so a plain delete is a true, side-effect-free reversal."""
        quote = Quotation.objects.filter(pk=pk).first()
        if quote is None:
            return  # already gone — rollback is idempotent
        if quote.status != QuotationStatus.DRAFT:
            raise ValueError(f"cannot delete quotation {quote.number}: status is {quote.status!r}, not draft")
        quote.delete()

    def existing_labels(self, actor):
        qs = scope_queryset(
            actor, Quotation.objects.filter(notes__startswith="import:"), "sales.quotation.view",
        )
        return list(qs.values_list("pk", "number"))


register(SalesQuotationAdapter())


class SalesOrderAdapter:
    """Flat-Excel order sheets: one row per LINE, same shape as ``SalesInvoiceAdapter`` — see that
    class's docstring for the "no distinct invoice document" reasoning, which applies here in
    reverse (this adapter is the "order" side of the same ``SalesOrder`` table). Both create a
    DRAFT ``SalesOrder`` via the identical ``contracts.create_order`` write-path; the only
    difference is the ``notes`` tag prefix (``import-so:`` here vs ``import:`` for
    ``SalesInvoiceAdapter``) so the two entities' natural-key matching never collides on rows the
    other one wrote.
    """

    entity = "sales_orders"
    label_key = "imports.entity.salesOrders"
    fields = [
        # --- header (one per document; blank on continuation rows of the same group) ---
        FieldSpec(
            name="doc_number", kind="text",
            synonyms_en=["order number", "order no", "order #"],
            synonyms_ar=["رقم الطلب", "رقم أمر البيع"],
        ),
        FieldSpec(
            name="customer_ref", kind="ref", ref="customers",
            synonyms_en=["customer", "customer code", "customer name", "bill to"],
            synonyms_ar=["العميل", "كود العميل", "اسم العميل"],
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
            notes=f"import-so:{doc_number}",
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
        qs = scope_queryset(actor, SalesOrder.objects.all(), "sales.order.view")
        return qs.filter(notes=f"import-so:{doc_number}").first()

    def exists_many(self, actor, rows: list[dict]) -> list[SalesOrder | None]:
        qs = scope_queryset(actor, SalesOrder.objects.all(), "sales.order.view")
        return batch_lookup_by_tagged_field(qs, rows, prefix="import-so:")

    def delete(self, actor, pk) -> None:
        """Rollback support — see ``SalesInvoiceAdapter.delete``: a DRAFT order has posted nothing
        anywhere yet, so a plain delete is a true, side-effect-free reversal."""
        order = SalesOrder.objects.filter(pk=pk).first()
        if order is None:
            return  # already gone — rollback is idempotent
        if order.status != OrderStatus.DRAFT:
            raise ValueError(f"cannot delete order {order.number}: status is {order.status!r}, not draft")
        order.delete()

    def existing_labels(self, actor):
        qs = scope_queryset(
            actor, SalesOrder.objects.filter(notes__startswith="import-so:"), "sales.order.view",
        )
        return list(qs.values_list("pk", "number"))


register(SalesOrderAdapter())


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
        mismatch = grouping.total_mismatch_issue(group.get("file_total_minor"), order.subtotal_minor)
        if mismatch is not None:
            warnings.append(mismatch)
        return order, warnings

    def exists(self, actor, group: dict):
        doc_number = (group.get("doc_number") or "").strip()
        if not doc_number:
            return None
        qs = scope_queryset(actor, SalesOrder.objects.all(), "sales.order.view")
        return qs.filter(notes=f"import:{doc_number}").first()

    def exists_many(self, actor, rows: list[dict]) -> list[SalesOrder | None]:
        qs = scope_queryset(actor, SalesOrder.objects.all(), "sales.order.view")
        return batch_lookup_by_tagged_field(qs, rows, prefix="import:")

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


# --- receipts (session 16b — PendingPayment, drafts-only) -----------------------------------------
def _find_order(actor, ref: str):
    """An existing SalesOrder by its ERP-native ``number`` (a human re-keying what they see on
    screen) or by the import-tag ``notes`` a prior document import left (``import:<doc>`` /
    ``import-so:<doc>`` — the source system's own invoice/order number, the common case for a
    cutover payments file)."""
    ref = (ref or "").strip()
    if not ref:
        return None
    qs = scope_queryset(actor, SalesOrder.objects.all(), "sales.order.view")
    return qs.filter(number=ref).first() or qs.filter(notes__in=[f"import:{ref}", f"import-so:{ref}"]).first()


_METHOD_TOKENS = {
    "cash": "cash", "نقدي": "cash", "نقدا": "cash",
    "transfer": "transfer", "bank transfer": "transfer", "تحويل": "transfer", "تحويل بنكي": "transfer",
    "cheque": "cheque", "check": "cheque", "شيك": "cheque",
}


def _normalize_method(value) -> str:
    token = str(value or "").strip().casefold()
    return _METHOD_TOKENS.get(token, "")


class ReceiptAdapter:
    """Customer receipts — always stages a ``sales.PendingPayment`` (drafts-only; see
    ``adapters/accounting.py`` for why the direct write-path ``receive_payment`` can't be used from
    an import). A resolvable ``order_ref`` pre-matches the row; otherwise it imports unmatched with
    a ``payment_unmatched`` warning (never blocks) — applying/matching is a human review-screen
    action (``erp.sales.services.pending_payments``), out of scope here.

    No natural key: a flat receipts file rarely carries a stable per-row id, so ``exists`` always
    returns ``None`` — every import run creates new pending rows. True duplicates are a human's call
    on the (future) review screen, same as any other data-entry double-check.
    """

    entity = "receipts"
    label_key = "imports.entity.receipts"
    fields = [
        FieldSpec(
            name="customer_ref", required=True, kind="ref", ref="customers",
            synonyms_en=["customer", "customer code", "customer name"],
            synonyms_ar=["العميل", "كود العميل", "اسم العميل"],
        ),
        FieldSpec(
            name="amount_minor", required=True, kind="money",
            synonyms_en=["amount", "payment amount", "received"],
            synonyms_ar=["المبلغ", "مبلغ الدفعة", "المحصل"],
        ),
        FieldSpec(
            name="date", required=True, kind="date",
            synonyms_en=["date", "payment date", "received date"],
            synonyms_ar=["التاريخ", "تاريخ الدفعة"],
        ),
        FieldSpec(
            name="method", kind="text",
            synonyms_en=["method", "payment method"],
            synonyms_ar=["طريقة الدفع", "الطريقة"],
        ),
        # Deliberately NOT kind="ref" — an unresolved order must import unmatched (warning), never
        # trigger the missing_ref/auto-create-master flow (there's nothing sane to auto-create for
        # a stray invoice number).
        FieldSpec(
            name="order_ref", kind="text",
            synonyms_en=["invoice number", "invoice ref", "order number"],
            synonyms_ar=["رقم الفاتورة", "رقم الطلب"],
        ),
    ]
    natural_key = []
    group_by = None

    @property
    def defaults(self) -> dict:
        return dict(getattr(settings, "IMPORTS_DEFAULTS", {}).get(self.entity, {}))

    def lookup(self, actor, field, value):
        if field == "customer_ref":
            return _find_customer(actor, value)
        return None

    def validate(self, actor, row: dict) -> list[Issue]:
        return []

    def write(self, actor, row: dict):
        require_role(actor, BRANCH_MANAGER)
        customer = _find_customer(actor, row.get("customer_ref"))
        order = _find_order(actor, row.get("order_ref"))
        pending = create_pending_payment(
            order=order,
            party_code=customer.code if customer else (row.get("customer_ref") or "").strip(),
            amount_minor=int(row["amount_minor"]),
            date=_as_date(row.get("date")) or _dt.date.today(),
            method=_normalize_method(row.get("method")),
            source="import",
            actor=actor,
        )
        if order is None:
            return pending, [Issue(
                field="order_ref", code="payment_unmatched", message="imports.issues.paymentUnmatched",
                meta={"customer_ref": row.get("customer_ref"), "order_ref": row.get("order_ref")},
            )]
        return pending

    def exists(self, actor, row: dict):
        return None

    def existing_labels(self, actor):
        return []

    def delete(self, actor, pk) -> None:
        """Rollback support: a still-PENDING row has posted nothing anywhere, so a plain delete is
        a true reversal. Refuses once applied/discarded — never deletes a row a human already
        acted on."""
        pending = PendingPayment.objects.filter(pk=pk).first()
        if pending is None:
            return
        if pending.status != PendingPaymentStatus.PENDING:
            raise ValueError(f"cannot delete pending payment {pending.pk}: status is {pending.status!r}, not pending")
        pending.delete()


register(ReceiptAdapter())
