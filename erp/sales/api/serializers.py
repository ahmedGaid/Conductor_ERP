"""Sales API serializers. Prices/values are integer minor units; quantities are decimals."""
from __future__ import annotations

from rest_framework import serializers


class CustomerSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    code = serializers.CharField(max_length=32)
    name = serializers.CharField(max_length=200)
    credit_limit_minor = serializers.IntegerField(min_value=0, required=False, default=0)
    is_active = serializers.BooleanField(required=False, default=True)

    def to_representation(self, obj) -> dict:
        return {
            "id": str(obj.id),
            "code": obj.code,
            "name": obj.name,
            "credit_limit_minor": obj.credit_limit_minor,
            "is_active": obj.is_active,
        }


class OrderLineInputSerializer(serializers.Serializer):
    item_sku = serializers.CharField(max_length=64)
    description = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    quantity = serializers.DecimalField(max_digits=18, decimal_places=4)
    unit_price = serializers.IntegerField(min_value=0)  # minor units


class OrderCreateSerializer(serializers.Serializer):
    customer_code = serializers.CharField()
    warehouse_code = serializers.CharField()
    order_date = serializers.DateField(required=False)
    currency = serializers.CharField(max_length=3, required=False, default="EGP")
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    lines = OrderLineInputSerializer(many=True)


class PaymentSerializer(serializers.Serializer):
    amount = serializers.IntegerField(min_value=1)  # minor units


class OrderLineSerializer(serializers.Serializer):
    line_no = serializers.IntegerField()
    item_sku = serializers.CharField()
    description = serializers.CharField()
    quantity = serializers.DecimalField(max_digits=18, decimal_places=4)
    unit_price_minor = serializers.IntegerField()
    line_total_minor = serializers.IntegerField()


class OrderSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    number = serializers.CharField()
    customer_code = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()
    order_date = serializers.DateField()
    warehouse_code = serializers.CharField()
    currency = serializers.CharField()
    status = serializers.CharField()
    subtotal_minor = serializers.IntegerField()
    invoiced_minor = serializers.IntegerField()
    paid_minor = serializers.IntegerField()
    outstanding_minor = serializers.IntegerField()
    invoice_number = serializers.CharField()
    notes = serializers.CharField()
    lines = serializers.SerializerMethodField()

    def get_customer_code(self, obj) -> str:
        return obj.customer.code

    def get_customer_name(self, obj) -> str:
        return obj.customer.name

    def get_lines(self, obj) -> list:
        return OrderLineSerializer(obj.lines.all().order_by("line_no"), many=True).data
