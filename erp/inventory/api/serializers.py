"""Inventory API serializers. Quantities are decimals; costs/values are integer minor units."""
from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers

from ..domain.models import ItemType


class CategorySerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    code = serializers.CharField(max_length=32)
    name = serializers.CharField(max_length=200)


class ItemSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    sku = serializers.CharField(max_length=64)
    name = serializers.CharField(max_length=200)
    category_code = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    uom = serializers.CharField(max_length=16, required=False, default="unit")
    type = serializers.ChoiceField(choices=ItemType.choices, required=False, default=ItemType.STOCK)
    is_active = serializers.BooleanField(required=False, default=True)
    reorder_point = serializers.DecimalField(max_digits=18, decimal_places=4, required=False, default=0)

    def to_representation(self, obj) -> dict:
        return {
            "id": str(obj.id),
            "sku": obj.sku,
            "name": obj.name,
            "category_code": obj.category.code if obj.category_id else None,
            "uom": obj.uom,
            "type": obj.type,
            "is_active": obj.is_active,
            "reorder_point": str(obj.reorder_point),
        }


class WarehouseSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    code = serializers.CharField(max_length=32)
    name = serializers.CharField(max_length=200)
    is_active = serializers.BooleanField(required=False, default=True)

    def to_representation(self, obj) -> dict:
        return {
            "id": str(obj.id),
            "code": obj.code,
            "name": obj.name,
            "is_active": obj.is_active,
        }


class ReceiveSerializer(serializers.Serializer):
    item_sku = serializers.CharField()
    warehouse_code = serializers.CharField()
    quantity = serializers.DecimalField(max_digits=18, decimal_places=4)
    unit_cost = serializers.IntegerField(min_value=0)  # minor units
    date = serializers.DateField(required=False)
    reference = serializers.CharField(required=False, allow_blank=True, default="")
    memo = serializers.CharField(required=False, allow_blank=True, default="")
    batch_no = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")
    expiry_date = serializers.DateField(required=False, allow_null=True)


class StockCountCreateSerializer(serializers.Serializer):
    warehouse_code = serializers.CharField()
    count_date = serializers.DateField(required=False)
    reference = serializers.CharField(required=False, allow_blank=True, default="")
    memo = serializers.CharField(required=False, allow_blank=True, default="")
    item_skus = serializers.ListField(child=serializers.CharField(), required=False, default=list)


class CountLineSetSerializer(serializers.Serializer):
    counted_quantity = serializers.DecimalField(max_digits=18, decimal_places=4, min_value=Decimal("0"))


class IssueSerializer(serializers.Serializer):
    item_sku = serializers.CharField()
    warehouse_code = serializers.CharField()
    quantity = serializers.DecimalField(max_digits=18, decimal_places=4)
    date = serializers.DateField(required=False)
    reference = serializers.CharField(required=False, allow_blank=True, default="")
    memo = serializers.CharField(required=False, allow_blank=True, default="")


class TransferSerializer(serializers.Serializer):
    item_sku = serializers.CharField()
    source_code = serializers.CharField()
    dest_code = serializers.CharField()
    quantity = serializers.DecimalField(max_digits=18, decimal_places=4)
    date = serializers.DateField(required=False)
    reference = serializers.CharField(required=False, allow_blank=True, default="")
    memo = serializers.CharField(required=False, allow_blank=True, default="")


class MovementSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    type = serializers.CharField()
    item_sku = serializers.SerializerMethodField()
    warehouse_code = serializers.SerializerMethodField()
    dest_warehouse_code = serializers.SerializerMethodField()
    date = serializers.DateField()
    quantity = serializers.DecimalField(max_digits=18, decimal_places=4)
    unit_cost_minor = serializers.IntegerField()
    value_minor = serializers.IntegerField()
    reference = serializers.CharField()
    memo = serializers.CharField()
    batch_no = serializers.CharField()
    expiry_date = serializers.DateField(allow_null=True)
    journal_number = serializers.CharField()

    def get_item_sku(self, obj) -> str:
        return obj.item.sku

    def get_warehouse_code(self, obj) -> str:
        return obj.warehouse.code

    def get_dest_warehouse_code(self, obj) -> str | None:
        return obj.dest_warehouse.code if obj.dest_warehouse_id else None
