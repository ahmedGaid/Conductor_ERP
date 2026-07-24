"""Sales API serializers. Prices/values are integer minor units; quantities are decimals."""
from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers


class CustomerSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    code = serializers.CharField(max_length=32)
    name = serializers.CharField(max_length=200)
    credit_limit_minor = serializers.IntegerField(min_value=0, required=False, default=0)
    is_active = serializers.BooleanField(required=False, default=True)
    # ETA receiver identity: a tax registration number, or a national ID as the fallback for a
    # customer with no registration number. Both optional; whichever is given must be well-formed.
    tax_registration_number = serializers.CharField(
        max_length=32, required=False, allow_blank=True, default="", trim_whitespace=True)
    national_id = serializers.CharField(
        max_length=14, required=False, allow_blank=True, default="", trim_whitespace=True)
    custom_data = serializers.JSONField(required=False, default=dict)

    def validate_tax_registration_number(self, value: str) -> str:
        value = (value or "").strip()
        if value and not value.isdigit():
            raise serializers.ValidationError("The tax registration number must be digits only.")
        return value

    def validate_national_id(self, value: str) -> str:
        # Egyptian national ID is exactly 14 digits. Validate only when given (it is the fallback
        # identity, not a required field for every customer).
        value = (value or "").strip()
        if value and (len(value) != 14 or not value.isdigit()):
            raise serializers.ValidationError("The national ID must be 14 digits.")
        return value

    def to_representation(self, obj) -> dict:
        return {
            "id": str(obj.id),
            "code": obj.code,
            "name": obj.name,
            "credit_limit_minor": obj.credit_limit_minor,
            "is_active": obj.is_active,
            "tax_registration_number": obj.tax_registration_number,
            "national_id": obj.national_id,
            "custom_data": obj.custom_data,
        }


class CustomerUpdateSerializer(serializers.Serializer):
    """Partial update — everything but the business-key ``code``, which callers already use to
    reference this customer elsewhere (imports, receipts) and never changes after creation."""

    name = serializers.CharField(max_length=200, required=False)
    credit_limit_minor = serializers.IntegerField(min_value=0, required=False)
    is_active = serializers.BooleanField(required=False)
    tax_registration_number = serializers.CharField(
        max_length=32, required=False, allow_blank=True, trim_whitespace=True)
    national_id = serializers.CharField(
        max_length=14, required=False, allow_blank=True, trim_whitespace=True)
    custom_data = serializers.JSONField(required=False)

    validate_tax_registration_number = CustomerSerializer.validate_tax_registration_number
    validate_national_id = CustomerSerializer.validate_national_id


class OrderLineInputSerializer(serializers.Serializer):
    item_sku = serializers.CharField(max_length=64)
    description = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    quantity = serializers.DecimalField(max_digits=18, decimal_places=4)
    unit_price = serializers.IntegerField(min_value=0)  # minor units
    discount = serializers.IntegerField(min_value=0, required=False, default=0)  # minor units


class OrderCreateSerializer(serializers.Serializer):
    customer_code = serializers.CharField()
    warehouse_code = serializers.CharField()
    order_date = serializers.DateField(required=False)
    currency = serializers.CharField(max_length=3, required=False, default="EGP")
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    tax_code = serializers.CharField(max_length=16, required=False, allow_blank=True, default="")
    lines = OrderLineInputSerializer(many=True)


class PaymentSerializer(serializers.Serializer):
    amount = serializers.IntegerField(min_value=1)  # minor units


class PendingPaymentSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    order_id = serializers.SerializerMethodField()
    order_number = serializers.SerializerMethodField()
    party_code = serializers.CharField()
    amount_minor = serializers.IntegerField()
    date = serializers.DateField()
    method = serializers.CharField()
    source = serializers.CharField()
    status = serializers.CharField()
    batch_ref = serializers.CharField()

    def get_order_id(self, obj) -> str | None:
        return str(obj.order_id) if obj.order_id else None

    def get_order_number(self, obj) -> str | None:
        return obj.order.number if obj.order_id else None


class MatchPendingPaymentSerializer(serializers.Serializer):
    order_id = serializers.UUIDField()


class LineQtySerializer(serializers.Serializer):
    line_no = serializers.IntegerField(min_value=1)
    quantity = serializers.DecimalField(max_digits=18, decimal_places=4, min_value=Decimal("0"))


class LinesActionSerializer(serializers.Serializer):
    """Optional per-line quantities for a partial deliver / return. Empty body = act in full."""

    lines = LineQtySerializer(many=True, required=False)

    def as_map(self) -> dict | None:
        rows = self.validated_data.get("lines") or []
        if not rows:
            return None
        return {row["line_no"]: row["quantity"] for row in rows}


class OrderLinesUpdateSerializer(serializers.Serializer):
    """Replace a draft order's lines wholesale (edit-record path). Mirrors ``OrderCreateSerializer``'s
    ``lines`` shape; the order's customer/warehouse/tax are set at creation and not edited here."""

    lines = OrderLineInputSerializer(many=True)


class OrderLineSerializer(serializers.Serializer):
    line_no = serializers.IntegerField()
    item_sku = serializers.CharField()
    description = serializers.CharField()
    quantity = serializers.DecimalField(max_digits=18, decimal_places=4)
    delivered_qty = serializers.DecimalField(max_digits=18, decimal_places=4)
    returned_qty = serializers.DecimalField(max_digits=18, decimal_places=4)
    unit_price_minor = serializers.IntegerField()
    discount_minor = serializers.IntegerField()
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
    tax_code = serializers.CharField()
    tax_minor = serializers.IntegerField()
    invoiced_minor = serializers.IntegerField()
    paid_minor = serializers.IntegerField()
    returned_minor = serializers.IntegerField()
    outstanding_minor = serializers.IntegerField()
    approved = serializers.BooleanField()
    requires_approval = serializers.SerializerMethodField()
    invoice_number = serializers.CharField()
    credit_note_number = serializers.CharField()
    notes = serializers.CharField()
    lines = serializers.SerializerMethodField()

    def get_customer_code(self, obj) -> str:
        return obj.customer.code

    def get_customer_name(self, obj) -> str:
        return obj.customer.name

    def get_requires_approval(self, obj) -> bool:
        from ..services import order_requires_approval

        return order_requires_approval(obj.subtotal_minor)

    def get_lines(self, obj) -> list:
        # No .order_by() here: it would clone the queryset and bypass the list view's prefetch
        # cache (a query per row). Meta.ordering on the line model already yields line_no order.
        return OrderLineSerializer(obj.lines.all(), many=True).data


class QuoteLineInputSerializer(serializers.Serializer):
    item_sku = serializers.CharField(max_length=64)
    description = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    quantity = serializers.DecimalField(max_digits=18, decimal_places=4)
    unit_price = serializers.IntegerField(min_value=0)  # minor units


class QuotationCreateSerializer(serializers.Serializer):
    customer_code = serializers.CharField()
    warehouse_code = serializers.CharField()
    quote_date = serializers.DateField(required=False)
    validity_until = serializers.DateField(required=False, allow_null=True)
    currency = serializers.CharField(max_length=3, required=False, default="EGP")
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    lines = QuoteLineInputSerializer(many=True)


class RejectSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")


class QuotationLineSerializer(serializers.Serializer):
    line_no = serializers.IntegerField()
    item_sku = serializers.CharField()
    description = serializers.CharField()
    quantity = serializers.DecimalField(max_digits=18, decimal_places=4)
    unit_price_minor = serializers.IntegerField()
    line_total_minor = serializers.IntegerField()


class QuotationSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    number = serializers.CharField()
    customer_code = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()
    quote_date = serializers.DateField()
    validity_until = serializers.DateField(allow_null=True)
    warehouse_code = serializers.CharField()
    currency = serializers.CharField()
    status = serializers.CharField()
    subtotal_minor = serializers.IntegerField()
    requires_approval = serializers.SerializerMethodField()
    rejected_reason = serializers.CharField()
    converted_order_number = serializers.CharField()
    notes = serializers.CharField()
    lines = serializers.SerializerMethodField()

    def get_customer_code(self, obj) -> str:
        return obj.customer.code

    def get_customer_name(self, obj) -> str:
        return obj.customer.name

    def get_requires_approval(self, obj) -> bool:
        from ..services import requires_approval

        return requires_approval(obj.subtotal_minor)

    def get_lines(self, obj) -> list:
        # Prefetch-cache friendly — see OrderSerializer.get_lines.
        return QuotationLineSerializer(obj.lines.all(), many=True).data
