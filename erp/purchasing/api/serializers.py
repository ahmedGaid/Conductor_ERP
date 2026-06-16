"""Purchasing API serializers. Costs/values are integer minor units; quantities are decimals."""
from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers


class SupplierSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    code = serializers.CharField(max_length=32)
    name = serializers.CharField(max_length=200)
    is_active = serializers.BooleanField(required=False, default=True)

    def to_representation(self, obj) -> dict:
        return {"id": str(obj.id), "code": obj.code, "name": obj.name, "is_active": obj.is_active}


class POLineInputSerializer(serializers.Serializer):
    item_sku = serializers.CharField(max_length=64)
    description = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    quantity = serializers.DecimalField(max_digits=18, decimal_places=4)
    unit_cost = serializers.IntegerField(min_value=0)  # minor units


class POCreateSerializer(serializers.Serializer):
    supplier_code = serializers.CharField()
    warehouse_code = serializers.CharField()
    order_date = serializers.DateField(required=False)
    currency = serializers.CharField(max_length=3, required=False, default="EGP")
    tax_code = serializers.CharField(max_length=16, required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    lines = POLineInputSerializer(many=True)


class PaymentSerializer(serializers.Serializer):
    amount = serializers.IntegerField(min_value=1)


class LineQtySerializer(serializers.Serializer):
    line_no = serializers.IntegerField(min_value=1)
    quantity = serializers.DecimalField(max_digits=18, decimal_places=4, min_value=Decimal("0"))


class LinesActionSerializer(serializers.Serializer):
    """Optional per-line quantities for a partial receive / return. Empty body = act in full."""

    lines = LineQtySerializer(many=True, required=False)

    def as_map(self) -> dict | None:
        rows = self.validated_data.get("lines") or []
        if not rows:
            return None
        return {row["line_no"]: row["quantity"] for row in rows}


class POLineSerializer(serializers.Serializer):
    line_no = serializers.IntegerField()
    item_sku = serializers.CharField()
    description = serializers.CharField()
    quantity = serializers.DecimalField(max_digits=18, decimal_places=4)
    received_qty = serializers.DecimalField(max_digits=18, decimal_places=4)
    returned_qty = serializers.DecimalField(max_digits=18, decimal_places=4)
    unit_cost_minor = serializers.IntegerField()
    line_total_minor = serializers.IntegerField()


class POSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    number = serializers.CharField()
    supplier_code = serializers.SerializerMethodField()
    supplier_name = serializers.SerializerMethodField()
    order_date = serializers.DateField()
    warehouse_code = serializers.CharField()
    currency = serializers.CharField()
    status = serializers.CharField()
    tax_code = serializers.CharField()
    subtotal_minor = serializers.IntegerField()
    received_minor = serializers.IntegerField()
    tax_minor = serializers.IntegerField()
    billed_minor = serializers.IntegerField()
    paid_minor = serializers.IntegerField()
    returned_minor = serializers.IntegerField()
    outstanding_minor = serializers.IntegerField()
    approved = serializers.BooleanField()
    requires_approval = serializers.SerializerMethodField()
    bill_number = serializers.CharField()
    debit_note_number = serializers.CharField()
    notes = serializers.CharField()
    lines = serializers.SerializerMethodField()

    def get_supplier_code(self, obj) -> str:
        return obj.supplier.code

    def get_supplier_name(self, obj) -> str:
        return obj.supplier.name

    def get_requires_approval(self, obj) -> bool:
        from ..services import order_requires_approval

        return order_requires_approval(obj.subtotal_minor)

    def get_lines(self, obj) -> list:
        return POLineSerializer(obj.lines.all().order_by("line_no"), many=True).data


class RequestLineInputSerializer(serializers.Serializer):
    item_sku = serializers.CharField(max_length=64)
    description = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    quantity = serializers.DecimalField(max_digits=18, decimal_places=4)
    unit_cost = serializers.IntegerField(min_value=0)  # minor units


class RequestCreateSerializer(serializers.Serializer):
    supplier_code = serializers.CharField()
    warehouse_code = serializers.CharField()
    request_date = serializers.DateField(required=False)
    currency = serializers.CharField(max_length=3, required=False, default="EGP")
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    lines = RequestLineInputSerializer(many=True)


class RejectSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")


class RequestLineSerializer(serializers.Serializer):
    line_no = serializers.IntegerField()
    item_sku = serializers.CharField()
    description = serializers.CharField()
    quantity = serializers.DecimalField(max_digits=18, decimal_places=4)
    unit_cost_minor = serializers.IntegerField()
    line_total_minor = serializers.IntegerField()


class RequestSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    number = serializers.CharField()
    supplier_code = serializers.SerializerMethodField()
    supplier_name = serializers.SerializerMethodField()
    request_date = serializers.DateField()
    warehouse_code = serializers.CharField()
    currency = serializers.CharField()
    status = serializers.CharField()
    subtotal_minor = serializers.IntegerField()
    requires_approval = serializers.SerializerMethodField()
    rejected_reason = serializers.CharField()
    converted_order_number = serializers.CharField()
    notes = serializers.CharField()
    lines = serializers.SerializerMethodField()

    def get_supplier_code(self, obj) -> str:
        return obj.supplier.code

    def get_supplier_name(self, obj) -> str:
        return obj.supplier.name

    def get_requires_approval(self, obj) -> bool:
        from ..services import requires_approval

        return requires_approval(obj.subtotal_minor)

    def get_lines(self, obj) -> list:
        return RequestLineSerializer(obj.lines.all().order_by("line_no"), many=True).data
