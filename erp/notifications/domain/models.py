"""Notification ORM models.

A ``Notification`` is the durable log of an outbound message dispatched through a channel adapter
(email, WhatsApp, …). It records the intent (channel, recipient, subject, body), the business key it
relates to (``reference`` — e.g. an invoice or ticket number, never a cross-module FK), the source
``event_name``, and the delivery outcome (status + provider reference / error). The log is the audit
trail: every dispatch — success or failure — leaves exactly one row, so a failed send is visible and
resendable rather than lost.
"""
from __future__ import annotations

from django.db import models

from erp.core.models import AuditedModel, TimeStampedModel


class NotificationChannel(models.TextChoices):
    EMAIL = "email", "Email"
    WHATSAPP = "whatsapp", "WhatsApp"
    # In-app: the row itself is the delivery — no gateway, no network. Read by the notifications
    # inbox, addressed to an internal user (``recipient`` holds the username), not a customer.
    INAPP = "inapp", "In-app"


class NotificationStatus(models.TextChoices):
    PENDING = "pending", "Pending"   # row created, adapter not yet called
    SENT = "sent", "Sent"            # adapter accepted the message
    FAILED = "failed", "Failed"      # adapter raised or rejected — isolated, recorded, resendable


class Notification(AuditedModel):
    channel = models.CharField(max_length=16, choices=NotificationChannel.choices)
    recipient = models.CharField(max_length=255)
    subject = models.CharField(max_length=255, blank=True, default="")
    body = models.TextField(blank=True, default="")
    # Business key into the source record (invoice number, ticket number, …) — no FK crosses a boundary.
    reference = models.CharField(max_length=64, blank=True, default="")
    event_name = models.CharField(max_length=64, blank=True, default="")
    status = models.CharField(max_length=16, choices=NotificationStatus.choices,
                              default=NotificationStatus.PENDING)
    provider_ref = models.CharField(max_length=64, blank=True, default="")  # adapter's message id
    error_text = models.CharField(max_length=255, blank=True, default="")
    sent_at = models.DateTimeField(null=True, blank=True)
    # When the recipient opened it in their inbox — null = unread. Only meaningful for the in-app
    # channel (email/WhatsApp leave the app; there is nothing to mark read there).
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "notifications_notification"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status"]), models.Index(fields=["channel"]),
                   models.Index(fields=["reference"])]

    def __str__(self) -> str:  # pragma: no cover
        return f"Notification[{self.channel}->{self.recipient} {self.status}]"


class WebhookSubscription(AuditedModel):
    """An admin-configured relay: any subscribed domain event fans out as a signed HTTP POST to
    ``url``. The cheapest external-integration primitive — see ``erp.notifications.services.webhooks``
    for delivery + signing, and ``erp.notifications.webhook_catalog`` for the subscribable events."""

    url = models.URLField(max_length=500)
    event_names = models.JSONField(default=list)
    secret = models.CharField(max_length=64)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "notifications_webhook_subscription"
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover
        return f"WebhookSubscription[{self.url}]"


class WebhookDeliveryStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    DELIVERED = "delivered", "Delivered"
    RETRYING = "retrying", "Retrying"
    FAILED = "failed", "Failed"


class WebhookDelivery(TimeStampedModel):
    """One attempt log for one event fanned out to one subscription. Every delivery — success or
    failure — leaves exactly one row, updated in place across retries (mirrors ``Notification``)."""

    subscription = models.ForeignKey(WebhookSubscription, on_delete=models.CASCADE,
                                     related_name="deliveries")
    event_name = models.CharField(max_length=64)
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=16, choices=WebhookDeliveryStatus.choices,
                              default=WebhookDeliveryStatus.PENDING)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.CharField(max_length=255, blank=True, default="")
    next_retry_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "notifications_webhook_delivery"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status"]), models.Index(fields=["subscription"])]

    def __str__(self) -> str:  # pragma: no cover
        return f"WebhookDelivery[{self.event_name}->{self.subscription_id} {self.status}]"
