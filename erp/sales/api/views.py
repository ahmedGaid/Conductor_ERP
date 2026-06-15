"""Sales API views — thin: validate, delegate to services, return {data}.

RBAC: sales operations require a Branch Manager (System Admin / superuser bypass).
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
from ..domain.models import Customer, SalesOrder
from ..repositories import customers as customer_repo
from .serializers import (
    CustomerSerializer,
    OrderCreateSerializer,
    OrderSerializer,
    PaymentSerializer,
)

_CanSell = HasAnyRole.require(BRANCH_MANAGER)


def _envelope(data, status: int = 200) -> Response:
    return Response({"data": data}, status=status)


def _order_qs():
    return SalesOrder.objects.select_related("customer").prefetch_related("lines")


class CustomerListCreateView(APIView):
    permission_classes = [IsAuthenticated, _CanSell]

    def get(self, request: Request) -> Response:
        return _envelope(CustomerSerializer(Customer.objects.all(), many=True).data)

    def post(self, request: Request) -> Response:
        s = CustomerSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        v = s.validated_data
        customer = Customer.objects.create(
            code=v["code"], name=v["name"],
            credit_limit_minor=v.get("credit_limit_minor", 0),
            is_active=v.get("is_active", True),
            created_by=request.user if request.user.is_authenticated else None,
        )
        return _envelope(CustomerSerializer(customer).data, status=201)


class OrderListCreateView(APIView):
    permission_classes = [IsAuthenticated, _CanSell]

    def get(self, request: Request) -> Response:
        qs = _order_qs().order_by("-order_date", "-created_at")
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
            lines=[
                services.OrderLineInput(
                    item_sku=ln["item_sku"], quantity=ln["quantity"],
                    unit_price_minor=ln["unit_price"], description=ln.get("description", ""),
                )
                for ln in v["lines"]
            ],
            actor=request.user,
        )
        return _envelope(OrderSerializer(_order_qs().get(id=order.id)).data, status=201)


class OrderDetailView(APIView):
    permission_classes = [IsAuthenticated, _CanSell]

    def get(self, request: Request, order_id) -> Response:
        return _envelope(OrderSerializer(get_object_or_404(_order_qs(), id=order_id)).data)


class _OrderActionView(APIView):
    permission_classes = [IsAuthenticated, _CanSell]
    action = ""

    def post(self, request: Request, order_id) -> Response:
        order = get_object_or_404(SalesOrder, id=order_id)
        fn = getattr(services, self.action)
        fn(order, actor=request.user)
        return _envelope(OrderSerializer(_order_qs().get(id=order.id)).data)


class OrderConfirmView(_OrderActionView):
    action = "confirm_order"


class OrderDeliverView(_OrderActionView):
    action = "deliver_order"


class OrderInvoiceView(_OrderActionView):
    action = "invoice_order"


class OrderPaymentView(APIView):
    permission_classes = [IsAuthenticated, _CanSell]

    def post(self, request: Request, order_id) -> Response:
        order = get_object_or_404(SalesOrder, id=order_id)
        s = PaymentSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        services.receive_payment(order, s.validated_data["amount"], actor=request.user)
        return _envelope(OrderSerializer(_order_qs().get(id=order.id)).data)
