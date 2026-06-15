"""Purchasing API views — thin: validate, delegate to services, return {data}.

RBAC: purchasing operations require a Branch Manager (System Admin / superuser bypass).
"""
from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from erp.identity.permissions import HasAnyRole
from erp.identity.roles import BRANCH_MANAGER

from .. import services
from ..domain.models import PurchaseOrder, Supplier
from .serializers import (
    POCreateSerializer,
    POSerializer,
    PaymentSerializer,
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


class POListCreateView(APIView):
    permission_classes = [IsAuthenticated, _CanBuy]

    def get(self, request: Request) -> Response:
        qs = _po_qs().order_by("-order_date", "-created_at")
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
            notes=v.get("notes", ""),
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


class POConfirmView(_POActionView):
    action = "confirm_order"


class POReceiveView(_POActionView):
    action = "receive_order"


class POBillView(_POActionView):
    action = "bill_order"


class POPaymentView(APIView):
    permission_classes = [IsAuthenticated, _CanBuy]

    def post(self, request: Request, order_id) -> Response:
        order = get_object_or_404(PurchaseOrder, id=order_id)
        s = PaymentSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        services.pay_order(order, s.validated_data["amount"], actor=request.user)
        return _envelope(POSerializer(_po_qs().get(id=order.id)).data)
