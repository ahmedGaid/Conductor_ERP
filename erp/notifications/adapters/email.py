"""Email channel adapter — real SMTP, offline-safe by default.

Sends through Django's email framework, so the transport is whatever ``EMAIL_BACKEND`` is configured
to be. In dev/offline that defaults to the **console backend** (prints the message, never touches the
network); in production, point ``EMAIL_BACKEND`` at SMTP via env and nothing else changes. The
adapter surface stays identical either way.
"""
from __future__ import annotations

import hashlib

from django.conf import settings
from django.core.mail import send_mail

from .base import NotificationMessage, SendResult


class EmailAdapter:
    channel = "email"

    def send(self, message: NotificationMessage) -> SendResult:
        sent = send_mail(
            subject=message.subject,
            message=message.body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "conductor@example.com"),
            recipient_list=[message.recipient],
            fail_silently=False,
        )
        if not sent:
            return SendResult(ok=False, error="email backend reported 0 delivered")
        # A stable local reference for the log (the SMTP server's id isn't returned by send_mail).
        ref = hashlib.sha256(f"{message.recipient}|{message.subject}".encode("utf-8")).hexdigest()[:24]
        return SendResult(provider_ref=f"email-{ref}", ok=True)
