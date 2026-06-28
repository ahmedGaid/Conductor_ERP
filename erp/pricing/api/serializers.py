"""Pricing API serializers. Prices are integer minor units in the list's currency; quantities decimal."""
from __future__ import annotations

from rest_framework import serializers


class PriceListSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    code = serializers.CharField(max_length=32)
    name = serializers.CharField(max_length=200)
    currency = serializers.CharField(max_length=3, required=False, default="EGP")
    tax_inclusive = serializers.BooleanField(required=False, default=False)
    is_default = serializers.BooleanField(required=False, default=False)
    is_active = serializers.BooleanField(required=False, default=True)
    line_count = serializers.IntegerField(read_only=True)

    def to_representation(self, obj) -> dict:
        return {
            "id": str(obj.id),
            "code": obj.code,
            "name": obj.name,
            "currency": obj.currency,
            "tax_inclusive": obj.tax_inclusive,
            "is_default": obj.is_default,
            "is_active": obj.is_active,
            # Annotated by the list view; falls back to a query when absent.
            "line_count": getattr(obj, "line_count", None)
            if getattr(obj, "line_count", None) is not None
            else obj.lines.count(),
        }


class PriceListUpdateSerializer(serializers.Serializer):
    """PATCH a price list — every field optional; code is immutable (it's the business key)."""

    name = serializers.CharField(max_length=200, required=False)
    currency = serializers.CharField(max_length=3, required=False)
    tax_inclusive = serializers.BooleanField(required=False)
    is_default = serializers.BooleanField(required=False)
    is_active = serializers.BooleanField(required=False)


class PriceListLineSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    item_sku = serializers.CharField(max_length=64)
    uom = serializers.CharField(max_length=16, required=False, default="unit")
    unit_price_minor = serializers.IntegerField(min_value=0)
    min_quantity = serializers.DecimalField(max_digits=18, decimal_places=4, required=False, default=0)
    valid_from = serializers.DateField(required=False, allow_null=True)
    valid_to = serializers.DateField(required=False, allow_null=True)

    def to_representation(self, obj) -> dict:
        return {
            "id": str(obj.id),
            "item_sku": obj.item_sku,
            "uom": obj.uom,
            "unit_price_minor": obj.unit_price_minor,
            "min_quantity": str(obj.min_quantity),
            "valid_from": obj.valid_from.isoformat() if obj.valid_from else None,
            "valid_to": obj.valid_to.isoformat() if obj.valid_to else None,
        }


class CustomerPriceListSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    customer_code = serializers.CharField(max_length=32)
    price_list_code = serializers.CharField(max_length=32)

    def to_representation(self, obj) -> dict:
        return {
            "id": str(obj.id),
            "customer_code": obj.customer_code,
            "price_list_code": obj.price_list.code,
        }


class CustomerItemPriceSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    customer_code = serializers.CharField(max_length=32)
    item_sku = serializers.CharField(max_length=64)
    uom = serializers.CharField(max_length=16, required=False, default="unit")
    unit_price_minor = serializers.IntegerField(min_value=0)
    tax_inclusive = serializers.BooleanField(required=False, default=False)
    min_quantity = serializers.DecimalField(max_digits=18, decimal_places=4, required=False, default=0)
    valid_from = serializers.DateField(required=False, allow_null=True)
    valid_to = serializers.DateField(required=False, allow_null=True)

    def to_representation(self, obj) -> dict:
        return {
            "id": str(obj.id),
            "customer_code": obj.customer_code,
            "item_sku": obj.item_sku,
            "uom": obj.uom,
            "unit_price_minor": obj.unit_price_minor,
            "tax_inclusive": obj.tax_inclusive,
            "min_quantity": str(obj.min_quantity),
            "valid_from": obj.valid_from.isoformat() if obj.valid_from else None,
            "valid_to": obj.valid_to.isoformat() if obj.valid_to else None,
        }
