"""Accounting API views — thin: validate, delegate to services, return the {data} envelope.

RBAC: accounting endpoints require an accounting-capable role (Accountant / Branch Manager);
System Admin and superusers bypass (see identity.permissions.HasAnyRole).
"""
from __future__ import annotations

from dataclasses import asdict

from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from erp.core.exports import EXPORT_FORMATS, export_response
from erp.identity.permissions import HasAnyRole
from erp.identity.roles import ACCOUNTANT, BRANCH_MANAGER

from .. import services
from ..domain.models import (
    Account,
    BankStatement,
    BankStatementLine,
    Budget,
    CostCenter,
    FiscalYear,
    FixedAsset,
    JournalEntry,
    JournalLine,
    Period,
    ReportDefinition,
)
from ..repositories import accounts as account_repo
from . import exports as export_tables
from .serializers import (
    AccountSerializer,
    AssetDisposeSerializer,
    BankAdjustmentSerializer,
    BankLineInputSerializer,
    BankMatchSerializer,
    BankStatementCreateSerializer,
    BudgetLineSetSerializer,
    BudgetSerializer,
    CostCenterSerializer,
    DepreciationRunSerializer,
    FiscalYearSerializer,
    FixedAssetCreateSerializer,
    FixedAssetSerializer,
    JournalEntrySerializer,
    JournalPostSerializer,
    PeriodSerializer,
    ReportDefinitionSerializer,
)

_CanAccount = HasAnyRole.require(ACCOUNTANT, BRANCH_MANAGER)

# Prefetch journal lines (ordered, with their account) so the serializer reads them from cache
# instead of issuing a query per entry — keeps the journals list at a constant query count.
_LINES_PREFETCH = Prefetch(
    "lines",
    queryset=JournalLine.objects.select_related("account").order_by("line_no"),
)


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
        # Prefetch lines (+ their account) so serializing N entries stays O(1) queries, not O(N).
        qs = (
            JournalEntry.objects.select_related("period")
            .prefetch_related(_LINES_PREFETCH)
            .order_by("-date", "-number")
        )
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
        entry = get_object_or_404(
            JournalEntry.objects.select_related("period").prefetch_related(_LINES_PREFETCH),
            id=entry_id,
        )
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


def _statement_dict(statement: BankStatement, with_reconciliation: bool = False) -> dict:
    data = {
        "id": str(statement.id),
        "account_code": statement.account_code,
        "statement_date": statement.statement_date,
        "opening_balance_minor": statement.opening_balance_minor,
        "closing_balance_minor": statement.closing_balance_minor,
        "reference": statement.reference,
        "status": statement.status,
        "lines": [
            {
                "id": str(ln.id),
                "line_no": ln.line_no,
                "date": ln.date,
                "description": ln.description,
                "amount_minor": ln.amount_minor,
                "is_matched": ln.is_matched,
                "matched_line_id": ln.matched_line_id,
            }
            for ln in statement.lines.order_by("line_no")
        ],
    }
    if with_reconciliation:
        rec = services.reconciliation(statement)
        data["reconciliation"] = {
            "book_balance": rec.book_balance,
            "statement_closing": rec.statement_closing,
            "difference": rec.difference,
            "is_reconciled": rec.is_reconciled,
            "unmatched_statement": rec.unmatched_statement,
            "unmatched_book": [asdict(g) for g in rec.unmatched_book],
        }
    return data


class BankStatementListCreateView(APIView):
    permission_classes = [IsAuthenticated, _CanAccount]

    def get(self, request: Request) -> Response:
        qs = BankStatement.objects.all().order_by("-statement_date")
        return _envelope([_statement_dict(s) for s in qs])

    def post(self, request: Request) -> Response:
        s = BankStatementCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        v = s.validated_data
        statement = services.create_statement(
            account_code=v["account_code"],
            statement_date=v["statement_date"],
            opening_balance_minor=v.get("opening_balance_minor", 0),
            closing_balance_minor=v["closing_balance_minor"],
            reference=v.get("reference", ""),
            lines=[
                services.BankLineInput(date=ln["date"], amount_minor=ln["amount_minor"],
                                       description=ln.get("description", ""))
                for ln in v.get("lines", [])
            ],
            actor=request.user,
        )
        return _envelope(_statement_dict(statement, with_reconciliation=True), status=201)


class BankStatementDetailView(APIView):
    permission_classes = [IsAuthenticated, _CanAccount]

    def get(self, request: Request, statement_id) -> Response:
        statement = get_object_or_404(BankStatement, id=statement_id)
        return _envelope(_statement_dict(statement, with_reconciliation=True))


class BankStatementAutoMatchView(APIView):
    permission_classes = [IsAuthenticated, _CanAccount]

    def post(self, request: Request, statement_id) -> Response:
        statement = get_object_or_404(BankStatement, id=statement_id)
        matched = services.auto_match(statement)
        data = _statement_dict(statement, with_reconciliation=True)
        data["matched"] = matched
        return _envelope(data)


class BankStatementAdjustmentView(APIView):
    permission_classes = [IsAuthenticated, _CanAccount]

    def post(self, request: Request, statement_id) -> Response:
        statement = get_object_or_404(BankStatement, id=statement_id)
        s = BankAdjustmentSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        v = s.validated_data
        services.post_adjustment(
            statement, amount_minor=v["amount_minor"],
            contra_account_code=v["contra_account_code"], memo=v.get("memo", ""),
            date=v.get("date"), actor=request.user,
        )
        return _envelope(_statement_dict(statement, with_reconciliation=True), status=201)


class BankStatementReconcileView(APIView):
    permission_classes = [IsAuthenticated, _CanAccount]

    def post(self, request: Request, statement_id) -> Response:
        statement = get_object_or_404(BankStatement, id=statement_id)
        services.mark_reconciled(statement)
        return _envelope(_statement_dict(statement, with_reconciliation=True))


class BankStatementCandidatesView(APIView):
    """Unmatched posted cash GL lines available to match against this statement (manual override)."""
    permission_classes = [IsAuthenticated, _CanAccount]

    def get(self, request: Request, statement_id) -> Response:
        from ..services.bank_rec import _candidate_gl_lines

        statement = get_object_or_404(BankStatement, id=statement_id)
        rows = _candidate_gl_lines(statement).order_by("entry__date", "entry__number", "line_no")
        return _envelope([
            {"id": gl.id, "date": gl.entry.date, "entry_number": gl.entry.number,
             "memo": gl.memo or gl.entry.memo, "amount_minor": gl.debit - gl.credit}
            for gl in rows
        ])


class BankLineMatchView(APIView):
    permission_classes = [IsAuthenticated, _CanAccount]

    def post(self, request: Request, line_id) -> Response:
        line = get_object_or_404(BankStatementLine, id=line_id)
        s = BankMatchSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        gl_line = get_object_or_404(JournalLine.objects.select_related("account"),
                                    id=s.validated_data["journal_line_id"])
        services.match_line(line, gl_line)
        return _envelope(_statement_dict(line.statement, with_reconciliation=True))

    def delete(self, request: Request, line_id) -> Response:
        line = get_object_or_404(BankStatementLine, id=line_id)
        services.unmatch_line(line)
        return _envelope(_statement_dict(line.statement, with_reconciliation=True))


class ReportDefinitionListCreateView(APIView):
    permission_classes = [IsAuthenticated, _CanAccount]

    def get(self, request: Request) -> Response:
        return _envelope(ReportDefinitionSerializer(ReportDefinition.objects.all(), many=True).data)

    def post(self, request: Request) -> Response:
        s = ReportDefinitionSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        v = s.validated_data
        defn = ReportDefinition.objects.create(
            name=v["name"], account_type=v.get("account_type", ""),
            account_codes=v.get("account_codes", ""), date_from=v.get("date_from"),
            date_to=v.get("date_to"), group_by=v.get("group_by", "account"),
            schedule=v.get("schedule", "none"),
            created_by=request.user if request.user.is_authenticated else None,
        )
        return _envelope(ReportDefinitionSerializer(defn).data, status=201)


class ReportDefinitionDetailView(APIView):
    permission_classes = [IsAuthenticated, _CanAccount]

    def get(self, request: Request, definition_id) -> Response:
        return _envelope(ReportDefinitionSerializer(get_object_or_404(ReportDefinition, id=definition_id)).data)

    def delete(self, request: Request, definition_id) -> Response:
        get_object_or_404(ReportDefinition, id=definition_id).delete()
        return _envelope({"deleted": True})


class ReportDefinitionRunView(APIView):
    permission_classes = [IsAuthenticated, _CanAccount]

    def get(self, request: Request, definition_id) -> Response:
        defn = get_object_or_404(ReportDefinition, id=definition_id)
        built = services.run_definition(defn)
        fmt = request.query_params.get("export")
        if fmt in EXPORT_FORMATS:
            table = export_tables.built_report_table(built, request.query_params.get("lang", "en"))
            return export_response(table, fmt, f"report-{built.name[:30]}")
        return _envelope({
            "definition_id": built.definition_id,
            "name": built.name,
            "group_by": built.group_by,
            "date_from": built.date_from,
            "date_to": built.date_to,
            "rows": [asdict(r) for r in built.rows],
            "total_debit": built.total_debit,
            "total_credit": built.total_credit,
            "total_balance": built.total_balance,
        })


class BudgetListCreateView(APIView):
    permission_classes = [IsAuthenticated, _CanAccount]

    def get(self, request: Request) -> Response:
        return _envelope(BudgetSerializer(Budget.objects.all(), many=True).data)

    def post(self, request: Request) -> Response:
        s = BudgetSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        v = s.validated_data
        budget = services.create_budget(
            name=v["name"], fiscal_year_code=v["fiscal_year_code"], actor=request.user
        )
        return _envelope(BudgetSerializer(budget).data, status=201)


class BudgetDetailView(APIView):
    permission_classes = [IsAuthenticated, _CanAccount]

    def get(self, request: Request, budget_id) -> Response:
        budget = get_object_or_404(Budget, id=budget_id)
        data = BudgetSerializer(budget).data
        data["lines"] = [
            {"account_code": ln.account_code, "period_code": ln.period_code,
             "amount_minor": ln.amount_minor}
            for ln in budget.lines.order_by("account_code", "period_code")
        ]
        return _envelope(data)


class BudgetLineSetView(APIView):
    permission_classes = [IsAuthenticated, _CanAccount]

    def post(self, request: Request, budget_id) -> Response:
        budget = get_object_or_404(Budget, id=budget_id)
        s = BudgetLineSetSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        v = s.validated_data
        services.set_budget_line(budget, v["account_code"], v["period_code"], v["amount_minor"])
        return _envelope({"ok": True}, status=201)


class BudgetVsActualView(APIView):
    permission_classes = [IsAuthenticated, _CanAccount]

    def get(self, request: Request, budget_id) -> Response:
        budget = get_object_or_404(Budget, id=budget_id)
        bva = services.budget_vs_actual(budget, period_code=request.query_params.get("period") or None)
        fmt = request.query_params.get("export")
        if fmt in EXPORT_FORMATS:
            table = export_tables.budget_vs_actual_table(bva, request.query_params.get("lang", "en"))
            return export_response(table, fmt, "budget-vs-actual")
        return _envelope({
            "budget_id": bva.budget_id,
            "budget_name": bva.budget_name,
            "fiscal_year_code": bva.fiscal_year_code,
            "period_code": bva.period_code,
            "rows": [asdict(r) for r in bva.rows],
            "total_budget": bva.total_budget,
            "total_actual": bva.total_actual,
            "total_variance": bva.total_variance,
        })


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
