"""E-invoicing API serializers. Money is integer minor units."""
from __future__ import annotations

from rest_framework import serializers


class ETAInvoiceSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    invoice_number = serializers.CharField()
    order_number = serializers.CharField()
    customer_code = serializers.CharField()
    customer_name = serializers.CharField()
    issue_date = serializers.DateField()
    currency = serializers.CharField()
    tax_code = serializers.CharField()
    net_minor = serializers.IntegerField()
    tax_minor = serializers.IntegerField()
    total_minor = serializers.IntegerField()
    status = serializers.CharField()
    uuid = serializers.CharField()
    document_hash = serializers.CharField()
    error_text = serializers.CharField()
