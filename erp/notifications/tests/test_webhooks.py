"""Outbound webhooks — signing, retry/backoff, SSRF egress guard, and the admin-only API.

No real network calls: ``urllib.request.urlopen`` is monkeypatched per test, mirroring how
``test_notifications.py`` stubs adapters rather than hitting real channels.
"""
from __future__ import annotations

import hashlib
import hmac
import json

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from erp.core.errors import ValidationError
from erp.core.events import bus
from erp.identity.models import User
from erp.notifications.domain.models import WebhookDelivery, WebhookDeliveryStatus, WebhookSubscription
from erp.notifications.services import webhooks
from erp.notifications.webhook_catalog import WEBHOOK_EVENT_CATALOG
from erp.sales.events import ORDER_INVOICED

pytestmark = pytest.mark.django_db


class _FakeResponse:
    def __init__(self, status: int = 200):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return b"{}"


def _admin():
    user = User.objects.create_user(username="webhook_admin", password="Dev12345!")
    user.is_superuser = True
    user.save(update_fields=["is_superuser"])
    return user


def _sub(**kwargs):
    defaults = dict(url="https://example.com/hook", event_names=[ORDER_INVOICED])
    defaults.update(kwargs)
    return webhooks.create_subscription(**defaults)


# --- signing + successful delivery ---

def test_signature_correctness(monkeypatch):
    sub = _sub()
    delivery = WebhookDelivery.objects.create(subscription=sub, event_name=ORDER_INVOICED,
                                              payload={"event": ORDER_INVOICED, "data": {"x": 1}})
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["headers"] = dict(req.headers)
        captured["body"] = req.data
        return _FakeResponse(200)

    monkeypatch.setattr("erp.notifications.services.webhooks.urllib.request.urlopen", fake_urlopen)
    result = webhooks.attempt_delivery(delivery.id)

    assert result.status == WebhookDeliveryStatus.DELIVERED
    expected = "sha256=" + hmac.new(sub.secret.encode(), captured["body"], hashlib.sha256).hexdigest()
    # DRF/urllib title-cases header names.
    assert captured["headers"]["X-conductor-signature"] == expected


# --- retry schedule on failure ---

def test_retry_schedule_on_failure(monkeypatch):
    sub = _sub()
    delivery = WebhookDelivery.objects.create(subscription=sub, event_name=ORDER_INVOICED,
                                              payload={"event": ORDER_INVOICED})

    def fake_urlopen(req, timeout=None):
        raise OSError("connection refused")

    monkeypatch.setattr("erp.notifications.services.webhooks.urllib.request.urlopen", fake_urlopen)

    before = timezone.now()
    for expected_delay in webhooks.RETRY_SCHEDULE:
        result = webhooks.attempt_delivery(delivery.id)
        assert result.status == WebhookDeliveryStatus.RETRYING
        assert result.next_retry_at is not None
        assert result.next_retry_at >= before  # scheduled forward, not immediate

    # One more attempt exhausts MAX_ATTEMPTS -> failed, no further retry.
    result = webhooks.attempt_delivery(delivery.id)
    assert result.status == WebhookDeliveryStatus.FAILED
    assert result.next_retry_at is None
    assert result.attempts == webhooks.MAX_ATTEMPTS


# --- inactive subscription is skipped ---

def test_inactive_subscription_skipped():
    _sub(url="https://example.com/off")
    inactive = _sub(url="https://example.com/inactive")
    webhooks.update_subscription(inactive.id, is_active=False)

    bus.publish(ORDER_INVOICED, {"invoice": "INV-1", "amount_minor": 10000})

    assert not WebhookDelivery.objects.filter(subscription=inactive).exists()


# --- SSRF-blocked URL rejected at create ---

def test_ssrf_blocked_url_rejected_at_create():
    with pytest.raises(ValidationError):
        webhooks.create_subscription(url="http://127.0.0.1/hook", event_names=[ORDER_INVOICED])


def test_unknown_event_rejected_at_create():
    with pytest.raises(ValidationError):
        webhooks.create_subscription(url="https://example.com/hook", event_names=["not.a.real.event"])


# --- money stays integer minor units in the payload ---

def test_payload_money_is_integers(monkeypatch):
    sub = _sub()

    def fake_urlopen(req, timeout=None):
        payload = json.loads(req.data)
        assert isinstance(payload["data"]["amount_minor"], int)
        return _FakeResponse(200)

    monkeypatch.setattr("erp.notifications.services.webhooks.urllib.request.urlopen", fake_urlopen)

    bus.publish(ORDER_INVOICED, {"invoice": "INV-2", "amount_minor": 250050})
    delivery = WebhookDelivery.objects.get(subscription=sub, event_name=ORDER_INVOICED)
    assert delivery.status == WebhookDeliveryStatus.DELIVERED


def test_on_domain_event_only_notifies_matching_subscriptions(monkeypatch):
    wanted = _sub(url="https://example.com/wants-it", event_names=[ORDER_INVOICED])
    _sub(url="https://example.com/does-not-want-it", event_names=[WEBHOOK_EVENT_CATALOG[0]]
         if WEBHOOK_EVENT_CATALOG[0] != ORDER_INVOICED else [WEBHOOK_EVENT_CATALOG[-1]])
    monkeypatch.setattr("erp.notifications.services.webhooks.urllib.request.urlopen",
                        lambda req, timeout=None: _FakeResponse(200))

    bus.publish(ORDER_INVOICED, {"invoice": "INV-3"})

    assert WebhookDelivery.objects.filter(subscription=wanted, event_name=ORDER_INVOICED).exists()
    assert WebhookDelivery.objects.filter(event_name=ORDER_INVOICED).count() == 1


# --- API: admin-only CRUD + secret reveal-once + retry-now ---

def test_webhooks_api_requires_admin():
    client = APIClient()
    assert client.get("/api/notifications/webhooks").status_code == 401

    plain = User.objects.create_user(username="plain_user", password="Dev12345!")
    client.force_authenticate(user=plain)
    assert client.get("/api/notifications/webhooks").status_code == 403


def test_webhooks_api_event_catalog():
    client = APIClient()
    client.force_authenticate(user=_admin())
    res = client.get("/api/notifications/webhooks/events")
    assert res.status_code == 200
    assert ORDER_INVOICED in res.data["data"]


def test_webhooks_api_create_shows_secret_once_then_hides_it():
    client = APIClient()
    client.force_authenticate(user=_admin())

    created = client.post("/api/notifications/webhooks",
                          {"url": "https://example.com/hook", "event_names": [ORDER_INVOICED]},
                          format="json")
    assert created.status_code == 201
    assert created.data["data"]["secret"]  # shown once, on create

    listed = client.get("/api/notifications/webhooks").data["data"]
    assert all("secret" not in row for row in listed)


def test_webhooks_api_update_and_delete():
    client = APIClient()
    client.force_authenticate(user=_admin())
    sub = _sub()

    patched = client.patch(f"/api/notifications/webhooks/{sub.id}", {"is_active": False},
                           format="json")
    assert patched.status_code == 200 and patched.data["data"]["is_active"] is False

    deleted = client.delete(f"/api/notifications/webhooks/{sub.id}")
    assert deleted.status_code == 204
    assert not WebhookSubscription.objects.filter(id=sub.id).exists()


def test_webhooks_api_retry_now(monkeypatch):
    sub = _sub()
    delivery = WebhookDelivery.objects.create(subscription=sub, event_name=ORDER_INVOICED,
                                              payload={"event": ORDER_INVOICED})
    monkeypatch.setattr("erp.notifications.services.webhooks.urllib.request.urlopen",
                        lambda req, timeout=None: _FakeResponse(200))

    client = APIClient()
    client.force_authenticate(user=_admin())
    res = client.post(f"/api/notifications/webhooks/deliveries/{delivery.id}/retry")
    assert res.status_code == 200
    assert res.data["data"]["status"] == WebhookDeliveryStatus.DELIVERED
