"""Inventory API views — thin: validate, resolve refs, delegate to services, return {data}.

RBAC: inventory operations require a Branch Manager (System Admin / superuser bypass).
"""
from __future__ import annotations

from dataclasses import asdict

from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from erp.identity.permissions import HasAnyRole
from erp.identity.roles import BRANCH_MANAGER

from .. import services
from ..domain.models import Category, Item, StockMovement, Warehouse
from ..repositories import items as item_repo
from ..repositories import warehouses as warehouse_repo
from .serializers import (
    CategorySerializer,
    IssueSerializer,
    ItemSerializer,
    MovementSerializer,
    ReceiveSerializer,
    TransferSerializer,
    WarehouseSerializer,
)

_CanStock = HasAnyRole.require(BRANCH_MANAGER)


def _envelope(data, status: int = 200) -> Response:
    return Response({"data": data}, status=status)


class ItemListCreateView(APIView):
    permission_classes = [IsAuthenticated, _CanStock]

    def get(self, request: Request) -> Response:
        return _envelope(ItemSerializer(Item.objects.select_related("category"), many=True).data)

    def post(self, request: Request) -> Response:
        s = ItemSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        v = s.validated_data
        category = None
        if v.get("category_code"):
            category = Category.objects.filter(code=v["category_code"]).first()
        item = Item.objects.create(
            sku=v["sku"], name=v["name"], category=category,
            uom=v.get("uom", "unit"), type=v.get("type", "stock"),
            is_active=v.get("is_active", True), reorder_point=v.get("reorder_point", 0),
            created_by=request.user if request.user.is_authenticated else None,
        )
        return _envelope(ItemSerializer(item).data, status=201)


class CategoryListCreateView(APIView):
    permission_classes = [IsAuthenticated, _CanStock]

    def get(self, request: Request) -> Response:
        return _envelope(CategorySerializer(Category.objects.all(), many=True).data)

    def post(self, request: Request) -> Response:
        s = CategorySerializer(data=request.data)
        s.is_valid(raise_exception=True)
        cat = Category.objects.create(code=s.validated_data["code"], name=s.validated_data["name"])
        return _envelope(CategorySerializer(cat).data, status=201)


class WarehouseListCreateView(APIView):
    permission_classes = [IsAuthenticated, _CanStock]

    def get(self, request: Request) -> Response:
        return _envelope(WarehouseSerializer(Warehouse.objects.all(), many=True).data)

    def post(self, request: Request) -> Response:
        s = WarehouseSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        wh = Warehouse.objects.create(
            code=s.validated_data["code"], name=s.validated_data["name"],
            is_active=s.validated_data.get("is_active", True),
            created_by=request.user if request.user.is_authenticated else None,
        )
        return _envelope(WarehouseSerializer(wh).data, status=201)


class ReceiveView(APIView):
    permission_classes = [IsAuthenticated, _CanStock]

    def post(self, request: Request) -> Response:
        s = ReceiveSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        v = s.validated_data
        item = get_object_or_404(Item, sku=v["item_sku"])
        warehouse = get_object_or_404(Warehouse, code=v["warehouse_code"])
        movement = services.receive_stock(
            item=item, warehouse=warehouse, quantity=v["quantity"],
            unit_cost_minor=v["unit_cost"], date=v.get("date"),
            reference=v.get("reference", ""), memo=v.get("memo", ""), actor=request.user,
        )
        return _envelope(MovementSerializer(movement).data, status=201)


class IssueView(APIView):
    permission_classes = [IsAuthenticated, _CanStock]

    def post(self, request: Request) -> Response:
        s = IssueSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        v = s.validated_data
        item = get_object_or_404(Item, sku=v["item_sku"])
        warehouse = get_object_or_404(Warehouse, code=v["warehouse_code"])
        movement = services.issue_stock(
            item=item, warehouse=warehouse, quantity=v["quantity"], date=v.get("date"),
            reference=v.get("reference", ""), memo=v.get("memo", ""), actor=request.user,
        )
        return _envelope(MovementSerializer(movement).data, status=201)


class TransferView(APIView):
    permission_classes = [IsAuthenticated, _CanStock]

    def post(self, request: Request) -> Response:
        s = TransferSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        v = s.validated_data
        item = get_object_or_404(Item, sku=v["item_sku"])
        source = get_object_or_404(Warehouse, code=v["source_code"])
        destination = get_object_or_404(Warehouse, code=v["dest_code"])
        movement = services.transfer_stock(
            item=item, source=source, destination=destination, quantity=v["quantity"],
            date=v.get("date"), reference=v.get("reference", ""), memo=v.get("memo", ""),
            actor=request.user,
        )
        return _envelope(MovementSerializer(movement).data, status=201)


class MovementListView(APIView):
    permission_classes = [IsAuthenticated, _CanStock]

    def get(self, request: Request) -> Response:
        qs = StockMovement.objects.select_related("item", "warehouse", "dest_warehouse").order_by(
            "-date", "-created_at"
        )
        if request.query_params.get("item"):
            qs = qs.filter(item__sku=request.query_params["item"])
        return _envelope(MovementSerializer(qs[:200], many=True).data)


class StockOnHandView(APIView):
    permission_classes = [IsAuthenticated, _CanStock]

    def get(self, request: Request) -> Response:
        report = services.stock_on_hand(
            item_sku=request.query_params.get("item") or None,
            warehouse_code=request.query_params.get("warehouse") or None,
        )
        return _envelope(
            {
                "rows": [asdict(r) for r in report.rows],
                "total_value_minor": report.total_value_minor,
            }
        )
