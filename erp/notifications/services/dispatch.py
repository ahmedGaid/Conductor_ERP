"""The single point every outbound notification flows through.

``dispatch`` writes the log row, resolves the channel **adapter** through the interface, calls
``send`` on it, and records the outcome — never propagating an adapter failure. So a broken channel
produces a ``failed`` row (visible + resendable), not an exception that bubbles into the publisher.
Combined with the event bus's own subscriber isolation, an integration outage can never break
invoicing or ticket escalation.
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from erp.audit import services as audit
from erp.core.events import bus

from .. import events
from ..adapters import NotificationMessage, get_adapter
from ..domain.models import Notification, NotificationStatus


@transaction.atomic
def dispatch(
    *,
    channel: str,
    recipient: str,
    subject: str = "",
    body: str = "",
    reference: str = "",
    event_name: str = "",
    actor=None,
) -> Notification:
    """Send one message through a channel adapter and record the outcome. Never raises on a send
    failure — the failure is captured on the row and a ``Failed`` event is published instead."""
    note = Notification.objects.create(
        channel=channel, recipient=recipient, subject=subject, body=body,
        reference=reference, event_name=event_name, status=NotificationStatus.PENDING,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
    )
    try:
        result = get_adapter(channel).send(
            NotificationMessage(recipient=recipient, subject=subject, body=body)
        )
        if result.ok:
            note.status = NotificationStatus.SENT
            note.provider_ref = result.provider_ref
            note.sent_at = timezone.now()
            note.error_text = ""
        else:
            note.status = NotificationStatus.FAILED
            note.error_text = (result.error or "send rejected")[:255]
    except Exception as exc:  # noqa: BLE001 - an adapter outage must not break the caller
        note.status = NotificationStatus.FAILED
        note.error_text = str(exc)[:255]
    note.save(update_fields=["status", "provider_ref", "sent_at", "error_text", "updated_at"])
    audit.record(module="notifications", action="dispatch", entity_type="Notification",
                 entity_id=str(note.id), actor=actor,
                 after={"channel": channel, "status": note.status})
    sent = note.status == NotificationStatus.SENT
    bus.publish(events.NOTIFICATION_SENT if sent else events.NOTIFICATION_FAILED,
                {"id": str(note.id), "channel": channel, "reference": reference})
    return note


def resend(note: Notification, actor=None) -> Notification:
    """Re-dispatch an existing notification (e.g. after a channel outage). Yields a new log row."""
    return dispatch(channel=note.channel, recipient=note.recipient, subject=note.subject,
                    body=note.body, reference=note.reference,
                    event_name=note.event_name, actor=actor)
