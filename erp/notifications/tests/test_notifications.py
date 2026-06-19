"""Notifications — domain events trigger channel adapters through the single interface, and any
adapter failure is recorded + isolated from the publisher (invoicing / ticket escalation)."""
from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from erp.core.events import bus
from erp.notifications import handlers
from erp.notifications.adapters import (
    NotificationMessage,
    SendResult,
    get_adapter,
    register_adapter,
)
from erp.notifications.domain.models import (
    Notification,
    NotificationChannel,
    NotificationStatus,
)
from erp.notifications.services import dispatch, resend
from erp.sales.events import ORDER_INVOICED

pytestmark = pytest.mark.django_db


def _breached_ticket():
    from erp.crm.domain.models import TicketPriority
    from erp.crm.services.support import create_ticket

    ticket = create_ticket(subject="Service down", customer_code="CUST1",
                           priority=TicketPriority.HIGH)
    ticket.sla_due_at = timezone.now() - timedelta(hours=1)  # force the SLA breach
    ticket.save(update_fields=["sla_due_at"])
    return ticket


# --- the adapters + the interface ---

def test_email_adapter_sends_offline():
    result = get_adapter(NotificationChannel.EMAIL).send(
        NotificationMessage(recipient="a@b.com", subject="Hi", body="Body"))
    assert result.ok
    assert result.provider_ref.startswith("email-")


def test_whatsapp_adapter_is_a_deterministic_offline_stub():
    msg = NotificationMessage(recipient="+20100", subject="S", body="B")
    r1 = get_adapter(NotificationChannel.WHATSAPP).send(msg)
    r2 = get_adapter(NotificationChannel.WHATSAPP).send(msg)
    assert r1.ok and r1.provider_ref == r2.provider_ref  # no network, reproducible
    assert r1.provider_ref.startswith("wamid-")


def test_dispatch_routes_through_the_adapter_interface():
    # A throwaway adapter registered on a new channel must receive the message via the interface —
    # dispatch never special-cases a channel, it only knows get_adapter(channel).send(...).
    seen: list[NotificationMessage] = []

    class _Recorder:
        channel = "recorder"

        def send(self, message: NotificationMessage) -> SendResult:
            seen.append(message)
            return SendResult(provider_ref="rec-1", ok=True)

    register_adapter(_Recorder())
    note = dispatch(channel="recorder", recipient="r", subject="S", body="B")
    assert note.status == NotificationStatus.SENT
    assert len(seen) == 1 and seen[0].recipient == "r"


# --- dispatch records every outcome; failures never propagate ---

def test_dispatch_records_a_sent_row():
    note = dispatch(channel=NotificationChannel.EMAIL, recipient="x@y.com",
                    subject="Test", body="hello", reference="INV-1")
    assert note.status == NotificationStatus.SENT
    assert note.provider_ref and note.sent_at is not None


def test_unknown_channel_is_recorded_failed_not_raised():
    note = dispatch(channel="pigeon", recipient="r", subject="S")
    assert note.status == NotificationStatus.FAILED
    assert "pigeon" in note.error_text


def test_adapter_exception_is_caught_and_recorded(monkeypatch):
    import sys

    # The package re-exports the `dispatch` function under the same name as its submodule, so reach
    # the real module via sys.modules to patch the symbol dispatch() actually calls.
    dispatch_mod = sys.modules["erp.notifications.services.dispatch"]

    def _raise(channel):
        raise RuntimeError("smtp refused")

    monkeypatch.setattr(dispatch_mod, "get_adapter", _raise)
    note = dispatch(channel=NotificationChannel.EMAIL, recipient="x@y.com", subject="S")
    assert note.status == NotificationStatus.FAILED
    assert "smtp refused" in note.error_text


def test_resend_redispatches_a_new_row():
    first = dispatch(channel=NotificationChannel.EMAIL, recipient="x@y.com",
                     subject="S", reference="INV-9")
    again = resend(first)
    assert again.id != first.id and again.reference == "INV-9"
    assert Notification.objects.filter(reference="INV-9").count() == 2


# --- the event wiring: invoice -> email, ticket escalation -> whatsapp ---

def test_invoice_event_dispatches_an_email():
    bus.publish(ORDER_INVOICED, {"invoice": "INV-2026-001", "customer_code": "CUST1",
                                 "customer_name": "Acme"})
    note = Notification.objects.filter(reference="INV-2026-001",
                                       channel=NotificationChannel.EMAIL).first()
    assert note is not None
    assert note.status == NotificationStatus.SENT
    assert note.event_name == ORDER_INVOICED


def test_ticket_escalation_dispatches_whatsapp():
    from erp.crm.services.support import escalate_ticket

    ticket = _breached_ticket()
    escalate_ticket(ticket)
    note = Notification.objects.filter(reference=ticket.number,
                                       channel=NotificationChannel.WHATSAPP).first()
    assert note is not None and note.status == NotificationStatus.SENT


def test_notify_failure_is_bus_isolated_from_escalation(monkeypatch):
    # If the notification handler blows up, the bus must isolate it so escalation still succeeds.
    def _boom(*args, **kwargs):
        raise RuntimeError("gateway down")

    monkeypatch.setattr(handlers, "dispatch", _boom)
    from erp.crm.services.support import escalate_ticket

    ticket = _breached_ticket()
    result = escalate_ticket(ticket)  # publishes TICKET_ESCALATED; handler raises; bus swallows it
    assert result.is_escalated  # the publisher completed despite the failing subscriber


# --- API ---

def test_notifications_api_requires_auth():
    from rest_framework.test import APIClient

    assert APIClient().get("/api/notifications").status_code == 401


def test_notifications_api_lists_and_resends():
    from rest_framework.test import APIClient

    from erp.identity.models import User

    note = dispatch(channel=NotificationChannel.WHATSAPP, recipient="+20100",
                    subject="S", reference="TKT-1")
    user = User.objects.create_user(username="notif_admin", password="Dev12345!")
    user.is_superuser = True
    user.save(update_fields=["is_superuser"])
    client = APIClient()
    client.force_authenticate(user=user)

    listed = client.get("/api/notifications").data["data"]
    assert any(r["reference"] == "TKT-1" for r in listed)

    resent = client.post(f"/api/notifications/{note.id}/resend")
    assert resent.status_code == 201
    assert Notification.objects.filter(reference="TKT-1").count() == 2
