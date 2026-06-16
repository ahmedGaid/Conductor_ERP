"""E-invoicing API views — list/detail + submit/poll the ETA lifecycle.

RBAC: e-invoicing is a finance/compliance function — requires Accountant or Branch Manager.
"""
from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from erp.core.exports import EXPORT_FORMATS, Column, ReportTable, export_response
from erp.identity.permissions import HasAnyRole
from erp.identity.roles import ACCOUNTANT, BRANCH_MANAGER

from .. import services
from ..domain.models import ETAInvoice
from .serializers import ETAInvoiceSerializer

_CanFile = HasAnyRole.require(ACCOUNTANT, BRANCH_MANAGER)


def _envelope(data, status: int = 200) -> Response:
    return Response({"data": data}, status=status)


def _l(en: str, ar: str, lang: str) -> str:
    return ar if lang == "ar" else en


def _einvoice_table(qs, lang: str) -> ReportTable:
    cols = [
        Column("invoice", _l("Invoice", "الفاتورة", lang)),
        Column("customer", _l("Customer", "العميل", lang)),
        Column("tax", _l("VAT", "ضريبة", lang), kind="money", align="end"),
        Column("total", _l("Total", "الإجمالي", lang), kind="money", align="end"),
        Column("uuid", _l("ETA UUID", "معرّف المصلحة", lang)),
        Column("status", _l("Status", "الحالة", lang)),
    ]
    rows = [
        {"invoice": e.invoice_number, "customer": e.customer_name or e.customer_code,
         "tax": e.tax_minor, "total": e.total_minor, "uuid": e.uuid or "", "status": e.status}
        for e in qs
    ]
    return ReportTable(title=_l("E-Invoices", "الفواتير الإلكترونية", lang),
                       columns=cols, rows=rows, rtl=(lang == "ar"))


class ETAInvoiceListView(APIView):
    permission_classes = [IsAuthenticated, _CanFile]

    def get(self, request: Request) -> Response:
        qs = ETAInvoice.objects.all()
        if request.query_params.get("status"):
            qs = qs.filter(status=request.query_params["status"])
        qs = qs[:200]
        fmt = request.query_params.get("export")
        if fmt in EXPORT_FORMATS:
            table = _einvoice_table(qs, request.query_params.get("lang", "en"))
            return export_response(table, fmt, "e-invoices")
        return _envelope(ETAInvoiceSerializer(qs, many=True).data)


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
