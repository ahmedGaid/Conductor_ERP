"""Accounting API views — thin: validate, delegate to services, return the {data} envelope.

RBAC: accounting endpoints require an accounting-capable role (Accountant / Branch Manager);
System Admin and superusers bypass (see identity.permissions.HasAnyRole).
"""
from __future__ import annotations

from dataclasses import asdict

from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from erp.core.exports import EXPORT_FORMATS, export_response
from erp.identity.permissions import HasAnyRole
from erp.identity.roles import ACCOUNTANT, BRANCH_MANAGER

from .. import services
from ..domain.models import Account, CostCenter, FiscalYear, FixedAsset, JournalEntry, Period
from ..repositories import accounts as account_repo
from . import exports as export_tables
from .serializers import (
    AccountSerializer,
    AssetDisposeSerializer,
    CostCenterSerializer,
    DepreciationRunSerializer,
    FiscalYearSerializer,
    FixedAssetCreateSerializer,
    FixedAssetSerializer,
    JournalEntrySerializer,
    JournalPostSerializer,
    PeriodSerializer,
)

_CanAccount = HasAnyRole.require(ACCOUNTANT, BRANCH_MANAGER)


def _envelope(data, status: int = 200) -> Response:
    return Response({"data": data}, status=status)


class AccountListCreateView(APIView):
    permission_classes = [IsAuthenticated, _CanAccount]

    def get(self, request: Request) -> Response:
        qs = Account.objects.all().order_by("code")
        return _envelope(AccountSerializer(qs, many=True).data)

    def post(self, request: Request) -> Response:
        s = AccountSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        v = s.validated_data
        parent = None
        if v.get("parent_code"):
            parent = account_repo.by_code(v["parent_code"])
        account = Account.objects.create(
            code=v["code"],
            name=v["name"],
            type=v["type"],
            parent=parent,
            is_postable=v.get("is_postable", True),
            is_active=v.get("is_active", True),
            is_cash=v.get("is_cash", False),
            currency=v.get("currency", "EGP"),
            created_by=request.user if request.user.is_authenticated else None,
        )
        return _envelope(AccountSerializer(account).data, status=201)


class FiscalYearListCreateView(APIView):
    permission_classes = [IsAuthenticated, _CanAccount]

    def get(self, request: Request) -> Response:
        return _envelope(FiscalYearSerializer(FiscalYear.objects.all(), many=True).data)

    def post(self, request: Request) -> Response:
        s = FiscalYearSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        fy = FiscalYear.objects.create(**s.validated_data)
        return _envelope(FiscalYearSerializer(fy).data, status=201)


class PeriodListCreateView(APIView):
    permission_classes = [IsAuthenticated, _CanAccount]

    def get(self, request: Request) -> Response:
        return _envelope(PeriodSerializer(Period.objects.select_related("fiscal_year"), many=True).data)

    def post(self, request: Request) -> Response:
        s = PeriodSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        v = s.validated_data
        fy = get_object_or_404(FiscalYear, code=v["fiscal_year_code"])
        period = Period.objects.create(
            fiscal_year=fy,
            code=v["code"],
            start_date=v["start_date"],
            end_date=v["end_date"],
            status=v.get("status", "open"),
        )
        return _envelope(PeriodSerializer(period).data, status=201)


class PeriodCloseView(APIView):
    permission_classes = [IsAuthenticated, _CanAccount]

    def post(self, request: Request, code: str) -> Response:
        period = get_object_or_404(Period, code=code)
        period.status = "closed"
        period.save(update_fields=["status"])
        return _envelope(PeriodSerializer(period).data)


class JournalListPostView(APIView):
    permission_classes = [IsAuthenticated, _CanAccount]

    def get(self, request: Request) -> Response:
        qs = JournalEntry.objects.select_related("period").order_by("-date", "-number")
        period = request.query_params.get("period")
        if period:
            qs = qs.filter(period__code=period)
        return _envelope(JournalEntrySerializer(qs[:200], many=True).data)

    def post(self, request: Request) -> Response:
        s = JournalPostSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        v = s.validated_data
        data = services.JournalInput(
            date=v["date"],
            memo=v.get("memo", ""),
            reference=v.get("reference", ""),
            source=v.get("source", "manual"),
            currency=v.get("currency", "EGP"),
            period_code=v.get("period_code") or None,
            lines=[
                services.LineInput(
                    account_code=ln["account_code"],
                    debit=ln["debit"],
                    credit=ln["credit"],
                    memo=ln.get("memo", ""),
                    cost_center_code=ln.get("cost_center_code", ""),
                )
                for ln in v["lines"]
            ],
        )
        entry = services.post_journal(data, actor=request.user)
        return _envelope(JournalEntrySerializer(entry).data, status=201)


class JournalDetailView(APIView):
    permission_classes = [IsAuthenticated, _CanAccount]

    def get(self, request: Request, entry_id) -> Response:
        entry = get_object_or_404(JournalEntry.objects.select_related("period"), id=entry_id)
        return _envelope(JournalEntrySerializer(entry).data)


class TrialBalanceView(APIView):
    permission_classes = [IsAuthenticated, _CanAccount]

    def get(self, request: Request) -> Response:
        period = request.query_params.get("period") or None
        tb = services.trial_balance(
            period_code=period,
            as_of=request.query_params.get("as_of") or None,
        )
        fmt = request.query_params.get("export")
        if fmt in EXPORT_FORMATS:
            table = export_tables.trial_balance_table(tb, request.query_params.get("lang", "en"), period)
            return export_response(table, fmt, "trial-balance")
        return _envelope(
            {
                "rows": [asdict(r) for r in tb.rows],
                "total_debit": tb.total_debit,
                "total_credit": tb.total_credit,
                "is_balanced": tb.is_balanced,
            }
        )


class GeneralLedgerView(APIView):
    permission_classes = [IsAuthenticated, _CanAccount]

    def get(self, request: Request) -> Response:
        account_code = request.query_params.get("account")
        if not account_code:
            return _envelope({"detail": "account query param required"}, status=400)
        period = request.query_params.get("period") or None
        gl = services.general_ledger(account_code, period_code=period)
        fmt = request.query_params.get("export")
        if fmt in EXPORT_FORMATS:
            table = export_tables.general_ledger_table(gl, request.query_params.get("lang", "en"), period)
            return export_response(table, fmt, f"general-ledger-{gl.account_code}")
        return _envelope(
            {
                "account_code": gl.account_code,
                "account_name": gl.account_name,
                "account_type": gl.account_type,
                "opening_balance": gl.opening_balance,
                "closing_balance": gl.closing_balance,
                "lines": [asdict(ln) for ln in gl.lines],
            }
        )


class IncomeStatementView(APIView):
    permission_classes = [IsAuthenticated, _CanAccount]

    def get(self, request: Request) -> Response:
        st = services.income_statement(
            date_from=request.query_params.get("from") or None,
            date_to=request.query_params.get("to") or None,
            period_code=request.query_params.get("period") or None,
            cost_center=request.query_params.get("cost_center") or None,
        )
        fmt = request.query_params.get("export")
        if fmt in EXPORT_FORMATS:
            table = export_tables.income_statement_table(st, request.query_params.get("lang", "en"))
            return export_response(table, fmt, "income-statement")
        return _envelope(
            {
                "date_from": st.date_from,
                "date_to": st.date_to,
                "cost_center": st.cost_center,
                "revenue": [asdict(line) for line in st.revenue],
                "expenses": [asdict(line) for line in st.expenses],
                "total_revenue": st.total_revenue,
                "total_expenses": st.total_expenses,
                "net_income": st.net_income,
            }
        )


class BalanceSheetView(APIView):
    permission_classes = [IsAuthenticated, _CanAccount]

    def get(self, request: Request) -> Response:
        bs = services.balance_sheet(as_of=request.query_params.get("as_of") or None)
        fmt = request.query_params.get("export")
        if fmt in EXPORT_FORMATS:
            table = export_tables.balance_sheet_table(bs, request.query_params.get("lang", "en"))
            return export_response(table, fmt, "balance-sheet")
        return _envelope(
            {
                "as_of": bs.as_of,
                "assets": [asdict(line) for line in bs.assets],
                "liabilities": [asdict(line) for line in bs.liabilities],
                "equity": [asdict(line) for line in bs.equity],
                "total_assets": bs.total_assets,
                "total_liabilities": bs.total_liabilities,
                "total_equity": bs.total_equity,
                "net_income": bs.net_income,
                "total_liabilities_and_equity": bs.total_liabilities_and_equity,
                "is_balanced": bs.is_balanced,
            }
        )


class TaxCodeListView(APIView):
    permission_classes = [IsAuthenticated, _CanAccount]

    def get(self, request: Request) -> Response:
        from ..domain.models import TaxCode

        rows = TaxCode.objects.filter(is_active=True).order_by("code")
        return _envelope([
            {"code": tc.code, "name": tc.name, "rate_bps": tc.rate_bps,
             "output_account_code": tc.output_account_code,
             "input_account_code": tc.input_account_code}
            for tc in rows
        ])


class CostCenterListCreateView(APIView):
    permission_classes = [IsAuthenticated, _CanAccount]

    def get(self, request: Request) -> Response:
        qs = CostCenter.objects.all().order_by("code")
        if request.query_params.get("active") == "true":
            qs = qs.filter(is_active=True)
        return _envelope(CostCenterSerializer(qs, many=True).data)

    def post(self, request: Request) -> Response:
        s = CostCenterSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        v = s.validated_data
        cc = CostCenter.objects.create(
            code=v["code"], name=v["name"], is_active=v.get("is_active", True),
            created_by=request.user if request.user.is_authenticated else None,
        )
        return _envelope(CostCenterSerializer(cc).data, status=201)


class VatReturnView(APIView):
    permission_classes = [IsAuthenticated, _CanAccount]

    def get(self, request: Request) -> Response:
        date_from = request.query_params.get("from")
        date_to = request.query_params.get("to")
        if not date_from or not date_to:
            return _envelope({"detail": "from and to query params required"}, status=400)
        vr = services.vat_return(date_from, date_to)
        fmt = request.query_params.get("export")
        if fmt in EXPORT_FORMATS:
            table = export_tables.vat_return_table(vr, request.query_params.get("lang", "en"))
            return export_response(table, fmt, "vat-return")
        return _envelope(asdict(vr))


class FixedAssetListCreateView(APIView):
    permission_classes = [IsAuthenticated, _CanAccount]

    def get(self, request: Request) -> Response:
        qs = FixedAsset.objects.all().order_by("code")
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return _envelope(FixedAssetSerializer(qs, many=True).data)

    def post(self, request: Request) -> Response:
        s = FixedAssetCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        v = s.validated_data
        asset = services.acquire_asset(
            services.AssetInput(
                code=v["code"],
                name=v["name"],
                category=v.get("category", ""),
                acquisition_date=v["acquisition_date"],
                in_service_date=v.get("in_service_date"),
                cost_minor=v["cost_minor"],
                salvage_minor=v.get("salvage_minor", 0),
                useful_life_months=v["useful_life_months"],
                funding_account_code=v.get("funding_account_code", "1000"),
            ),
            actor=request.user,
        )
        return _envelope(FixedAssetSerializer(asset).data, status=201)


class FixedAssetDetailView(APIView):
    permission_classes = [IsAuthenticated, _CanAccount]

    def get(self, request: Request, code: str) -> Response:
        asset = get_object_or_404(FixedAsset, code=code)
        return _envelope(FixedAssetSerializer(asset).data)


class FixedAssetDisposeView(APIView):
    permission_classes = [IsAuthenticated, _CanAccount]

    def post(self, request: Request, code: str) -> Response:
        asset = get_object_or_404(FixedAsset, code=code)
        s = AssetDisposeSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        v = s.validated_data
        asset = services.dispose_asset(
            asset,
            disposed_date=v["disposed_date"],
            proceeds_minor=v["proceeds_minor"],
            proceeds_account_code=v.get("proceeds_account_code", "1000"),
            actor=request.user,
        )
        return _envelope(FixedAssetSerializer(asset).data)


class DepreciationRunView(APIView):
    permission_classes = [IsAuthenticated, _CanAccount]

    def post(self, request: Request) -> Response:
        s = DepreciationRunSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        v = s.validated_data
        result = services.run_depreciation(v["period_code"], v["date"], actor=request.user)
        return _envelope({
            "period_code": result.period_code,
            "count": len(result.entries),
            "total_minor": result.total_minor,
        }, status=201)


class AssetRegisterView(APIView):
    permission_classes = [IsAuthenticated, _CanAccount]

    def get(self, request: Request) -> Response:
        include_disposed = request.query_params.get("include_disposed") == "true"
        reg = services.asset_register(include_disposed=include_disposed)
        fmt = request.query_params.get("export")
        if fmt in EXPORT_FORMATS:
            table = export_tables.asset_register_table(reg, request.query_params.get("lang", "en"))
            return export_response(table, fmt, "asset-register")
        return _envelope({
            "rows": [asdict(r) for r in reg.rows],
            "total_cost": reg.total_cost,
            "total_accumulated": reg.total_accumulated,
            "total_nbv": reg.total_nbv,
        })


class CashFlowView(APIView):
    permission_classes = [IsAuthenticated, _CanAccount]

    def get(self, request: Request) -> Response:
        cf = services.cash_flow(
            date_from=request.query_params.get("from") or None,
            date_to=request.query_params.get("to") or None,
            period_code=request.query_params.get("period") or None,
        )
        fmt = request.query_params.get("export")
        if fmt in EXPORT_FORMATS:
            table = export_tables.cash_flow_table(cf, request.query_params.get("lang", "en"))
            return export_response(table, fmt, "cash-flow")
        return _envelope(
            {
                "date_from": cf.date_from,
                "date_to": cf.date_to,
                "opening_balance": cf.opening_balance,
                "cash_in": cf.cash_in,
                "cash_out": cf.cash_out,
                "net_change": cf.net_change,
                "closing_balance": cf.closing_balance,
                "reconciles": cf.reconciles,
            }
        )
