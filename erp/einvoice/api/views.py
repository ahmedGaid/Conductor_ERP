"""E-invoicing API views — list/detail + submit/poll the ETA lifecycle.

RBAC: e-invoicing is a finance/compliance function — requires Accountant or Branch Manager.
"""
from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from erp.identity.permissions import HasAnyRole
from erp.identity.roles import ACCOUNTANT, BRANCH_MANAGER

from .. import services
from ..domain.models import ETAInvoice
from .serializers import ETAInvoiceSerializer

_CanFile = HasAnyRole.require(ACCOUNTANT, BRANCH_MANAGER)


def _envelope(data, status: int = 200) -> Response:
    return Response({"data": data}, status=status)


class ETAInvoiceListView(APIView):
    permission_classes = [IsAuthenticated, _CanFile]

    def get(self, request: Request) -> Response:
        qs = ETAInvoice.objects.all()
        if request.query_params.get("status"):
            qs = qs.filter(status=request.query_params["status"])
        return _envelope(ETAInvoiceSerializer(qs[:200], many=True).data)


class ETAInvoiceDetailView(APIView):
    permission_classes = [IsAuthenticated, _CanFile]

    def get(self, request: Request, eta_id) -> Response:
        return _envelope(ETAInvoiceSerializer(get_object_or_404(ETAInvoice, id=eta_id)).data)


class _ETAActionView(APIView):
    permission_classes = [IsAuthenticated, _CanFile]
    action = ""

    def post(self, request: Request, eta_id) -> Response:
        eta = get_object_or_404(ETAInvoice, id=eta_id)
        getattr(services, self.action)(eta, actor=request.user)
        eta.refresh_from_db()
        return _envelope(ETAInvoiceSerializer(eta).data)


class ETAInvoiceSubmitView(_ETAActionView):
    action = "submit_invoice"


class ETAInvoicePollView(_ETAActionView):
    action = "poll_invoice"
