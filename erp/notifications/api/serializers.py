"""Notifications API serializers."""
from __future__ import annotations

from rest_framework import serializers


class NotificationSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    channel = serializers.CharField()
    recipient = serializers.CharField()
    subject = serializers.CharField()
    body = serializers.CharField()
    reference = serializers.CharField()
    event_name = serializers.CharField()
    status = serializers.CharField()
    provider_ref = serializers.CharField()
    error_text = serializers.CharField()
    sent_at = serializers.DateTimeField()
    created_at = serializers.DateTimeField()


class InboxSerializer(serializers.Serializer):
    """An in-app inbox row — the subset the panel renders (localised text is derived on the client
    from ``event_name`` + ``reference``, so the raw English subject/body are only a fallback)."""

    id = serializers.UUIDField()
    subject = serializers.CharField()
    body = serializers.CharField()
    reference = serializers.CharField()
    event_name = serializers.CharField()
    read_at = serializers.DateTimeField()
    created_at = serializers.DateTimeField()


class WebhookSubscriptionSerializer(serializers.Serializer):
    """Never includes ``secret`` — that is only ever returned once, on create/regenerate."""

    id = serializers.UUIDField()
    url = serializers.URLField()
    event_names = serializers.ListField(child=serializers.CharField())
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField()


class WebhookDeliverySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    event_name = serializers.CharField()
    status = serializers.CharField()
    attempts = serializers.IntegerField()
    last_error = serializers.CharField()
    next_retry_at = serializers.DateTimeField(allow_null=True)
    created_at = serializers.DateTimeField()
