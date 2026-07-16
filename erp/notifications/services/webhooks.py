"""Outbound webhooks — admin-managed subscriptions that relay domain events to external systems.

An active subscription lists the event names it wants; the core-event listener (``on_domain_event``,
wired for every catalog event in ``handlers.register``) fans a matching event out to a
``WebhookDelivery`` row per subscription and hands it to the Celery task. A failed delivery schedules
its own retry (exponential backoff, capped attempts) rather than propagating — exactly like
``services.dispatch`` isolates a channel outage from the publisher.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import urllib.error
import urllib.request
from datetime import timedelta

from django.utils import timezone

from erp.core.errors import NotFoundError, ValidationError
from erp.workflow.adapters.egress import EgressBlockedError, assert_public_url

from ..domain.models import WebhookDelivery, WebhookDeliveryStatus, WebhookSubscription
from ..webhook_catalog import WEBHOOK_EVENT_CATALOG

# Exponential backoff in seconds: 1m / 5m / 30m / 2h, then fail — matches the plan's retry schedule.
RETRY_SCHEDULE = [60, 300, 1800, 7200]
MAX_ATTEMPTS = 5
_TIMEOUT = 10.0


def _validate_url(url: str) -> None:
    if not url:
        raise ValidationError("URL is required")
    try:
        assert_public_url(url)
    except EgressBlockedError as exc:
        raise ValidationError(str(exc)) from exc


def _validate_events(event_names: list[str]) -> list[str]:
    names = [n for n in dict.fromkeys(event_names or []) if n]
    if not names:
        raise ValidationError("select at least one event")
    unknown = [n for n in names if n not in WEBHOOK_EVENT_CATALOG]
    if unknown:
        raise ValidationError(f"unknown event(s): {', '.join(unknown)}")
    return names


def _get(subscription_id) -> WebhookSubscription:
    try:
        return WebhookSubscription.objects.get(id=subscription_id)
    except WebhookSubscription.DoesNotExist as exc:
        raise NotFoundError("webhook subscription not found") from exc


def list_subscriptions():
    return WebhookSubscription.objects.all()


def create_subscription(*, url: str, event_names: list[str], actor=None) -> WebhookSubscription:
    _validate_url(url)
    names = _validate_events(event_names)
    return WebhookSubscription.objects.create(
        url=url, event_names=names, secret=secrets.token_hex(24),
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
    )


def update_subscription(subscription_id, *, url=None, event_names=None, is_active=None,
                        actor=None) -> WebhookSubscription:
    sub = _get(subscription_id)
    if url is not None:
        _validate_url(url)
        sub.url = url
    if event_names is not None:
        sub.event_names = _validate_events(event_names)
    if is_active is not None:
        sub.is_active = is_active
    sub.updated_by = actor if getattr(actor, "is_authenticated", False) else None
    sub.save()
    return sub


def delete_subscription(subscription_id) -> None:
    _get(subscription_id).delete()


def regenerate_secret(subscription_id) -> WebhookSubscription:
    sub = _get(subscription_id)
    sub.secret = secrets.token_hex(24)
    sub.save(update_fields=["secret", "updated_at"])
    return sub


def list_deliveries(subscription_id, limit: int = 50):
    _get(subscription_id)  # 404s if the subscription doesn't exist
    return (
        WebhookDelivery.objects.filter(subscription_id=subscription_id)
        .order_by("-created_at")[:limit]
    )


def _sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _build_payload(event) -> dict:
    p = event.payload
    return {
        "event": event.name,
        "occurred_at": timezone.now().isoformat(),
        "entity": p.get("entity", ""),
        "id": p.get("id") or p.get("reference") or "",
        "data": p,
    }


def on_domain_event(event) -> None:
    """Core-event listener: fan the event out to every active subscription that wants it."""
    subs = WebhookSubscription.objects.filter(is_active=True, event_names__contains=[event.name])
    if not subs.exists():
        return
    payload = _build_payload(event)
    for sub in subs:
        delivery = WebhookDelivery.objects.create(subscription=sub, event_name=event.name,
                                                   payload=payload)
        from ..tasks import deliver_webhook

        deliver_webhook(str(delivery.id))


def attempt_delivery(delivery_id) -> WebhookDelivery:
    """Send one HTTP attempt; record the outcome and schedule a retry on failure. Never raises —
    an integration outage must not break the publisher, matching ``services.dispatch``."""
    delivery = WebhookDelivery.objects.select_related("subscription").get(id=delivery_id)
    sub = delivery.subscription
    delivery.attempts += 1
    body = json.dumps(delivery.payload).encode("utf-8")
    try:
        assert_public_url(sub.url)
        req = urllib.request.Request(
            sub.url, data=body, method="POST",
            headers={
                "Content-Type": "application/json",
                "X-Conductor-Event": delivery.event_name,
                "X-Conductor-Signature": _sign(sub.secret, body),
            },
        )
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            if not (200 <= resp.status < 300):
                raise RuntimeError(f"non-2xx response: {resp.status}")
        delivery.status = WebhookDeliveryStatus.DELIVERED
        delivery.last_error = ""
        delivery.next_retry_at = None
    except Exception as exc:  # noqa: BLE001 - an integration outage must never break the publisher
        delivery.last_error = str(exc)[:255]
        if delivery.attempts >= MAX_ATTEMPTS:
            delivery.status = WebhookDeliveryStatus.FAILED
            delivery.next_retry_at = None
        else:
            delivery.status = WebhookDeliveryStatus.RETRYING
            delay = RETRY_SCHEDULE[min(delivery.attempts - 1, len(RETRY_SCHEDULE) - 1)]
            delivery.next_retry_at = timezone.now() + timedelta(seconds=delay)
    delivery.save(update_fields=["attempts", "status", "last_error", "next_retry_at", "updated_at"])
    return delivery


def retry_now(delivery_id) -> WebhookDelivery:
    """The UI's "retry now" action — attempts immediately, bypassing the backoff schedule."""
    return attempt_delivery(delivery_id)


def due_retries():
    return WebhookDelivery.objects.filter(status=WebhookDeliveryStatus.RETRYING,
                                          next_retry_at__lte=timezone.now())
