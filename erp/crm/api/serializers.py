"""CRM API serializers. Money is integer minor units; quantities are decimals."""
from __future__ import annotations

from rest_framework import serializers


# --- Leads -----------------------------------------------------------------

class LeadSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    code = serializers.CharField()
    name = serializers.CharField()
    company = serializers.CharField()
    email = serializers.CharField()
    phone = serializers.CharField()
    source = serializers.CharField()
    status = serializers.CharField()
    owner = serializers.CharField()
    notes = serializers.CharField()


class LeadCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    company = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    email = serializers.CharField(max_length=254, required=False, allow_blank=True, default="")
    phone = serializers.CharField(max_length=40, required=False, allow_blank=True, default="")
    source = serializers.CharField(max_length=16, required=False, default="other")
    owner = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


class LeadStatusSerializer(serializers.Serializer):
    status = serializers.CharField()


class LeadConvertSerializer(serializers.Serializer):
    opportunity_name = serializers.CharField(required=False, allow_blank=True, default="")
    customer_code = serializers.CharField(required=False, allow_blank=True, default="")


# --- Opportunities ---------------------------------------------------------

class OppLineInputSerializer(serializers.Serializer):
    item_sku = serializers.CharField(max_length=64)
    description = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    quantity = serializers.DecimalField(max_digits=18, decimal_places=4)
    unit_price = serializers.IntegerField(min_value=0)  # minor units


class OppCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    customer_code = serializers.CharField(required=False, allow_blank=True, default="")
    warehouse_code = serializers.CharField(required=False, allow_blank=True, default="")
    currency = serializers.CharField(max_length=3, required=False, default="EGP")
    probability = serializers.IntegerField(min_value=0, max_value=100, required=False, default=10)
    expected_close = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    lines = OppLineInputSerializer(many=True, required=False, default=list)


class OppStageSerializer(serializers.Serializer):
    stage = serializers.CharField()


class OppWinSerializer(serializers.Serializer):
    create_sales_order = serializers.BooleanField(required=False, default=True)


class OppLoseSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class OppLineSerializer(serializers.Serializer):
    line_no = serializers.IntegerField()
    item_sku = serializers.CharField()
    description = serializers.CharField()
    quantity = serializers.DecimalField(max_digits=18, decimal_places=4)
    unit_price_minor = serializers.IntegerField()
    line_total_minor = serializers.IntegerField()


class OpportunitySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    number = serializers.CharField()
    name = serializers.CharField()
    lead_code = serializers.SerializerMethodField()
    customer_code = serializers.CharField()
    warehouse_code = serializers.CharField()
    stage = serializers.CharField()
    currency = serializers.CharField()
    amount_minor = serializers.IntegerField()
    weighted_minor = serializers.IntegerField()
    probability = serializers.IntegerField()
    expected_close = serializers.DateField()
    sales_order_number = serializers.CharField()
    notes = serializers.CharField()
    lines = serializers.SerializerMethodField()

    def get_lead_code(self, obj) -> str:
        return obj.lead.code if obj.lead_id else ""

    def get_lines(self, obj) -> list:
        return OppLineSerializer(obj.lines.all().order_by("line_no"), many=True).data


# --- Activities ------------------------------------------------------------

class ActivitySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    type = serializers.CharField()
    subject = serializers.CharField()
    related_type = serializers.CharField()
    related_ref = serializers.CharField()
    owner = serializers.CharField()
    due_date = serializers.DateField()
    done = serializers.BooleanField()
    notes = serializers.CharField()


class ActivityCreateSerializer(serializers.Serializer):
    type = serializers.CharField(max_length=16)
    subject = serializers.CharField(max_length=200)
    related_type = serializers.CharField(max_length=16)
    related_ref = serializers.CharField(max_length=64)
    owner = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    due_date = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


# --- Tickets ---------------------------------------------------------------

class TicketSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    number = serializers.CharField()
    customer_code = serializers.CharField()
    subject = serializers.CharField()
    description = serializers.CharField()
    priority = serializers.CharField()
    status = serializers.CharField()
    owner = serializers.CharField()
    opened_at = serializers.DateTimeField()
    sla_due_at = serializers.DateTimeField()
    resolved_at = serializers.DateTimeField()
    is_breached = serializers.BooleanField()


class TicketCreateSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=200)
    customer_code = serializers.CharField(required=False, allow_blank=True, default="")
    description = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")
    priority = serializers.CharField(max_length=16, required=False, default="medium")
    owner = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")


class TicketResolveSerializer(serializers.Serializer):
    resolution = serializers.CharField(required=False, allow_blank=True, default="")
