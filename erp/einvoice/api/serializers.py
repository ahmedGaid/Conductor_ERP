"""E-invoicing API serializers. Money is integer minor units."""
from __future__ import annotations

from rest_framework import serializers

from ..domain.models import ETAEnvironment


def _https_or_blank(value: str) -> str:
    """Allow an empty string (field being cleared) or an https URL — nothing else. ETA serves https
    only, and a non-https identity URL would put the client secret on the wire in clear text."""
    value = (value or "").strip()
    if value and not value.lower().startswith("https://"):
        raise serializers.ValidationError("Must be an https:// URL.")
    return value


class ETASettingsUpdateSerializer(serializers.Serializer):
    """Admin input for the ETA connection settings. The client secret is **write-only**: it is
    accepted here but never appears in any response. Omitting it (or sending an empty string) leaves
    the stored secret unchanged; ``clear_secret`` removes it."""

    environment = serializers.ChoiceField(choices=ETAEnvironment.values, required=False, allow_blank=True)
    identity_url = serializers.CharField(required=False, allow_blank=True, max_length=255, validators=[_https_or_blank])
    api_base_url = serializers.CharField(required=False, allow_blank=True, max_length=255, validators=[_https_or_blank])
    client_id = serializers.CharField(required=False, allow_blank=True, max_length=128)
    rin = serializers.CharField(required=False, allow_blank=True, max_length=32)
    client_secret = serializers.CharField(required=False, allow_blank=True, write_only=True, trim_whitespace=False)
    clear_secret = serializers.BooleanField(required=False, default=False)
    enabled = serializers.BooleanField(required=False)


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
