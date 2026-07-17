"""Notifications API — the delivery log + a resend action.

RBAC: viewing the log requires an authenticated user; resending (re-triggering an outbound message)
requires a Branch Manager.
"""
from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from erp.core.errors import NotFoundError, ValidationError
from erp.core.exports import EXPORT_FORMATS, Column, ReportTable, export_response
from erp.identity.permissions import HasAnyRole
from erp.identity.roles import BRANCH_MANAGER, SYSTEM_ADMIN

from .. import services
from ..domain.models import Notification
from ..webhook_catalog import WEBHOOK_EVENT_CATALOG
from .serializers import (
    InboxSerializer,
    NotificationSerializer,
    WebhookDeliverySerializer,
    WebhookSubscriptionSerializer,
)

_CanResend = HasAnyRole.require(BRANCH_MANAGER)
_IsAdmin = HasAnyRole.require(SYSTEM_ADMIN)


def _envelope(data, status: int = 200) -> Response:
    return Response({"data": data}, status=status)


def _l(en: str, ar: str, lang: str) -> str:
    return ar if lang == "ar" else en


def _table(qs, lang: str) -> ReportTable:
    cols = [
        Column("channel", _l("Channel", "القناة", lang)),
        Column("recipient", _l("Recipient", "المستلم", lang)),
        Column("subject", _l("Subject", "الموضوع", lang)),
        Column("reference", _l("Reference", "المرجع", lang)),
        Column("status", _l("Status", "الحالة", lang)),
    ]
    rows = [
        {"channel": n.channel, "recipient": n.recipient, "subject": n.subject,
         "reference": n.reference, "status": n.status}
        for n in qs
    ]
    return ReportTable(title=_l("Notifications", "الإشعارات", lang),
                       columns=cols, rows=rows, rtl=(lang == "ar"))


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        qs = Notification.objects.all()
        if request.query_params.get("channel"):
            qs = qs.filter(channel=request.query_params["channel"])
        if request.query_params.get("status"):
            qs = qs.filter(status=request.query_params["status"])
        qs = qs[:200]
        fmt = request.query_params.get("export")
        if fmt in EXPORT_FORMATS:
            return export_response(_table(qs, request.query_params.get("lang", "en")),
                                   fmt, "notifications")
        return _envelope(NotificationSerializer(qs, many=True).data)


class NotificationResendView(APIView):
    permission_classes = [IsAuthenticated, _CanResend]

    def post(self, request: Request, note_id) -> Response:
        note = get_object_or_404(Notification, id=note_id)
        fresh = services.resend(note, actor=request.user)
        return _envelope(NotificationSerializer(fresh).data, status=201)


# --- In-app inbox: a per-user reader over the notification log ---

class InboxListView(APIView):
    """The signed-in user's own in-app notifications — unread first, newest first."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        rows = services.inbox_for(request.user)
        return _envelope(InboxSerializer(rows, many=True).data)


class InboxMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, note_id) -> Response:
        note = services.mark_read(request.user, note_id)
        if note is None:
            return _envelope({"detail": "not found"}, status=404)
        return _envelope(InboxSerializer(note).data)


class InboxMarkAllReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        count = services.mark_all_read(request.user)
        return _envelope({"count": count})


# --- Outbound webhooks: admin-only subscription management + delivery log ---

class WebhookEventCatalogView(APIView):
    permission_classes = [IsAuthenticated, _IsAdmin]

    def get(self, request: Request) -> Response:
        return _envelope(WEBHOOK_EVENT_CATALOG)


class WebhookSubscriptionListView(APIView):
    permission_classes = [IsAuthenticated, _IsAdmin]

    def get(self, request: Request) -> Response:
        subs = services.list_webhook_subscriptions()
        return _envelope(WebhookSubscriptionSerializer(subs, many=True).data)

    def post(self, request: Request) -> Response:
        try:
            sub = services.create_webhook_subscription(
                url=request.data.get("url", ""),
                event_names=request.data.get("event_names") or [],
                actor=request.user,
            )
        except ValidationError as exc:
            return _envelope({"detail": exc.message}, status=400)
        data = dict(WebhookSubscriptionSerializer(sub).data)
        data["secret"] = sub.secret  # shown exactly once — the caller must record it now
        return _envelope(data, status=201)


class WebhookSubscriptionDetailView(APIView):
    permission_classes = [IsAuthenticated, _IsAdmin]

    def patch(self, request: Request, subscription_id) -> Response:
        try:
            sub = services.update_webhook_subscription(
                subscription_id,
                url=request.data.get("url"),
                event_names=request.data.get("event_names"),
                is_active=request.data.get("is_active"),
                actor=request.user,
            )
        except NotFoundError:
            return _envelope({"detail": "not found"}, status=404)
        except ValidationError as exc:
            return _envelope({"detail": exc.message}, status=400)
        return _envelope(WebhookSubscriptionSerializer(sub).data)

    def delete(self, request: Request, subscription_id) -> Response:
        try:
            services.delete_webhook_subscription(subscription_id)
        except NotFoundError:
            return _envelope({"detail": "not found"}, status=404)
        return Response(status=204)


class WebhookSecretRegenerateView(APIView):
    permission_classes = [IsAuthenticated, _IsAdmin]

    def post(self, request: Request, subscription_id) -> Response:
        try:
            sub = services.regenerate_webhook_secret(subscription_id)
        except NotFoundError:
            return _envelope({"detail": "not found"}, status=404)
        data = dict(WebhookSubscriptionSerializer(sub).data)
        data["secret"] = sub.secret
        return _envelope(data)


class WebhookDeliveryListView(APIView):
    permission_classes = [IsAuthenticated, _IsAdmin]

    def get(self, request: Request, subscription_id) -> Response:
        try:
            deliveries = services.list_webhook_deliveries(subscription_id)
        except NotFoundError:
            return _envelope({"detail": "not found"}, status=404)
        return _envelope(WebhookDeliverySerializer(deliveries, many=True).data)


class WebhookDeliveryRetryView(APIView):
    permission_classes = [IsAuthenticated, _IsAdmin]

    def post(self, request: Request, delivery_id) -> Response:
        from ..domain.models import WebhookDelivery

        if not WebhookDelivery.objects.filter(id=delivery_id).exists():
            return _envelope({"detail": "not found"}, status=404)
        delivery = services.retry_webhook_now(delivery_id)
        return _envelope(WebhookDeliverySerializer(delivery).data)
