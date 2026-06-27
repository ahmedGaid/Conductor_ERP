"""Purchasing API views — thin: validate, delegate to services, return {data}.

RBAC: purchasing operations require a Branch Manager (System Admin / superuser bypass).
"""
from __future__ import annotations

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from erp.core.import_api import run_import_request, template_response
from erp.identity.permissions import HasAnyRole
from erp.identity.roles import BRANCH_MANAGER
from erp.identity.scoping import scope_queryset

from .. import services
from ..domain.models import PurchaseOrder, PurchaseRequest, Supplier
from ..imports import SUPPLIER_IMPORT
from .serializers import (
    LinesActionSerializer,
    POCreateSerializer,
    POSerializer,
    PaymentSerializer,
    RejectSerializer,
    RequestCreateSerializer,
    RequestSerializer,
    SupplierSerializer,
)

_CanBuy = HasAnyRole.require(BRANCH_MANAGER)


def _envelope(data, status: int = 200) -> Response:
    return Response({"data": data}, status=status)


def _po_qs():
    return PurchaseOrder.objects.select_related("supplier").prefetch_related("lines")


class SupplierListCreateView(APIView):
    permission_classes = [IsAuthenticated, _CanBuy]

    def get(self, request: Request) -> Response:
        return _envelope(SupplierSerializer(Supplier.objects.all(), many=True).data)

    def post(self, request: Request) -> Response:
        s = SupplierSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        v = s.validated_data
        supplier = Supplier.objects.create(
            code=v["code"], name=v["name"], is_active=v.get("is_active", True),
            created_by=request.user if request.user.is_authenticated else None,
        )
        return _envelope(SupplierSerializer(supplier).data, status=201)


class SupplierImportView(APIView):
    """CSV import for suppliers — upload to preview, re-post with commit=true to apply."""

    permission_classes = [IsAuthenticated, _CanBuy]

    def post(self, request: Request) -> Response:
        return _envelope(run_import_request(SUPPLIER_IMPORT, request))


class SupplierImportTemplateView(APIView):
    """Download a CSV template (canonical headers + one example row) so columns are obvious."""

    permission_classes = [IsAuthenticated, _CanBuy]

    def get(self, request: Request) -> HttpResponse:
        return template_response(SUPPLIER_IMPORT, "suppliers-template.csv")


class POListCreateView(APIView):
    permission_classes = [IsAuthenticated, _CanBuy]

    def get(self, request: Request) -> Response:
        qs = _po_qs().order_by("-order_date", "-created_at")
        qs = scope_queryset(request.user, qs, "purchasing.order.view")
        if request.query_params.get("status"):
            qs = qs.filter(status=request.query_params["status"])
        if request.query_params.get("supplier"):
            qs = qs.filter(supplier__code=request.query_params["supplier"])
        return _envelope(POSerializer(qs[:200], many=True).data)

    def post(self, request: Request) -> Response:
        s = POCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        v = s.validated_data
        supplier = get_object_or_404(Supplier, code=v["supplier_code"])
        order = services.create_order(
            supplier=supplier, warehouse_code=v["warehouse_code"],
            order_date=v.get("order_date"), currency=v.get("currency", "EGP"),
            tax_code=v.get("tax_code", ""), notes=v.get("notes", ""),
            lines=[
                services.POLineInput(
                    item_sku=ln["item_sku"], quantity=ln["quantity"],
                    unit_cost_minor=ln["unit_cost"], description=ln.get("description", ""),
                )
                for ln in v["lines"]
            ],
            actor=request.user,
        )
        return _envelope(POSerializer(_po_qs().get(id=order.id)).data, status=201)


class PODetailView(APIView):
    permission_classes = [IsAuthenticated, _CanBuy]

    def get(self, request: Request, order_id) -> Response:
        return _envelope(POSerializer(get_object_or_404(_po_qs(), id=order_id)).data)


class _POActionView(APIView):
    permission_classes = [IsAuthenticated, _CanBuy]
    action = ""

    def post(self, request: Request, order_id) -> Response:
        order = get_object_or_404(PurchaseOrder, id=order_id)
        getattr(services, self.action)(order, actor=request.user)
        return _envelope(POSerializer(_po_qs().get(id=order.id)).data)


class POApproveView(_POActionView):
    action = "approve_order"


class POConfirmView(_POActionView):
    action = "confirm_order"


class POBillView(_POActionView):
    action = "bill_order"


class POReceiveView(APIView):
    permission_classes = [IsAuthenticated, _CanBuy]

    def post(self, request: Request, order_id) -> Response:
        order = get_object_or_404(PurchaseOrder, id=order_id)
        s = LinesActionSerializer(data=request.data or {})
        s.is_valid(raise_exception=True)
        services.receive_order(order, received=s.as_map(), actor=request.user)
        return _envelope(POSerializer(_po_qs().get(id=order.id)).data)


class POReturnView(APIView):
    permission_classes = [IsAuthenticated, _CanBuy]

    def post(self, request: Request, order_id) -> Response:
        order = get_object_or_404(PurchaseOrder, id=order_id)
        s = LinesActionSerializer(data=request.data or {})
        s.is_valid(raise_exception=True)
        services.return_order(order, returned=s.as_map(), actor=request.user)
        return _envelope(POSerializer(_po_qs().get(id=order.id)).data)


class POPaymentView(APIView):
    permission_classes = [IsAuthenticated, _CanBuy]

    def post(self, request: Request, order_id) -> Response:
        order = get_object_or_404(PurchaseOrder, id=order_id)
        s = PaymentSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        services.pay_order(order, s.validated_data["amount"], actor=request.user)
        return _envelope(POSerializer(_po_qs().get(id=order.id)).data)


# --- Purchase requests -----------------------------------------------------------------------

def _req_qs():
    return PurchaseRequest.objects.select_related("supplier").prefetch_related("lines")


class RequestListCreateView(APIView):
    permission_classes = [IsAuthenticated, _CanBuy]

    def get(self, request: Request) -> Response:
        qs = _req_qs().order_by("-request_date", "-created_at")
        qs = scope_queryset(request.user, qs, "purchasing.request.view")
        if request.query_params.get("status"):
            qs = qs.filter(status=request.query_params["status"])
        return _envelope(RequestSerializer(qs[:200], many=True).data)

    def post(self, request: Request) -> Response:
        s = RequestCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        v = s.validated_data
        supplier = get_object_or_404(Supplier, code=v["supplier_code"])
        req = services.create_request(
            supplier=supplier, warehouse_code=v["warehouse_code"],
            request_date=v.get("request_date"), currency=v.get("currency", "EGP"),
            notes=v.get("notes", ""),
            lines=[
                services.RequestLineInput(
                    item_sku=ln["item_sku"], quantity=ln["quantity"],
                    unit_cost_minor=ln["unit_cost"], description=ln.get("description", ""),
                )
                for ln in v["lines"]
            ],
            actor=request.user,
        )
        return _envelope(RequestSerializer(_req_qs().get(id=req.id)).data, status=201)


class RequestDetailView(APIView):
    permission_classes = [IsAuthenticated, _CanBuy]

    def get(self, request: Request, req_id) -> Response:
        return _envelope(RequestSerializer(get_object_or_404(_req_qs(), id=req_id)).data)


class _RequestActionView(APIView):
    permission_classes = [IsAuthenticated, _CanBuy]
    action = ""

    def post(self, request: Request, req_id) -> Response:
        req = get_object_or_404(PurchaseRequest, id=req_id)
        getattr(services, self.action)(req, actor=request.user)
        return _envelope(RequestSerializer(_req_qs().get(id=req.id)).data)


class RequestSubmitView(_RequestActionView):
    action = "submit_request"


class RequestApproveView(_RequestActionView):
    action = "approve_request"


class RequestRejectView(APIView):
    permission_classes = [IsAuthenticated, _CanBuy]

    def post(self, request: Request, req_id) -> Response:
        req = get_object_or_404(PurchaseRequest, id=req_id)
        s = RejectSerializer(data=request.data or {})
        s.is_valid(raise_exception=True)
        services.reject_request(req, reason=s.validated_data.get("reason", ""), actor=request.user)
        return _envelope(RequestSerializer(_req_qs().get(id=req.id)).data)


class RequestConvertView(APIView):
    permission_classes = [IsAuthenticated, _CanBuy]

    def post(self, request: Request, req_id) -> Response:
        req = get_object_or_404(PurchaseRequest, id=req_id)
        order = services.convert_request(req, actor=request.user)
        return _envelope(
            {"request": RequestSerializer(_req_qs().get(id=req.id)).data,
             "order_id": str(order.id), "order_number": order.number},
            status=201,
        )
