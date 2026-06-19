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
