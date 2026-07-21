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
from erp.identity.roles import ACCOUNTANT, BRANCH_MANAGER, SYSTEM_ADMIN
from erp.identity.scoping import scope_queryset

from .. import services
from ..domain.models import ETAInvoice, ETASettings
from ..services import config as eta_config
from ..services import eta_adapter
from .serializers import ETAInvoiceSerializer, ETASettingsUpdateSerializer

_CanFile = HasAnyRole.require(ACCOUNTANT, BRANCH_MANAGER)
# Connection configuration is a system-administration surface (it holds a credential), not a
# day-to-day filing action — so it is gated tighter than the invoice list/submit views.
_CanConfigure = HasAnyRole.require(SYSTEM_ADMIN)


def _scoped(request: Request):
    """Base queryset narrowed to the requester's data scope — list and detail share it, so an
    out-of-scope e-invoice 404s (indistinguishable from absent) rather than leaking existence."""
    return scope_queryset(request.user, ETAInvoice.objects.all(), "einvoice.invoice.view")


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
        # Locally generated, not a Tax-Authority UUID, while the adapter is simulated.
        Column("uuid", _l("Local reference", "مرجع محلي", lang)),
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
        qs = _scoped(request)
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
        return _envelope(ETAInvoiceSerializer(get_object_or_404(_scoped(request), id=eta_id)).data)


class _ETAActionView(APIView):
    permission_classes = [IsAuthenticated, _CanFile]
    action = ""

    def post(self, request: Request, eta_id) -> Response:
        eta = get_object_or_404(_scoped(request), id=eta_id)
        getattr(services, self.action)(eta, actor=request.user)
        eta.refresh_from_db()
        return _envelope(ETAInvoiceSerializer(eta).data)


class ETAInvoiceSubmitView(_ETAActionView):
    action = "submit_invoice"


class ETAInvoicePollView(_ETAActionView):
    action = "poll_invoice"


def _config_payload() -> dict:
    """The admin view of ETA connection settings — every value except the secret.

    Shows the stored row (so the form repopulates) alongside the resolver's verdict (``source``,
    ``configured``, ``missing``) and whether the submission adapter is still simulated — so the UI
    can never claim more than the integration actually does."""
    row = ETASettings.load()
    cfg = eta_config.effective_config()
    return {
        "environment": row.environment,
        "identity_url": row.identity_url,
        "api_base_url": row.api_base_url,
        "client_id": row.client_id,
        "rin": row.rin,
        "enabled": row.enabled,
        "has_secret": row.has_secret,   # presence only — the secret itself never leaves the server
        "last_test_ok_at": row.last_test_ok_at.isoformat() if row.last_test_ok_at else None,
        "source": cfg.source,           # "database" | "environment" | "none"
        "configured": not eta_config.missing_fields(cfg),
        "missing": eta_config.missing_setting_names(cfg),
        "simulated": not eta_adapter.is_live(),  # live only when credentials + API base are configured
    }


class ETAConfigView(APIView):
    """``GET``/``PUT /api/einvoice/config`` — System-Admin-only ETA connection settings.

    The client secret is write-only: accepted on ``PUT``, never returned on ``GET``."""

    permission_classes = [IsAuthenticated, _CanConfigure]

    def get(self, request: Request) -> Response:
        return _envelope(_config_payload())

    def put(self, request: Request) -> Response:
        serializer = ETASettingsUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        eta_config.apply_admin_update(serializer.validated_data, actor=request.user)
        return _envelope(_config_payload())


class ETAConfigTestView(APIView):
    """``POST /api/einvoice/config/test`` — try to authenticate against ETA with the config in force
    and report the outcome. Proves *credentials + reachability* only; it does not submit a document
    (the submission adapter is a later step)."""

    permission_classes = [IsAuthenticated, _CanConfigure]

    def post(self, request: Request) -> Response:
        return _envelope(eta_config.test_connection())
