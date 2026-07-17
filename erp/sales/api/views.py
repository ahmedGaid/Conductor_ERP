"""Sales API views — thin: validate, delegate to services, return {data}.

RBAC: sales operations require a Branch Manager (System Admin / superuser bypass).
"""
from __future__ import annotations

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from erp.audit import services as audit
from erp.audit.history import order_history
from erp.core.custom_fields import custom_field_columns, validate_custom_data
from erp.core.exports import EXPORT_FORMATS, Column, ReportTable, export_response
from erp.core.import_api import run_import_request, template_response
from erp.identity.permissions import HasAnyRole
from erp.identity.roles import BRANCH_MANAGER
from erp.identity.scoping import scope_queryset

from .. import services
from ..domain.models import Customer, Quotation, SalesOrder
from ..imports import CUSTOMER_IMPORT
from ..repositories import customers as customer_repo
from .serializers import (
    CustomerSerializer,
    LinesActionSerializer,
    OrderCreateSerializer,
    OrderSerializer,
    PaymentSerializer,
    QuotationCreateSerializer,
    QuotationSerializer,
    RejectSerializer,
)

_CanSell = HasAnyRole.require(BRANCH_MANAGER)


def _envelope(data, status: int = 200) -> Response:
    return Response({"data": data}, status=status)


def _order_qs():
    return SalesOrder.objects.select_related("customer").prefetch_related("lines")


# List/detail and action fetches share the scoped queryset, so an out-of-scope order 404s
# (indistinguishable from absent) rather than leaking existence. Actions pass the bare model:
# the prefetched `lines` cache would go stale once the service mutates them.
def _scoped_orders(request: Request, base=None):
    return scope_queryset(request.user, base if base is not None else _order_qs(), "sales.order.view")


def _customer_export_table(qs, lang: str) -> ReportTable:
    extra = custom_field_columns("sales.customer", lang)
    cols = [
        Column("code", "الكود" if lang == "ar" else "Code"),
        Column("name", "الاسم" if lang == "ar" else "Name"),
        Column("credit_limit_minor", "حد الائتمان" if lang == "ar" else "Credit limit",
               kind="money", align="end"),
        Column("is_active", "نشط" if lang == "ar" else "Active"),
        *extra,
    ]
    rows = []
    for c in qs:
        row = {
            "code": c.code, "name": c.name, "credit_limit_minor": c.credit_limit_minor,
            "is_active": ("نعم" if lang == "ar" else "Yes") if c.is_active else ("لا" if lang == "ar" else "No"),
        }
        row.update({col.key: c.custom_data.get(col.key, "") for col in extra})
        rows.append(row)
    return ReportTable(title="العملاء" if lang == "ar" else "Customers",
                       columns=cols, rows=rows, rtl=(lang == "ar"))


class CustomerListCreateView(APIView):
    permission_classes = [IsAuthenticated, _CanSell]

    def get(self, request: Request) -> Response:
        qs = Customer.objects.all()
        fmt = request.query_params.get("export")
        if fmt in EXPORT_FORMATS:
            table = _customer_export_table(qs, request.query_params.get("lang", "en"))
            return export_response(table, fmt, "customers")
        return _envelope(CustomerSerializer(qs, many=True).data)

    def post(self, request: Request) -> Response:
        s = CustomerSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        v = s.validated_data
        custom_data = validate_custom_data("sales.customer", v.get("custom_data"))
        customer = Customer.objects.create(
            code=v["code"], name=v["name"],
            credit_limit_minor=v.get("credit_limit_minor", 0),
            is_active=v.get("is_active", True),
            custom_data=custom_data,
            created_by=request.user if request.user.is_authenticated else None,
        )
        audit.record(
            module="sales", action="create_customer", entity_type="Customer",
            entity_id=customer.code, actor=request.user,
            after={"code": customer.code, "name": customer.name, "custom_data": customer.custom_data},
        )
        return _envelope(CustomerSerializer(customer).data, status=201)


class CustomerImportView(APIView):
    """CSV import for customers — upload to preview, re-post with commit=true to apply.

    Multipart fields: ``file`` (CSV), optional ``mapping`` (JSON {field: source_header}),
    ``mode`` (create | upsert, default create), ``commit`` (bool, default false = preview).
    Preview and commit run the same engine path, so the preview is exactly what commit will do.
    """

    permission_classes = [IsAuthenticated, _CanSell]

    def post(self, request: Request) -> Response:
        return _envelope(run_import_request(CUSTOMER_IMPORT, request))


class CustomerImportTemplateView(APIView):
    """Download a CSV template (canonical headers + one example row) so columns are obvious."""

    permission_classes = [IsAuthenticated, _CanSell]

    def get(self, request: Request) -> HttpResponse:
        return template_response(CUSTOMER_IMPORT, "customers-template.csv")


class OrderListCreateView(APIView):
    permission_classes = [IsAuthenticated, _CanSell]

    def get(self, request: Request) -> Response:
        qs = _scoped_orders(request).order_by("-order_date", "-created_at")
        if request.query_params.get("status"):
            qs = qs.filter(status=request.query_params["status"])
        if request.query_params.get("customer"):
            qs = qs.filter(customer__code=request.query_params["customer"])
        return _envelope(OrderSerializer(qs[:200], many=True).data)

    def post(self, request: Request) -> Response:
        s = OrderCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        v = s.validated_data
        customer = get_object_or_404(Customer, code=v["customer_code"])
        order = services.create_order(
            customer=customer,
            warehouse_code=v["warehouse_code"],
            order_date=v.get("order_date"),
            currency=v.get("currency", "EGP"),
            notes=v.get("notes", ""),
            tax_code=v.get("tax_code", ""),
            lines=[
                services.OrderLineInput(
                    item_sku=ln["item_sku"], quantity=ln["quantity"],
                    unit_price_minor=ln["unit_price"], description=ln.get("description", ""),
                    discount_minor=ln.get("discount", 0),
                )
                for ln in v["lines"]
            ],
            actor=request.user,
        )
        return _envelope(OrderSerializer(_order_qs().get(id=order.id)).data, status=201)


class OrderDetailView(APIView):
    permission_classes = [IsAuthenticated, _CanSell]

    def get(self, request: Request, order_id) -> Response:
        return _envelope(OrderSerializer(get_object_or_404(_scoped_orders(request), id=order_id)).data)


# Audit action → workflow tracker stage key (see apps/web/src/lib/workflow.ts). Approval gates the
# confirm stage, so it shares it; a return is the lifecycle's exception stage.
_SALES_STAGE = {
    "create_order": "create",
    "approve_order": "confirm",
    "confirm_order": "confirm",
    "deliver_order": "deliver",
    "invoice_order": "invoice",
    "receive_payment": "payment",
    "return_order": "returned",
}


class OrderHistoryView(APIView):
    """Lifecycle of one order: who reached each stage, when, and the order's snapshot at that point."""

    permission_classes = [IsAuthenticated, _CanSell]

    def get(self, request: Request, order_id) -> Response:
        order = get_object_or_404(_scoped_orders(request, SalesOrder.objects.all()), id=order_id)
        return _envelope(order_history("SalesOrder", order.number, _SALES_STAGE))


class _OrderActionView(APIView):
    permission_classes = [IsAuthenticated, _CanSell]
    action = ""

    def post(self, request: Request, order_id) -> Response:
        order = get_object_or_404(_scoped_orders(request, SalesOrder.objects.all()), id=order_id)
        fn = getattr(services, self.action)
        fn(order, actor=request.user)
        return _envelope(OrderSerializer(_order_qs().get(id=order.id)).data)


class OrderApproveView(_OrderActionView):
    action = "approve_order"


class OrderConfirmView(_OrderActionView):
    action = "confirm_order"


class OrderInvoiceView(_OrderActionView):
    action = "invoice_order"


class OrderCancelView(_OrderActionView):
    action = "cancel_order"


class OrderCompleteView(_OrderActionView):
    """Fast-path the counter sale: confirm → deliver → invoice in one move (additive shortcut)."""

    action = "complete_sale"


class OrderDeliverView(APIView):
    permission_classes = [IsAuthenticated, _CanSell]

    def post(self, request: Request, order_id) -> Response:
        order = get_object_or_404(_scoped_orders(request, SalesOrder.objects.all()), id=order_id)
        s = LinesActionSerializer(data=request.data or {})
        s.is_valid(raise_exception=True)
        services.deliver_order(order, delivered=s.as_map(), actor=request.user)
        return _envelope(OrderSerializer(_order_qs().get(id=order.id)).data)


class OrderReturnView(APIView):
    permission_classes = [IsAuthenticated, _CanSell]

    def post(self, request: Request, order_id) -> Response:
        order = get_object_or_404(_scoped_orders(request, SalesOrder.objects.all()), id=order_id)
        s = LinesActionSerializer(data=request.data or {})
        s.is_valid(raise_exception=True)
        services.return_order(order, returned=s.as_map(), actor=request.user)
        return _envelope(OrderSerializer(_order_qs().get(id=order.id)).data)


class OrderPaymentView(APIView):
    permission_classes = [IsAuthenticated, _CanSell]

    def post(self, request: Request, order_id) -> Response:
        order = get_object_or_404(_scoped_orders(request, SalesOrder.objects.all()), id=order_id)
        s = PaymentSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        services.receive_payment(order, s.validated_data["amount"], actor=request.user)
        return _envelope(OrderSerializer(_order_qs().get(id=order.id)).data)


# --- Quotations ------------------------------------------------------------------------------

def _quote_qs():
    return Quotation.objects.select_related("customer").prefetch_related("lines")


def _scoped_quotes(request: Request, base=None):
    return scope_queryset(request.user, base if base is not None else _quote_qs(),
                          "sales.quotation.view")


class QuotationListCreateView(APIView):
    permission_classes = [IsAuthenticated, _CanSell]

    def get(self, request: Request) -> Response:
        qs = _scoped_quotes(request).order_by("-quote_date", "-created_at")
        if request.query_params.get("status"):
            qs = qs.filter(status=request.query_params["status"])
        return _envelope(QuotationSerializer(qs[:200], many=True).data)

    def post(self, request: Request) -> Response:
        s = QuotationCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        v = s.validated_data
        customer = get_object_or_404(Customer, code=v["customer_code"])
        quote = services.create_quotation(
            customer=customer, warehouse_code=v["warehouse_code"],
            quote_date=v.get("quote_date"), currency=v.get("currency", "EGP"),
            notes=v.get("notes", ""),
            lines=[
                services.QuoteLineInput(
                    item_sku=ln["item_sku"], quantity=ln["quantity"],
                    unit_price_minor=ln["unit_price"], description=ln.get("description", ""),
                )
                for ln in v["lines"]
            ],
            actor=request.user,
        )
        return _envelope(QuotationSerializer(_quote_qs().get(id=quote.id)).data, status=201)


class QuotationDetailView(APIView):
    permission_classes = [IsAuthenticated, _CanSell]

    def get(self, request: Request, quote_id) -> Response:
        return _envelope(QuotationSerializer(get_object_or_404(_scoped_quotes(request), id=quote_id)).data)


class _QuotationActionView(APIView):
    permission_classes = [IsAuthenticated, _CanSell]
    action = ""

    def post(self, request: Request, quote_id) -> Response:
        quote = get_object_or_404(_scoped_quotes(request, Quotation.objects.all()), id=quote_id)
        getattr(services, self.action)(quote, actor=request.user)
        return _envelope(QuotationSerializer(_quote_qs().get(id=quote.id)).data)


class QuotationSubmitView(_QuotationActionView):
    action = "submit_quotation"


class QuotationApproveView(_QuotationActionView):
    action = "approve_quotation"


class QuotationRejectView(APIView):
    permission_classes = [IsAuthenticated, _CanSell]

    def post(self, request: Request, quote_id) -> Response:
        quote = get_object_or_404(_scoped_quotes(request, Quotation.objects.all()), id=quote_id)
        s = RejectSerializer(data=request.data or {})
        s.is_valid(raise_exception=True)
        services.reject_quotation(quote, reason=s.validated_data.get("reason", ""), actor=request.user)
        return _envelope(QuotationSerializer(_quote_qs().get(id=quote.id)).data)


class QuotationConvertView(APIView):
    permission_classes = [IsAuthenticated, _CanSell]

    def post(self, request: Request, quote_id) -> Response:
        quote = get_object_or_404(_scoped_quotes(request, Quotation.objects.all()), id=quote_id)
        order = services.convert_quotation(quote, actor=request.user)
        return _envelope(
            {"quotation": QuotationSerializer(_quote_qs().get(id=quote.id)).data,
             "order_id": str(order.id), "order_number": order.number},
            status=201,
        )
