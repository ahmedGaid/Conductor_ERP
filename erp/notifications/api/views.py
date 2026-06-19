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

from erp.core.exports import EXPORT_FORMATS, Column, ReportTable, export_response
from erp.identity.permissions import HasAnyRole
from erp.identity.roles import BRANCH_MANAGER

from .. import services
from ..domain.models import Notification
from .serializers import NotificationSerializer

_CanResend = HasAnyRole.require(BRANCH_MANAGER)


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
