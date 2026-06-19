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

from erp.core.models import AuditedModel


class NotificationChannel(models.TextChoices):
    EMAIL = "email", "Email"
    WHATSAPP = "whatsapp", "WhatsApp"


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

    class Meta:
        db_table = "notifications_notification"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status"]), models.Index(fields=["channel"]),
                   models.Index(fields=["reference"])]

    def __str__(self) -> str:  # pragma: no cover
        return f"Notification[{self.channel}->{self.recipient} {self.status}]"
